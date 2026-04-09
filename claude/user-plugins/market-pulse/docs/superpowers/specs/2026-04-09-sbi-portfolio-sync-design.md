# SBI証券 ポートフォリオ自動同期 Design Spec

## 概要

market-pulseスキルの `fetch_portfolio.py` 実行前に、SBI証券のWebサイトから保有銘柄・口座資産・信用ポジションを自動取得し、`portfolio.yaml` を最新状態に更新する。

## アーキテクチャ

```
fetch_portfolio.py 実行
  → sbi_sync.py (新規)
    → curl + Jina Reader (Agent Reach経由)
      → SBI証券 HTML取得
        → BeautifulSoup解析
          → portfolio.yaml 自動更新
            → 既存の分析パイプライン継続
```

## コンポーネント

### 1. `scripts/sbi_sync.py` — SBI証券同期スクリプト

**責務:**
- SBI証券からHTMLを取得（Jina Reader + Cookie）
- HTMLを解析して構造化データに変換
- `portfolio.yaml` を上書き更新

**対象ページ:**
- 保有資産（My資産）: `/ETGate/?...sw_param2=assets`
- 国内株保有一覧: `/ETGate/?...sw_param4=balance`
- 信用ポジション: `/ETGate/?...path=foreign%2Faccount%2Fmargin%2Fassets`

**認証方式:**
- 環境変数 `SBI_COOKIE` にセッションCookieを設定
- Cookie例: `JSESSIONID=xxx; SBI-SSO=yyy; SBI_SSO2_TOKEN=zzz`

**取得データ:**

| フィールド | YAMLキー | ソース |
|-----------|----------|--------|
| 総資産 | `account.total_assets` | 口座サマリーページ |
| 現金残高 | `account.available_cash` | 口座サマリーページ |
| 銘柄コード | `holdings[].ticker` | 保有一覧テーブル |
| 銘柄名 | `holdings[].name` | 保有一覧テーブル |
| 保有数量 | `holdings[].quantity` | 保有一覧テーブル |
| 取得単価 | `holdings[].cost_price` | 保有一覧テーブル |
| ポジション種別 | `holdings[].position_type` | 現物/信用の区別 |
| 信用期限 | `holdings[].expiry_date` | 信用ポジション詳細 |
| 信用タイプ | `holdings[].credit_type` | 制度/一般 |

**HTML解析アプローチ:**
- SBI証券のHTMLテーブル構造をBeautifulSoupで解析
- テーブルのカラム位置でデータをマッピング（カラム名→値）
- テーブルが見つからない場合はエラーで終了（静かに失敗しない）

### 2. Cookie管理

**保存場所:** `~/.agent-reach/config.yaml` または環境変数 `SBI_COOKIE`

**設定方法:**
```bash
# Cookie-Editor等でブラウザからCookieをエクスポート
export SBI_COOKIE="JSESSIONID=xxx; SBI-SSO=yyy"
```

**有効期限管理:**
- Cookie有効期限切れで取得失敗した場合は明示的なエラーメッセージを出力
- ユーザーにCookie再設定を案内

### 3. `fetch_portfolio.py` への組み込み

**既存パイプラインへの統合:**
- `fetch_portfolio.py` の冒頭で `sbi_sync.py` を呼び出し
- `--skip-sync` フラグで同期をスキップ可能にする
- `SBI_COOKIE` が未設定の場合は同期をスキップし、既存の `portfolio.yaml` をそのまま使用

**エラーハンドリング:**
- 同期失敗時は警告を出力して既存データで継続（フェイルセーフ）
- Cookie期限切れ: 「SBI証券のCookieが無効です。再設定してください」
- ネットワークエラー: 「SBI証券に接続できませんでした」
- HTML解析エラー: 「SBI証券のページ構造が変更された可能性があります」

### 4. `update_portfolio.py` との連携

- 既存の `update_portfolio.py` はそのまま維持
- SBI同期は読み取り専用（SBI側への書き込みはしない）
- 手動取引の記録は `update_portfolio.py` で引き続き管理

## 依存関係

- `beautifulsoup4` — HTML解析
- `lxml` — 高速HTMLパーサー（beautifulsoup4のバックエンド）
- `requests` — HTTPリクエスト（Jina Reader経由の場合は不要だが、直接アクセスのフォールバック用）

## セキュリティ考慮事項

- Cookieは環境変数のみで管理、ファイルには保存しない
- `portfolio.yaml` に含み損益等の市場価格データは書き込まない（`fetch_portfolio.py` でyfinanceから取得する既存ロジックを維持）
- SBI証券へのアクセスはHTTPSのみ

## テスト

- `sbi_sync.py` をスタンドアロンで実行可能にする
- テスト用にサンプルHTMLを `/tests/fixtures/sbi_*.html` に保存
- HTML解析ロジックの単体テスト

## スコープ外

- 外国株・投資信託・債券の同期（将来対応）
- SBI証券への注文発注
- 複数口座の同時管理
