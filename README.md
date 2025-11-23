# ページクローラー

指定ドメインのトップページから配下の全ページをクロールして、URL、タイトル、ディスクリプションをCSVファイルに出力するスクリプトです。

## セットアップ

```bash
pip install -r requirements.txt
```

## 使い方

### 基本的な使い方

```bash
python crawl_pages.py https://example.com
```

### オプション

- `-o, --output`: 出力CSVファイル名を指定（指定しない場合はドメイン名から自動生成。例: `https://example.com` → `example.com.csv`）
- `-d, --delay`: リクエスト間の待機時間を秒で指定（デフォルト: 1.0秒）

### 例

```bash
# 基本的な実行（example.com.csvが自動生成されます）
python crawl_pages.py https://example.com

# 出力ファイル名を指定
python crawl_pages.py https://example.com -o output.csv

# 待機時間を短く設定（サーバーに負荷をかけないよう注意）
python crawl_pages.py https://example.com -d 0.5
```

## 出力形式

CSVファイルには以下の3列が含まれます：

- `url`: ページのURL
- `title`: ページのタイトル（`<title>`タグ）
- `description`: ページのディスクリプション（`<meta name="description">`または`<meta property="og:description">`）

## 注意事項

- 同じドメイン内のページのみをクロールします
- リクエスト間にはデフォルトで1秒の待機時間があります（サーバーへの負荷を軽減）
- 大量のページがあるサイトの場合、実行に時間がかかる場合があります

