#!/usr/bin/env python3
"""sbi_sync.py — SBI証券のHTMLを解析してポートフォリオデータを抽出する"""
import sys
import os
import re
import subprocess
from bs4 import BeautifulSoup
import yaml

SBI_BASE = "https://site1.sbisec.co.jp/ETGate"

SBI_PAGES = {
    "account": "/?_ControlID=WPLETacR001Control&_PageID=DefaultPID&_ActionID=DefaultAID&_DataStoreID=DSWPLETacR001Control&OutSide=on&getFlg=on",
}

PORTFOLIO_PATH = os.path.join(os.path.dirname(__file__), "..", "portfolio.yaml")


def _clean_number(text: str) -> str:
    return re.sub(r"[,円]", "", text.strip())


def _format_cookie(raw: str) -> str:
    raw = raw.strip()
    if not raw.startswith("["):
        return raw
    try:
        names = re.findall(r'name\s*:\s*"?([^,}"]+)', raw)
        values = re.findall(r'value\s*:\s*"?([^,}"]+)', raw)
        if names and values and len(names) == len(values):
            return "; ".join(f"{n.strip()}={v.strip()}" for n, v in zip(names, values))
    except Exception:
        pass
    return raw


def _parse_ticker_name(text: str) -> tuple[str, str]:
    m = re.match(r"^(\d{3,5}[A-Z]?)(.+)$", text.strip())
    if m:
        return m.group(1), m.group(2).strip()
    return "", text.strip()


def parse_holdings_html(html: str) -> list[dict]:
    if "ログイン" in html and "保有株数" not in html:
        raise ValueError(
            "SBI証券のCookieが無効です。ブラウザから新しいCookieを取得して "
            "SBI_COOKIE 環境変数に設定してください。"
        )
    soup = BeautifulSoup(html, "lxml")
    results = []
    for table in soup.find_all("table"):
        # 保有株式テーブルを1つだけ処理
        table_text = table.get_text()
        if "株式（現物" not in table_text:
            continue
        rows = table.find_all("tr")
        in_equity_section = False
        position_type = "現物"
        for row in rows:
            cells = row.find_all("td")
            texts = [c.get_text(strip=True) for c in cells]
            joined = " ".join(texts)
            if "株式（現物" in joined or "株式（信用" in joined:
                in_equity_section = True
                position_type = "信用" if "信用" in joined else "現物"
                continue
            if "投資信託" in joined and "保有口数" in joined:
                in_equity_section = False
                continue
            if "債券" in joined and "保有口数" in joined:
                in_equity_section = False
                continue
            if not in_equity_section:
                continue
            if any("保有株数" in t for t in texts):
                continue
            if any("取得単価" in t for t in texts):
                continue
            for cell_text in texts:
                ticker, name = _parse_ticker_name(cell_text)
                if ticker and name and re.match(r"^\d{4}[A-Z]?$", ticker) or (ticker and name and re.match(r"^\d{3}[A-Z]$", ticker)):
                    remaining = texts[texts.index(cell_text) + 1:] if cell_text in texts else []
                    nums = []
                    for t in remaining:
                        cleaned = _clean_number(t)
                        if cleaned and re.match(r"^-?[\d,.]+$", cleaned.replace(",", "")):
                            nums.append(cleaned.replace(",", ""))
                    if len(nums) < 2:
                        next_row = row.find_next_sibling("tr")
                        if next_row:
                            next_cells = next_row.find_all("td")
                            for nc in next_cells:
                                nt = nc.get_text(strip=True)
                                cleaned = _clean_number(nt)
                                if cleaned and re.match(r"^-?[\d,.]+$", cleaned.replace(",", "")):
                                    nums.append(cleaned.replace(",", ""))
                    if len(nums) >= 2:
                        entry = {
                            "ticker": ticker,
                            "name": name,
                            "quantity": int(nums[0]),
                            "cost_price": int(float(nums[1])),
                        }
                        if position_type != "現物":
                            entry["position_type"] = position_type
                        results.append(entry)
                    break
        # 最初の有効なテーブルだけで十分
        if results:
            break
    return results


def parse_account_html(html: str) -> dict:
    if "ログイン" in html and "買付余力" not in html:
        raise ValueError(
            "SBI証券のCookieが無効です。ブラウザから新しいCookieを取得して "
            "SBI_COOKIE 環境変数に設定してください。"
        )
    total_assets = None
    available_cash = None
    soup = BeautifulSoup(html, "lxml")
    for td in soup.find_all("td"):
        text = td.get_text(strip=True)
        if text.startswith("買付余力"):
            next_td = td.find_next_sibling("td")
            if next_td:
                val_text = _clean_number(next_td.get_text(strip=True))
                try:
                    available_cash = int(val_text)
                except ValueError:
                    pass
        if text == "計":
            next_td = td.find_next_sibling("td")
            if next_td:
                val_text = _clean_number(next_td.get_text(strip=True))
                try:
                    total_assets = int(val_text)
                except ValueError:
                    pass
    return {"total_assets": total_assets, "available_cash": available_cash}


def fetch_sbi_page(page_key: str, cookie: str) -> str:
    url = SBI_BASE + SBI_PAGES.get(page_key, "")
    try:
        result = subprocess.run(
            ["curl", "-s", "-L",
             "-H", f"Cookie: {cookie}",
             "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
             "--max-time", "30",
             url],
            capture_output=True, timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(f"curl failed: {result.stderr}")
        html = result.stdout.decode("shift_jis", errors="replace")
        if len(html) < 500:
            raise RuntimeError("Response too short — possible auth failure")
        return html
    except subprocess.TimeoutExpired:
        raise RuntimeError("SBI証券への接続がタイムアウトしました")


def sync_to_portfolio(holdings: list[dict], account: dict):
    if os.path.isfile(PORTFOLIO_PATH):
        with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
            portfolio = yaml.safe_load(f) or {}
    else:
        portfolio = {}

    portfolio.setdefault("account", {})
    if account.get("total_assets") is not None:
        portfolio["account"]["total_assets"] = account["total_assets"]
    if account.get("available_cash") is not None:
        portfolio["account"]["available_cash"] = account["available_cash"]

    existing_holdings = portfolio.get("holdings", [])
    existing_map = {}
    for h in existing_holdings:
        key = (h["ticker"], h.get("position_type", "現物"))
        existing_map[key] = h

    def _ticker_base(ticker: str) -> str:
        return re.sub(r"\.T$", "", ticker)

    new_holdings = []
    for h in holdings:
        key = (h["ticker"], h.get("position_type", "現物"))
        if key in existing_map:
            merged = existing_map[key].copy()
            merged["quantity"] = h["quantity"]
            if "cost_price" in h:
                merged["cost_price"] = h["cost_price"]
            if "name" in h and h["name"]:
                merged["name"] = h["name"]
            new_holdings.append(merged)
        else:
            # .Tサフィックス無視で既存エントリを探す
            matched = False
            for ekey, eentry in existing_map.items():
                if _ticker_base(ekey[0]) == _ticker_base(key[0]) and ekey[1] == key[1]:
                    merged = eentry.copy()
                    merged["quantity"] = h["quantity"]
                    if "cost_price" in h:
                        merged["cost_price"] = h["cost_price"]
                    new_holdings.append(merged)
                    matched = True
                    break
            if not matched:
                entry = {
                    "ticker": h["ticker"],
                    "name": h.get("name", h["ticker"]),
                    "quantity": h["quantity"],
                    "cost_price": h.get("cost_price", 0),
                    "position_type": h.get("position_type", "現物"),
                }
                new_holdings.append(entry)

    new_bases = {(_ticker_base(h["ticker"]), h.get("position_type", "現物")) for h in holdings}
    for key, h in existing_map.items():
        if (_ticker_base(key[0]), key[1]) not in new_bases:
            print(f"[SBI sync] 警告: {key[0]} はSBI取得データに含まれないため既存データを保持します")
            new_holdings.append(h)

    portfolio["holdings"] = new_holdings

    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        yaml.dump(portfolio, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"[SBI sync] {len(new_holdings)} 銘柄を portfolio.yaml に反映しました")


def main():
    cookie = os.environ.get("SBI_COOKIE", "")
    if not cookie:
        print("[SBI sync] SBI_COOKIE が未設定のためスキップします")
        sys.exit(0)
    cookie = _format_cookie(cookie)

    print("[SBI sync] SBI証券からデータを取得中...")

    try:
        html = fetch_sbi_page("account", cookie)
    except RuntimeError as e:
        print(f"[SBI sync] ページの取得に失敗: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        holdings = parse_holdings_html(html)
    except ValueError as e:
        print(f"[SBI sync] 保有一覧の解析に失敗: {e}", file=sys.stderr)
        sys.exit(1)

    if not holdings:
        print("[SBI sync] 保有銘柄が取得できませんでした", file=sys.stderr)
        sys.exit(1)

    try:
        account = parse_account_html(html)
    except ValueError as e:
        print(f"[SBI sync] 口座サマリーの解析に失敗: {e}", file=sys.stderr)
        account = {"total_assets": None, "available_cash": None}

    sync_to_portfolio(holdings, account)
    print("[SBI sync] 同期完了")


if __name__ == "__main__":
    main()
