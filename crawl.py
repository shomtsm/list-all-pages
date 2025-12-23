#!/usr/bin/env python3
"""
A lightweight script to crawl all pages of a specified domain and output URL, title, and description to CSV
指定ドメインの全ページをクロールして、URL、タイトル、ディスクリプションをCSVに出力する軽量スクリプト

Uses requests + BeautifulSoup for fast crawling of standard websites
requests + BeautifulSoupを使用した高速クロール（通常のウェブサイト向け）

For SPA (Single Page Application) sites, use crawl_pages_spa.py instead
SPA（シングルページアプリケーション）サイトには crawl_pages_spa.py を使用してください
"""

import csv
from urllib.parse import urljoin, urlparse
import time
import argparse
from collections import deque
import sys
import signal
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: Required packages are not installed / エラー: 必要なパッケージがインストールされていません")
    print("Please run: pip install requests beautifulsoup4")
    print("実行してください: pip install requests beautifulsoup4")
    sys.exit(1)


class PageCrawler:
    def __init__(self, domain, output_file='pages.csv', delay=0.5):
        """
        Args:
            domain: Domain to crawl (e.g., https://example.com) / クロール対象のドメイン（例: https://example.com）
            output_file: Output CSV filename / 出力CSVファイル名
            delay: Delay between requests (seconds) / リクエスト間の待機時間（秒）
        """
        self.domain = domain.rstrip('/')
        self.output_file = output_file
        self.delay = delay
        self.visited = set()
        self.to_visit = deque([self.domain])
        self.results = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.interrupted = False

    def is_same_domain(self, url):
        """Check if URL belongs to the same domain / URLが同じドメインかどうかをチェック"""
        try:
            parsed = urlparse(url)
            domain_parsed = urlparse(self.domain)
            return parsed.netloc == domain_parsed.netloc
        except:
            return False

    def normalize_url(self, url):
        """Normalize URL (remove fragments, etc.) / URLを正規化（フラグメントを削除など）"""
        parsed = urlparse(url)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized.rstrip('/') or self.domain

    def is_valid_page_url(self, url):
        """Check if URL is a valid page URL (not a file download, etc.) / URLが有効なページURLかチェック"""
        skip_extensions = (
            '.pdf', '.zip', '.tar', '.gz', '.rar',
            '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv',
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.css', '.js', '.json', '.xml'
        )
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        return not path_lower.endswith(skip_extensions)

    def extract_page_info(self, soup):
        """Extract title and description from BeautifulSoup object / BeautifulSoupオブジェクトからタイトルとディスクリプションを抽出"""
        # Extract title / タイトルの取得
        title = ''
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Extract description (meta description) / ディスクリプションの取得（meta description）
        description = ''
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc:
            meta_desc = soup.find('meta', attrs={'property': 'og:description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc['content'].strip()

        return title, description

    def extract_links(self, soup, base_url):
        """Extract all links from BeautifulSoup object / BeautifulSoupオブジェクトから全てのリンクを抽出"""
        links = []
        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            # Convert to absolute URL / 絶対URLに変換
            absolute_url = urljoin(base_url, href)
            links.append(absolute_url)
        return links

    def crawl(self):
        """Main crawling process / メインのクロール処理"""
        print(f"Crawling started (Simple mode) / クロール開始（シンプルモード）: {self.domain}")
        print(f"Output file / 出力ファイル: {self.output_file}")
        print("-" * 50)

        while self.to_visit and not self.interrupted:
            url = self.to_visit.popleft()
            normalized_url = self.normalize_url(url)

            # Skip if already visited / 既に訪問済みの場合はスキップ
            if normalized_url in self.visited:
                continue

            # Skip if not same domain / 同じドメインでない場合はスキップ
            if not self.is_same_domain(normalized_url):
                continue

            # Skip if not a valid page URL / 有効なページURLでない場合はスキップ
            if not self.is_valid_page_url(normalized_url):
                continue

            self.visited.add(normalized_url)

            try:
                print(f"Fetching / 取得中: {normalized_url}")
                response = self.session.get(normalized_url, timeout=10)
                response.raise_for_status()

                # Check if response is HTML / レスポンスがHTMLかチェック
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type:
                    print(f"  - Skipped (not HTML) / スキップ（HTML以外）")
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract title and description / タイトルとディスクリプションの抽出
                title, description = self.extract_page_info(soup)

                # Add to results / 結果に追加
                self.results.append({
                    'url': normalized_url,
                    'title': title,
                    'description': description
                })

                title_display = title[:50] + '...' if len(title) > 50 else title
                print(f"  ✓ Title / タイトル: {title_display}")

                # Extract links and add to queue / リンクを抽出してキューに追加
                links = self.extract_links(soup, normalized_url)
                for link in links:
                    normalized_link = self.normalize_url(link)
                    if (self.is_same_domain(normalized_link) and
                        self.is_valid_page_url(normalized_link) and
                        normalized_link not in self.visited and
                        normalized_link not in self.to_visit):
                        self.to_visit.append(normalized_link)

                # Delay between requests / リクエスト間の待機時間
                time.sleep(self.delay)

            except requests.Timeout:
                print(f"  ✗ Timeout / タイムアウト")
                continue
            except requests.RequestException as e:
                print(f"  ✗ Error / エラー: {e}")
                continue
            except Exception as e:
                print(f"  ✗ Error / エラー: {e}")
                continue

        print("-" * 50)
        print(f"Crawling completed / クロール完了: {len(self.results)} pages fetched / ページを取得")

    def save_to_csv(self):
        """Save results to CSV file / 結果をCSVファイルに保存"""
        if not self.results:
            print("No results to save / 保存する結果がありません")
            return

        with open(self.output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['url', 'title', 'description'])
            writer.writeheader()
            writer.writerows(self.results)

        print(f"Saved {len(self.results)} pages to CSV file / {len(self.results)}ページをCSVファイルに保存しました: {self.output_file}")


def get_domain_filename(domain_url):
    """Extract domain name from URL and generate CSV filename with timestamp / URLからドメイン名を抽出してタイムスタンプ付きCSVファイル名を生成"""
    parsed = urlparse(domain_url)
    domain_name = parsed.netloc
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{domain_name}_{timestamp}.csv"


def main():
    parser = argparse.ArgumentParser(
        description='Crawl all pages of specified domain and output to CSV (Lightweight mode) / 指定ドメインの全ページをクロールしてCSVに出力（軽量モード）'
    )
    parser.add_argument(
        'domain',
        help='Domain to crawl (e.g., https://example.com) / クロール対象のドメイン（例: https://example.com）'
    )
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='Output CSV filename (auto-generated from domain if not specified) / 出力CSVファイル名（指定しない場合はドメイン名から自動生成）'
    )
    parser.add_argument(
        '-d', '--delay',
        type=float,
        default=0.5,
        help='Delay between requests in seconds (default: 0.5) / リクエスト間の待機時間（秒）（デフォルト: 0.5）'
    )

    args = parser.parse_args()

    # Check domain format / ドメインの形式チェック
    if not args.domain.startswith(('http://', 'https://')):
        print("Error: Domain must start with http:// or https:// / エラー: ドメインは http:// または https:// で始まる必要があります")
        sys.exit(1)

    # Generate filename from domain if not specified / 出力ファイル名が指定されていない場合はドメイン名から生成
    output_file = args.output if args.output else get_domain_filename(args.domain)

    crawler = PageCrawler(
        args.domain,
        output_file,
        args.delay
    )

    # Set up signal handler to save results on interrupt / 中断時に結果を保存するシグナルハンドラーを設定
    def signal_handler(signum, frame):
        print("\n" + "-" * 50)
        print("Interrupted! Saving partial results... / 中断されました！途中結果を保存します...")
        crawler.interrupted = True
        crawler.save_to_csv()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        crawler.crawl()
    except Exception as e:
        print(f"\nUnexpected error occurred / 予期しないエラーが発生しました: {e}")
        print("Saving partial results... / 途中結果を保存します...")
    finally:
        crawler.save_to_csv()


if __name__ == '__main__':
    main()
