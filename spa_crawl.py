#!/usr/bin/env python3
"""
A script to crawl all pages of a specified domain and output URL, title, and description to CSV
指定ドメインの全ページをクロールして、URL、タイトル、ディスクリプションをCSVに出力するスクリプト

Supports SPA (Single Page Application) sites using Playwright
PlaywrightでSPA（シングルページアプリケーション）サイトにも対応

Note: This script uses Playwright and is slower but supports JavaScript-rendered content.
For standard websites, use crawl_pages_simple.py for faster crawling.
備考: このスクリプトはPlaywrightを使用するため遅いですが、JavaScript描画コンテンツに対応しています。
通常のウェブサイトには、高速な crawl_pages_simple.py を使用してください。
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
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Error: Playwright is not installed / エラー: Playwrightがインストールされていません")
    print("Please run: pip install playwright && playwright install chromium")
    print("実行してください: pip install playwright && playwright install chromium")
    sys.exit(1)


class PageCrawler:
    def __init__(self, domain, output_file='pages.csv', delay=1.0, headless=True):
        """
        Args:
            domain: Domain to crawl (e.g., https://example.com) / クロール対象のドメイン（例: https://example.com）
            output_file: Output CSV filename / 出力CSVファイル名
            delay: Delay between requests (seconds) / リクエスト間の待機時間（秒）
            headless: Run browser in headless mode / ヘッドレスモードでブラウザを実行
        """
        self.domain = domain.rstrip('/')
        self.output_file = output_file
        self.delay = delay
        self.headless = headless
        self.visited = set()
        self.to_visit = deque([self.domain])
        self.results = []
        self.playwright = None
        self.browser = None
        self.page = None

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

    def wait_for_spa_render(self, timeout=5000):
        """
        Wait for SPA to finish rendering / SPAのレンダリング完了を待機

        Note: Currently not used. Enable this if SPA sites return incorrect titles.
        備考: 現在未使用。SPAサイトで正しいタイトルが取得できない場合に有効化する。
        """
        try:
            # Wait for network to be idle / ネットワークが落ち着くまで待機
            self.page.wait_for_load_state('networkidle', timeout=timeout)
        except PlaywrightTimeout:
            pass

        # Wait for title to change from initial state / タイトルが初期状態から変更されるまで待機
        try:
            # Check if title is a typical SPA placeholder / タイトルがSPAの典型的なプレースホルダーかチェック
            initial_title = self.page.title() or ''
            spa_placeholders = ['', 'loading', 'Loading', 'Loading...', '読み込み中']

            if initial_title.strip().lower() in [p.lower() for p in spa_placeholders]:
                # Wait for title to change / タイトルが変更されるまで待機
                for _ in range(10):  # Max 10 retries
                    time.sleep(0.5)
                    new_title = self.page.title() or ''
                    if new_title.strip().lower() not in [p.lower() for p in spa_placeholders]:
                        break
        except:
            pass

    def extract_page_info(self):
        """Extract title and description from current page / 現在のページからタイトルとディスクリプションを抽出"""
        # Extract title / タイトルの取得
        try:
            title = self.page.title() or ''
        except:
            title = ''

        # Extract description (meta description) / ディスクリプションの取得（meta description）
        description = ''
        try:
            meta_desc = self.page.query_selector('meta[name="description"]')
            if not meta_desc:
                meta_desc = self.page.query_selector('meta[property="og:description"]')
            if meta_desc:
                description = meta_desc.get_attribute('content') or ''
                description = description.strip()
        except:
            pass

        return title, description

    def extract_links(self):
        """Extract all links from current page / 現在のページから全てのリンクを抽出"""
        links = []
        try:
            # Wait for page to be fully loaded / ページの完全読み込みを待機
            self.page.wait_for_load_state('networkidle', timeout=10000)
        except PlaywrightTimeout:
            pass  # Continue even if timeout / タイムアウトしても続行

        try:
            anchors = self.page.query_selector_all('a[href]')
            for anchor in anchors:
                try:
                    href = anchor.get_attribute('href')
                    if href:
                        # Convert to absolute URL / 絶対URLに変換
                        absolute_url = urljoin(self.page.url, href)
                        links.append(absolute_url)
                except:
                    continue
        except:
            pass

        return links

    def start_browser(self):
        """Start Playwright browser / Playwrightブラウザを起動"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        self.page.set_default_timeout(30000)

    def stop_browser(self):
        """Stop Playwright browser / Playwrightブラウザを停止"""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def crawl(self):
        """Main crawling process / メインのクロール処理"""
        print(f"Crawling started (SPA mode) / クロール開始（SPAモード）: {self.domain}")
        print(f"Output file / 出力ファイル: {self.output_file}")
        print("-" * 50)

        self.start_browser()

        try:
            while self.to_visit:
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
                    self.page.goto(normalized_url, wait_until='domcontentloaded')

                    # Wait a bit for SPA to render / SPAのレンダリングを少し待機
                    time.sleep(0.5)

                    # Extract title and description / タイトルとディスクリプションの抽出
                    title, description = self.extract_page_info()

                    # Add to results / 結果に追加
                    self.results.append({
                        'url': normalized_url,
                        'title': title,
                        'description': description
                    })

                    title_display = title[:50] + '...' if len(title) > 50 else title
                    print(f"  ✓ Title / タイトル: {title_display}")

                    # Extract links and add to queue / リンクを抽出してキューに追加
                    links = self.extract_links()
                    for link in links:
                        normalized_link = self.normalize_url(link)
                        if (self.is_same_domain(normalized_link) and
                            self.is_valid_page_url(normalized_link) and
                            normalized_link not in self.visited and
                            normalized_link not in self.to_visit):
                            self.to_visit.append(normalized_link)

                    # Delay between requests / リクエスト間の待機時間
                    time.sleep(self.delay)

                except PlaywrightTimeout:
                    print(f"  ✗ Timeout / タイムアウト")
                    continue
                except Exception as e:
                    print(f"  ✗ Error / エラー: {e}")
                    continue

        finally:
            self.stop_browser()

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
        description='Crawl all pages of specified domain and output to CSV (SPA supported) / 指定ドメインの全ページをクロールしてCSVに出力（SPA対応）'
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
        default=1.0,
        help='Delay between requests in seconds (default: 1.0) / リクエスト間の待機時間（秒）（デフォルト: 1.0）'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Show browser window (default: headless) / ブラウザウィンドウを表示（デフォルト: ヘッドレス）'
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
        args.delay,
        headless=not args.no_headless
    )

    # Set up signal handler to save results on interrupt / 中断時に結果を保存するシグナルハンドラーを設定
    def signal_handler(signum, frame):
        print("\n" + "-" * 50)
        print("Interrupted! Saving partial results... / 中断されました！途中結果を保存します...")
        crawler.stop_browser()
        crawler.save_to_csv()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        crawler.crawl()
    except Exception as e:
        print(f"\nUnexpected error occurred / 予期しないエラーが発生しました: {e}")
        print("Saving partial results... / 途中結果を保存します...")
        crawler.stop_browser()
    finally:
        crawler.save_to_csv()


if __name__ == '__main__':
    main()
