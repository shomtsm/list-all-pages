# Page Crawler / ページクローラー

A script that crawls all pages from the top page of a specified domain and outputs URL, title, and description to a CSV file.<br />指定ドメインのトップページから配下の全ページをクロールして、URL、タイトル、ディスクリプションをCSVファイルに出力するスクリプトです。

## Setup

```bash
pip install -r requirements.txt
```

## Usage 

### Basic Usage

```bash
python crawl_pages.py https://example.com
```

### Options

- `-o, --output`: Specify output CSV filename (auto-generated from domain if not specified, e.g., `https://example.com` → `example.com.csv`) <br /> 出力CSVファイル名を指定（指定しない場合はドメイン名から自動生成。例: `https://example.com` → `example.com.csv`）
- `-d, --delay`: Specify delay between requests in seconds (default: 1.0 seconds) <br /> リクエスト間の待機時間を秒で指定（デフォルト: 1.0秒）

### Examples

```bash
# Basic execution (example.com.csv is auto-generated)
# 基本的な実行（example.com.csvが自動生成されます）
python crawl_pages.py https://example.com

# Specify output filename
# 出力ファイル名を指定
python crawl_pages.py https://example.com -o output.csv

# Set shorter delay (be careful not to overload the server)
# 待機時間を短く設定（サーバーに負荷をかけないよう注意）
python crawl_pages.py https://example.com -d 0.5
```

## Output Format

The CSV file contains the following 3 columns:<br />
CSVファイルには以下の3列が含まれます：

- `url`: Page URLL
- `title`: Page title (`<title>` tag)
- `description`: Page description (`<meta name="description">` or `<meta property="og:description">`)

## Notes

- Only crawls pages within the same domain<br />同じドメイン内のページのみをクロールします
- There is a default 1-second delay between requests (to reduce server load)<br />リクエスト間にはデフォルトで1秒の待機時間があります（サーバーへの負荷を軽減）
- For sites with many pages, execution may take time<br />大量のページがあるサイトの場合、実行に時間がかかる場合があります

