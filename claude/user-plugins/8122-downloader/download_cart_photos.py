#!/usr/bin/env python3
"""Download cart photo preview images from 8122.jp."""

import os
import sys
import time
import logging
from pathlib import Path
from urllib.parse import urlparse, unquote

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

SITE_URL = "https://8122.jp"
CART_URL = "https://8122.jp/cart"

MAX_RETRIES = 3
RETRY_DELAY = 2


def login(page: Page) -> None:
    """Log in to 8122.jp with email and password."""
    email = os.environ.get("SITE_EMAIL")
    password = os.environ.get("SITE_PASSWORD")

    if not email or not password:
        log.error("SITE_EMAIL and SITE_PASSWORD must be set in environment or .env file")
        sys.exit(1)

    log.info("Navigating to login page...")
    page.goto(SITE_URL, wait_until="networkidle")

    log.info("Filling credentials...")
    page.get_by_role("textbox", name="メールアドレス").fill(email)
    page.get_by_role("textbox", name="パスワード").fill(password)
    page.get_by_role("button", name="ログイン").click()

    page.wait_for_load_state("networkidle")

    if "action_user_home" not in page.url:
        log.error("Login failed. Check credentials.")
        sys.exit(1)

    log.info("Login successful.")


def navigate_to_cart(page: Page) -> None:
    """Navigate to the cart page."""
    log.info("Navigating to cart page...")
    page.goto(CART_URL, wait_until="networkidle")
    log.info(f"Cart page loaded: {page.url}")


def get_photo_urls(page: Page) -> list[str]:
    """Get all photo image URLs from the cart page.

    Each cart item has an img inside .p-cart-item_photo_edge.
    The CDN URL includes signature auth, so we extract from the DOM.
    """
    urls = page.evaluate("""() => {
        const imgs = document.querySelectorAll('.p-cart-item_photo_edge img.u-absolute');
        return Array.from(imgs).map(img => {
            if (img.src && img.src.includes('cdn.image.8122.jp')) return img.src;
            if (img.dataset.src && img.dataset.src.includes('cdn.image.8122.jp')) return img.dataset.src;
            return null;
        }).filter(Boolean);
    }""")
    log.info(f"Found {len(urls)} photo URLs in cart")
    return urls


def download_image(page: Page, url: str, save_path: Path) -> bool:
    """Download an image using the browser context (preserves session cookies).

    Returns True on success, False on failure.
    """
    if save_path.exists():
        log.info(f"Skipping (already exists): {save_path.name}")
        return True

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = page.request.get(url)
            if response.status == 200:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_path.write_bytes(response.body())
                log.info(f"Downloaded: {save_path.name} ({len(response.body())} bytes)")
                return True
            else:
                log.warning(f"HTTP {response.status} for {url} (attempt {attempt})")
        except Exception as e:
            log.warning(f"Download error (attempt {attempt}): {e}")

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    log.error(f"Failed to download after {MAX_RETRIES} attempts: {url}")
    return False


def get_filename_from_url(url: str, index: int) -> str:
    """Extract filename from URL or generate one from index."""
    parsed = urlparse(url)
    name = Path(unquote(parsed.path)).name
    if name and "." in name:
        return f"{index:04d}_{name}"
    return f"photo_{index:04d}.jpg"


def run_download(download_dir: Path, limit: int | None = None) -> dict:
    """Run the full download process.

    Args:
        download_dir: Directory to save images.
        limit: Max number of photos to process (None = all).

    Returns:
        Dict with success/failed/skipped counts.
    """
    stats = {"success": 0, "failed": 0, "skipped": 0}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            login(page)
            navigate_to_cart(page)
            urls = get_photo_urls(page)

            if not urls:
                log.warning("No photos found in cart")
                return stats

            total = len(urls) if limit is None else min(limit, len(urls))
            log.info(f"Processing {total} of {len(urls)} photos...")

            for i in range(total):
                log.info(f"[{i+1}/{total}] Processing photo {i+1}...")

                filename = get_filename_from_url(urls[i], i)
                save_path = download_dir / filename

                if download_image(page, urls[i], save_path):
                    stats["success"] += 1
                else:
                    stats["failed"] += 1

        finally:
            browser.close()

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Download cart photo preview images from 8122.jp"
    )
    parser.add_argument(
        "-o", "--output",
        default="./downloads",
        help="Output directory (default: ./downloads)",
    )
    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=None,
        help="Max number of photos to download (default: all)",
    )
    args = parser.parse_args()

    email = os.environ.get("SITE_EMAIL")
    password = os.environ.get("SITE_PASSWORD")
    if not email or not password:
        log.error("Set SITE_EMAIL and SITE_PASSWORD environment variables")
        sys.exit(1)

    download_dir = Path(args.output)
    download_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"Download directory: {download_dir.resolve()}")
    if args.limit:
        log.info(f"Limit: {args.limit} photos")

    stats = run_download(download_dir, args.limit)

    log.info("=" * 50)
    log.info("Download complete!")
    log.info(f"  Success: {stats['success']}")
    log.info(f"  Failed:  {stats['failed']}")
    log.info(f"  Total:   {stats['success'] + stats['failed']}")
    log.info("=" * 50)


if __name__ == "__main__":
    main()
