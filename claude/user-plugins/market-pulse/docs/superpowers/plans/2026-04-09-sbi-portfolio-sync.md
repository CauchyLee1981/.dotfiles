# SBI証券 ポートフォリオ自動同期 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SBI証券のWebサイトから保有銘柄・口座資産・信用ポジションを自動取得し、`portfolio.yaml` を最新状態に更新するスクリプトを作成し、`fetch_portfolio.py` に組み込む。

**Architecture:** Jina Reader (Agent Reach経由) でSBI証券のHTMLを取得 → BeautifulSoup4で解析 → `portfolio.yaml` を自動更新。認証は環境変数 `SBI_COOKIE` で管理。`fetch_portfolio.py` の冒頭で `sbi_sync.py` を呼び出し、失敗時はフェイルセーフで既存データを使用。

**Tech Stack:** Python 3, beautifulsoup4, lxml, subprocess (curl経由Jina Reader), yaml

---

## File Structure

| ファイル | 責務 |
|---------|------|
| `scripts/sbi_sync.py` | SBI証券HTML取得・解析・portfolio.yaml更新 |
| `scripts/fetch_portfolio.py` | 既存。冒頭にsbi_sync呼び出しを追加 |
| `tests/test_sbi_sync.py` | sbi_sync.pyのHTML解析ロジック単体テスト |
| `tests/fixtures/sbi_holdings.html` | 保有一覧ページのサンプルHTML |
| `tests/fixtures/sbi_account.html` | 口座サマリーページのサンプルHTML |

---

### Task 1: 依存パッケージのインストールとテスト確認

**Files:**
- None (環境セットアップのみ)

- [ ] **Step 1: 依存パッケージをインストール**

```bash
pip install beautifulsoup4 lxml
```

- [ ] **Step 2: インストール確認**

```bash
python3 -c "from bs4 import BeautifulSoup; import lxml; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 既存テストが通るか確認**

```bash
cd /workspace/.dotfiles/claude/skills/market-pulse && python3 -m pytest tests/ -v 2>&1 | tail -5
```

Expected: 全テストPASS

---

### Task 2: SBI証券 HTMLサンプルフィクスチャ作成（保有一覧）

**Files:**
- Create: `tests/fixtures/sbi_holdings.html`

- [ ] **Step 1: 保有一覧ページのサンプルHTMLを作成**

SBI証券の保有一覧テーブル構造を模したHTMLフィクスチャを作成する。カラム: 銘柄コード、銘柄名、保有数量、取得単価、現在値。

```html
<!-- tests/fixtures/sbi_holdings.html -->
<table class="tbl01">
  <tr>
    <th>銘柄コード</th><th>銘柄名</th><th>保有数量</th><th>取得単価</th><th>現在値</th>
  </tr>
  <tr>
    <td><a href="...">7974</a></td>
    <td>任天堂</td>
    <td style="text-align:right">100</td>
    <td style="text-align:right">10,673</td>
    <td style="text-align:right">11,200</td>
  </tr>
  <tr>
    <td><a href="...">9984</a></td>
    <td>ソフトバンクG</td>
    <td style="text-align:right">400</td>
    <td style="text-align:right">4,775</td>
    <td style="text-align:right">5,100</td>
  </tr>
  <tr>
    <td><a href="...">285A</a></td>
    <td>キオクシアHD</td>
    <td style="text-align:right">400</td>
    <td style="text-align:right">15,136</td>
    <td style="text-align:right">14,800</td>
  </tr>
</table>
```

- [ ] **Step 2: ファイルが正しく作成されたか確認**

```bash
cat /workspace/.dotfiles/claude/skills/market-pulse/tests/fixtures/sbi_holdings.html
```

---

### Task 3: SBI証券 HTMLサンプルフィクスチャ作成（口座サマリー）

**Files:**
- Create: `tests/fixtures/sbi_account.html`

- [ ] **Step 1: 口座サマリーページのサンプルHTMLを作成**

```html
<!-- tests/fixtures/sbi_account.html -->
<table class="tbl01">
  <tr><th>項目</th><th>金額</th></tr>
  <tr><td>預り金合計</td><td style="text-align:right">9,466,965円</td></tr>
  <tr><td>現物買付可能額</td><td style="text-align:right">974,965円</td></tr>
  <tr><td>信用新規可能額</td><td style="text-align:right">5,000,000円</td></tr>
</table>
```

- [ ] **Step 2: ファイル確認**

```bash
ls /workspace/.dotfiles/claude/skills/market-pulse/tests/fixtures/
```

Expected: `sbi_holdings.html`, `sbi_account.html`

---

### Task 4: HTML解析ロジックの単体テスト作成

**Files:**
- Create: `tests/test_sbi_sync.py`

- [ ] **Step 1: 失敗するテストを作成**

`scripts/sbi_sync.py` はまだ存在しないので、テストは失敗するはず。

```python
# tests/test_sbi_sync.py
import os
import pytest
from scripts.sbi_sync import parse_holdings_html, parse_account_html

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_parse_holdings_html_extracts_tickers():
    with open(os.path.join(FIXTURES, "sbi_holdings.html"), encoding="utf-8") as f:
        html = f.read()
    result = parse_holdings_html(html)
    tickers = [h["ticker"] for h in result]
    assert "7974" in tickers
    assert "9984" in tickers
    assert "285A" in tickers


def test_parse_holdings_html_extracts_quantity():
    with open(os.path.join(FIXTURES, "sbi_holdings.html"), encoding="utf-8") as f:
        html = f.read()
    result = parse_holdings_html(html)
    nintendo = next(h for h in result if h["ticker"] == "7974")
    assert nintendo["quantity"] == 100
    assert nintendo["name"] == "任天堂"


def test_parse_holdings_html_extracts_cost_price():
    with open(os.path.join(FIXTURES, "sbi_holdings.html"), encoding="utf-8") as f:
        html = f.read()
    result = parse_holdings_html(html)
    softbank = next(h for h in result if h["ticker"] == "9984")
    assert softbank["cost_price"] == 4775


def test_parse_holdings_html_empty_table_returns_empty():
    result = parse_holdings_html("<html><body><table></table></body></html>")
    assert result == []


def test_parse_account_html_extracts_totals():
    with open(os.path.join(FIXTURES, "sbi_account.html"), encoding="utf-8") as f:
        html = f.read()
    result = parse_account_html(html)
    assert result["total_assets"] == 9466965
    assert result["available_cash"] == 974965


def test_parse_account_html_empty_returns_none():
    result = parse_account_html("<html><body></body></html>")
    assert result["total_assets"] is None
    assert result["available_cash"] is None
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /workspace/.dotfiles/claude/skills/market-pulse && python3 -m pytest tests/test_sbi_sync.py -v
```

Expected: `ModuleNotFoundError: No module named 'scripts.sbi_sync'`

---

### Task 5: sbi_sync.py — HTML解析ロジック実装（テスト通過）

**Files:**
- Create: `scripts/sbi_sync.py`

- [ ] **Step 1: 最小限の解析関数を実装**

```python
#!/usr/bin/env python3
"""
sbi_sync.py — SBI証券のHTMLを解析してポートフォリオデータを抽出する

環境変数:
  SBI_COOKIE: SBI証券のセッションCookie（未設定時はスキップ）
"""

import sys
import os
import re
import subprocess
from bs4 import BeautifulSoup

SBI_BASE = "https://www.sbisec.co.jp/ETGate"


def _clean_number(text: str) -> str:
    """カンマ・円記号を除去して数値文字列にする。"""
    return re.sub(r"[,円]", "", text.strip())


def parse_holdings_html(html: str) -> list[dict]:
    """保有一覧HTMLから保有銘柄リストを抽出する。"""
    soup = BeautifulSoup(html, "lxml")
    holdings = []

    # SBI証券の保有一覧テーブルを検索
    tables = soup.find_all("table", class_="tbl01")
    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        # ヘッダ行からカラム位置を特定
        header_cells = rows[0].find_all(["th", "td"])
        header_texts = [cell.get_text(strip=True) for cell in header_cells]

        col_map = {}
        for i, text in enumerate(header_texts):
            if "銘柄コード" in text:
                col_map["ticker"] = i
            elif "銘柄名" in text:
                col_map["name"] = i
            elif "保有数量" in text:
                col_map["quantity"] = i
            elif "取得単価" in text:
                col_map["cost_price"] = i

        if "ticker" not in col_map:
            continue

        # データ行を解析
        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) <= max(col_map.values(), default=0):
                continue

            ticker_raw = cells[col_map["ticker"]].get_text(strip=True)
            if not ticker_raw:
                continue

            ticker = _clean_number(ticker_raw)

            holding = {"ticker": ticker}
            if "name" in col_map:
                holding["name"] = cells[col_map["name"]].get_text(strip=True)
            if "quantity" in col_map:
                try:
                    holding["quantity"] = int(_clean_number(cells[col_map["quantity"]].get_text()))
                except ValueError:
                    continue
            if "cost_price" in col_map:
                try:
                    holding["cost_price"] = float(_clean_number(cells[col_map["cost_price"]].get_text()))
                except ValueError:
                    continue

            holdings.append(holding)

    return holdings


def parse_account_html(html: str) -> dict:
    """口座サマリーHTMLから総資産・現金残高を抽出する。"""
    soup = BeautifulSoup(html, "lxml")
    result = {"total_assets": None, "available_cash": None}

    tables = soup.find_all("table", class_="tbl01")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["th", "td"])
            if len(cells) < 2:
                continue
            label = cells[0].get_text(strip=True)
            value_text = _clean_number(cells[-1].get_text())
            try:
                value = int(value_text)
            except ValueError:
                continue

            if "預り金合計" in label:
                result["total_assets"] = value
            elif "買付可能額" in label or "現金" in label:
                result["available_cash"] = value

    return result
```

- [ ] **Step 2: テストが通過することを確認**

```bash
cd /workspace/.dotfiles/claude/skills/market-pulse && python3 -m pytest tests/test_sbi_sync.py -v
```

Expected: 全テストPASS

- [ ] **Step 3: コミット**

```bash
git add scripts/sbi_sync.py tests/test_sbi_sync.py tests/fixtures/
git commit -m "feat: add SBI HTML parsing with tests"
```

---

### Task 6: Jina Reader経由のHTML取得ロジック追加

**Files:**
- Modify: `scripts/sbi_sync.py`

- [ ] **Step 1: fetch_sbi_page 関数を追加**

```python
SBI_PAGES = {
    "holdings": "/?_=1&_PageID=DefaultPID&_ControlID=WPLETstT001Control&_SeqNo=1&_PrmNm=&_PrmNm2=&getFlg=on&_MenuID=MENU_WPLETST001&_KessaiFlg=on",
    "account":  "/?_=1&_PageID=DefaultPID&_ControlID=WPLETacR001Control&_SeqNo=1&_PrmNm=&_MenuID=MENU_WPLETAC001",
}


def fetch_sbi_page(page_key: str, cookie: str) -> str:
    """Jina Reader経由でSBI証券のページHTMLを取得する。"""
    url = SBI_BASE + SBI_PAGES.get(page_key, "")
    jina_url = f"https://r.jina.ai/{url}"
    try:
        result = subprocess.run(
            ["curl", "-s", "-L",
             "-H", f"Cookie: {cookie}",
             "-H", "X-Return-Format: html",
             "--max-time", "30",
             jina_url],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(f"curl failed: {result.stderr}")
        if len(result.stdout) < 500:
            raise RuntimeError("Response too short — possible auth failure")
        return result.stdout
    except subprocess.TimeoutExpired:
        raise RuntimeError("SBI証券への接続がタイムアウトしました")
```

- [ ] **Step 2: HTML構造エラー検出を追加**

`parse_holdings_html` の先頭に以下を追加：

```python
    # ログインページにリダイレクトされた場合
    if "ログイン" in html and "tbl01" not in html:
        raise ValueError(
            "SBI証券のCookieが無効です。ブラウザから新しいCookieを取得して "
            "SBI_COOKIE 環境変数に設定してください。"
        )
```

- [ ] **Step 3: コミット**

```bash
git add scripts/sbi_sync.py
git commit -m "feat: add Jina Reader fetch with error handling"
```

---

### Task 7: portfolio.yaml更新ロジック追加

**Files:**
- Modify: `scripts/sbi_sync.py`

- [ ] **Step 1: sync_to_portfolio 関数を追加**

```python
import yaml

PORTFOLIO_PATH = os.path.join(os.path.dirname(__file__), "..", "portfolio.yaml")


def sync_to_portfolio(holdings: list[dict], account: dict):
    """解析結果を portfolio.yaml に書き込む。"""
    # 既存のportfolio.yamlを読み込む（trading_rules等を保持するため）
    if os.path.isfile(PORTFOLIO_PATH):
        with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
            portfolio = yaml.safe_load(f) or {}
    else:
        portfolio = {}

    # 口座情報を更新
    portfolio.setdefault("account", {})
    if account.get("total_assets") is not None:
        portfolio["account"]["total_assets"] = account["total_assets"]
    if account.get("available_cash") is not None:
        portfolio["account"]["available_cash"] = account["available_cash"]

    # 保有銘柄を更新（position_type等は既存値を優先）
    existing_holdings = portfolio.get("holdings", [])
    existing_map = {}
    for h in existing_holdings:
        key = (h["ticker"], h.get("position_type", "現物"))
        existing_map[key] = h

    new_holdings = []
    for h in holdings:
        key = (h["ticker"], h.get("position_type", "現物"))
        if key in existing_map:
            # 既存エントリのメタデータ（信用期限等）を保持しつつ更新
            merged = existing_map[key].copy()
            merged["quantity"] = h["quantity"]
            if "cost_price" in h:
                merged["cost_price"] = h["cost_price"]
            if "name" in h and h["name"]:
                merged["name"] = h["name"]
            new_holdings.append(merged)
        else:
            entry = {
                "ticker": h["ticker"],
                "name": h.get("name", h["ticker"]),
                "quantity": h["quantity"],
                "cost_price": h.get("cost_price", 0),
                "position_type": h.get("position_type", "現物"),
            }
            new_holdings.append(entry)

    portfolio["holdings"] = new_holdings

    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        yaml.dump(portfolio, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"[SBI sync] {len(new_holdings)} 銘柄を portfolio.yaml に反映しました")
```

- [ ] **Step 2: コミット**

```bash
git add scripts/sbi_sync.py
git commit -m "feat: add portfolio.yaml sync logic"
```

---

### Task 8: CLIエントリポイントとmain関数

**Files:**
- Modify: `scripts/sbi_sync.py`

- [ ] **Step 1: main関数を追加**

```python
def main():
    """スタンドアロン実行: SBI証券からデータを取得してportfolio.yamlを更新する。"""
    cookie = os.environ.get("SBI_COOKIE", "")
    if not cookie:
        print("[SBI sync] SBI_COOKIE が未設定のためスキップします")
        sys.exit(0)

    print("[SBI sync] SBI証券からデータを取得中...")

    # 保有一覧を取得・解析
    try:
        holdings_html = fetch_sbi_page("holdings", cookie)
        holdings = parse_holdings_html(holdings_html)
    except (RuntimeError, ValueError) as e:
        print(f"[SBI sync] 保有一覧の取得に失敗: {e}", file=sys.stderr)
        sys.exit(1)

    if not holdings:
        print("[SBI sync] 保有銘柄が取得できませんでした", file=sys.stderr)
        sys.exit(1)

    # 口座サマリーを取得・解析
    try:
        account_html = fetch_sbi_page("account", cookie)
        account = parse_account_html(account_html)
    except (RuntimeError, ValueError) as e:
        print(f"[SBI sync] 口座サマリーの取得に失敗: {e}", file=sys.stderr)
        account = {"total_assets": None, "available_cash": None}

    # portfolio.yaml に反映
    sync_to_portfolio(holdings, account)
    print("[SBI sync] 同期完了")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: スタンドアロンテスト（Cookie未設定時）**

```bash
cd /workspace/.dotfiles/claude/skills/market-pulse && python3 scripts/sbi_sync.py
```

Expected: `[SBI sync] SBI_COOKIE が未設定のためスキップします`

- [ ] **Step 3: コミット**

```bash
git add scripts/sbi_sync.py
git commit -m "feat: add CLI entry point for sbi_sync"
```

---

### Task 9: fetch_portfolio.py への組み込み

**Files:**
- Modify: `scripts/fetch_portfolio.py`

- [ ] **Step 1: `--skip-sync` 引数を追加**

```python
parser.add_argument("--skip-sync", action="store_true",
                    help="SBI証券からの自動同期をスキップ")
```

`_ensure_deps()` の後、`main()` の先頭付近に以下を追加：

```python
    # ── SBI証券自動同期 ──────────────────────────────────────────
    if not args.skip_sync:
        sbi_sync_path = os.path.join(os.path.dirname(__file__), "sbi_sync.py")
        if os.path.isfile(sbi_sync_path) and os.environ.get("SBI_COOKIE"):
            try:
                result = subprocess.run(
                    [sys.executable, sbi_sync_path],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    print(result.stdout)
                else:
                    print(f"[警告] SBI同期に失敗: {result.stderr}", file=sys.stderr)
            except subprocess.TimeoutExpired:
                print("[警告] SBI同期がタイムアウトしました", file=sys.stderr)
```

- [ ] **Step 2: 既存テストへの影響確認**

```bash
cd /workspace/.dotfiles/claude/skills/market-pulse && python3 -m pytest tests/ -v
```

Expected: 全テストPASS（SBI_COOKIE未設定なので同期はスキップされる）

- [ ] **Step 3: コミット**

```bash
git add scripts/fetch_portfolio.py
git commit -m "feat: integrate SBI sync into fetch_portfolio pipeline"
```

---

### Task 10: SKILL.md のドキュメント更新

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: SBI同期の説明を追加**

`## 手順` の `### Step 1: データ取得` セクションの前に以下を追加：

```markdown
### Step 0: SBI証券自動同期（任意）

`SBI_COOKIE` 環境変数が設定されている場合、`fetch_portfolio.py` は実行前にSBI証券から保有銘柄・口座資産を自動取得し `portfolio.yaml` を更新する。

**設定方法:**
1. ブラウザでSBI証券にログイン
2. Cookie-Editor拡張機能でCookieをエクスポート
3. 環境変数に設定: `export SBI_COOKIE="JSESSIONID=xxx; ..."`
4. `--skip-sync` フラグでスキップ可能
```

- [ ] **Step 2: コミット**

```bash
git add SKILL.md
git commit -m "docs: add SBI sync instructions to SKILL.md"
```
