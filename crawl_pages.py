#!/usr/bin/env python3
"""
A script to crawl all pages of a specified domain and output URL, title, and description to CSV
指定ドメインの全ページをクロールして、URL、タイトル、ディスクリプションをCSVに出力するスクリプト
"""

import requests
from bs4 import BeautifulSoup
import csv
from urllib.parse import urljoin, urlparse
import time
import argparse
from collections import deque
import sys


class PageCrawler:
    def __init__(self, domain, output_file='pages.csv', delay=1.0):
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
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
    
    def extract_page_info(self, url, html_content):
        """Extract title and description from HTML / HTMLからタイトルとディスクリプションを抽出"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract title / タイトルの取得
        title_tag = soup.find('title')
        title = title_tag.get_text(strip=True) if title_tag else ''
        
        # Extract description (meta description) / ディスクリプションの取得（meta description）
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc:
            meta_desc = soup.find('meta', attrs={'property': 'og:description'})
        
        description = ''
        if meta_desc:
            description = meta_desc.get('content', '') or meta_desc.get('value', '')
            description = description.strip()
        
        return title, description
    
    def crawl(self):
        """Main crawling process / メインのクロール処理"""
        print(f"Crawling started / クロール開始: {self.domain}")
        print(f"Output file / 出力ファイル: {self.output_file}")
        print("-" * 50)
        
        while self.to_visit:
            url = self.to_visit.popleft()
            normalized_url = self.normalize_url(url)
            
            # Skip if already visited / 既に訪問済みの場合はスキップ
            if normalized_url in self.visited:
                continue
            
            # Skip if not same domain / 同じドメインでない場合はスキップ
            if not self.is_same_domain(normalized_url):
                continue
            
            self.visited.add(normalized_url)
            
            try:
                print(f"Fetching / 取得中: {normalized_url}")
                response = self.session.get(normalized_url, timeout=10)
                response.raise_for_status()
                
                # Get HTML content / HTMLコンテンツの取得
                html_content = response.text
                
                # Extract title and description / タイトルとディスクリプションの抽出
                title, description = self.extract_page_info(normalized_url, html_content)
                
                # Add to results / 結果に追加
                self.results.append({
                    'url': normalized_url,
                    'title': title,
                    'description': description
                })
                
                print(f"  ✓ Title / タイトル: {title[:50]}...")
                
                # Extract links and add to queue / リンクを抽出してキューに追加
                soup = BeautifulSoup(html_content, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    absolute_url = urljoin(normalized_url, href)
                    normalized_link = self.normalize_url(absolute_url)
                    
                    if (self.is_same_domain(normalized_link) and 
                        normalized_link not in self.visited and 
                        normalized_link not in self.to_visit):
                        self.to_visit.append(absolute_url)
                
                # Delay between requests / リクエスト間の待機時間
                time.sleep(self.delay)
                
            except requests.exceptions.RequestException as e:
                print(f"  ✗ Error / エラー: {e}")
                continue
            except Exception as e:
                print(f"  ✗ Unexpected error / 予期しないエラー: {e}")
                continue
        
        print("-" * 50)
        print(f"Crawling completed / クロール完了: {len(self.results)} pages fetched / ページを取得")
    
    def save_to_csv(self):
        """Save results to CSV file / 結果をCSVファイルに保存"""
        with open(self.output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['url', 'title', 'description'])
            writer.writeheader()
            writer.writerows(self.results)
        
        print(f"Saved to CSV file / CSVファイルに保存しました: {self.output_file}")


def get_domain_filename(domain_url):
    """Extract domain name from URL and generate CSV filename / URLからドメイン名を抽出してCSVファイル名を生成"""
    parsed = urlparse(domain_url)
    domain_name = parsed.netloc
    return f"{domain_name}.csv"


def main():
    parser = argparse.ArgumentParser(
        description='Crawl all pages of specified domain and output to CSV / 指定ドメインの全ページをクロールしてCSVに出力'
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
    
    args = parser.parse_args()
    
    # Check domain format / ドメインの形式チェック
    if not args.domain.startswith(('http://', 'https://')):
        print("Error: Domain must start with http:// or https:// / エラー: ドメインは http:// または https:// で始まる必要があります")
        sys.exit(1)
    
    # Generate filename from domain if not specified / 出力ファイル名が指定されていない場合はドメイン名から生成
    output_file = args.output if args.output else get_domain_filename(args.domain)
    
    crawler = PageCrawler(args.domain, output_file, args.delay)
    crawler.crawl()
    crawler.save_to_csv()


if __name__ == '__main__':
    main()

