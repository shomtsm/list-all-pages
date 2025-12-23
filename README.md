# Page Crawler / ページクローラー

A script that crawls all pages from the top page of a specified domain and outputs URL, title, and description to a CSV file.<br />指定ドメインのトップページから配下の全ページをクロールして、URL、タイトル、ディスクリプションをCSVファイルに出力するスクリプトです。

## Setup

```bash
pip install -r requirements.txt
```

## Two Versions Available / 2種類のスクリプト

| Script | Speed | Use Case |
|--------|-------|----------|
| `crawl.py` | Fast / 高速 | Standard websites / 通常のウェブサイト |
| `spa_crawl.py` | Slow / 低速 | SPA (React, Vue, etc.) / SPA（React, Vueなど） |

### Which one should I use? / どちらを使うべき？

- **crawl.py (Recommended for most sites / ほとんどのサイトにおすすめ)**
  - Uses `requests` + `BeautifulSoup`
  - Much faster, lightweight
  - Works for standard server-rendered HTML sites
  - 通常のサーバーサイドレンダリングのHTMLサイト向け

- **spa_crawl.py (For JavaScript-heavy sites / JavaScript多用サイト向け)**
  - Uses `Playwright` (headless browser)
  - Slower but renders JavaScript content
  - Required for React, Vue, Angular, Next.js (CSR) sites
  - JavaScript描画コンテンツに対応

## Usage

### Simple Mode (Fast) / シンプルモード（高速）

```bash
source venv/bin/activate

python crawl.py https://example.com
```

### SPA Mode (For JavaScript sites) / SPAモード（JavaScriptサイト向け）

```bash
source venv/bin/activate

python spa_crawl.py https://example.com
```

## Options

### crawl.py

- `-o, --output`: Specify output CSV filename (auto-generated from domain if not specified) <br /> 出力CSVファイル名を指定（指定しない場合はドメイン名から自動生成）
- `-d, --delay`: Delay between requests in seconds (default: 0.5) <br /> リクエスト間の待機時間（デフォルト: 0.5秒）

### spa_crawl.py

- `-o, --output`: Specify output CSV filename (auto-generated from domain if not specified) <br /> 出力CSVファイル名を指定（指定しない場合はドメイン名から自動生成）
- `-d, --delay`: Delay between requests in seconds (default: 1.0) <br /> リクエスト間の待機時間（デフォルト: 1.0秒）
- `--no-headless`: Show browser window <br /> ブラウザウィンドウを表示

## Examples

```bash
# Fast crawl for standard websites
# 通常のウェブサイト向け高速クロール
python crawl.py https://example.com

# Specify output filename
# 出力ファイル名を指定
python crawl.py https://example.com -o output.csv

# For SPA sites (React, Vue, etc.)
# SPAサイト（React, Vueなど）向け
python spa_crawl.py https://spa-site.com

# SPA with visible browser (for debugging)
# SPAでブラウザを表示（デバッグ用）
python spa_crawl.py https://spa-site.com --no-headless
```

## Output Format

The CSV file contains the following 3 columns:<br />
CSVファイルには以下の3列が含まれます：

- `url`: Page URL
- `title`: Page title (`<title>` tag)
- `description`: Page description (`<meta name="description">` or `<meta property="og:description">`)

## Notes

- Only crawls pages within the same domain<br />同じドメイン内のページのみをクロールします
- Ctrl+C to interrupt and save partial results<br />Ctrl+Cで中断して途中結果を保存できます
- For sites with many pages, execution may take time<br />大量のページがあるサイトの場合、実行に時間がかかる場合があります
