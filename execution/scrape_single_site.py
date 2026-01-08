#!/usr/bin/env python3
"""
Scrape a single website and save structured data.

Usage:
    python scrape_single_site.py --url "https://example.com" --output-format json
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup


def scrape_site(url, delay=1, dynamic=False, cookies_path=None):
    """
    Scrape a single website.

    Args:
        url: Target URL to scrape
        delay: Delay between requests in seconds
        dynamic: Use Playwright for JavaScript rendering
        cookies_path: Path to cookies JSON file

    Returns:
        dict: Scraped data
    """
    print(f"Scraping: {url}")

    # Add delay to be respectful
    if delay > 0:
        time.sleep(delay)

    # Load cookies if provided
    cookies = None
    if cookies_path:
        with open(cookies_path, 'r') as f:
            cookies = json.load(f)

    # Handle dynamic content with Playwright
    if dynamic:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(url)
                time.sleep(2)  # Wait for JS to load
                content = page.content()
                browser.close()
        except ImportError:
            print("Warning: Playwright not installed. Install with: pip install playwright")
            print("Falling back to static scraping...")
            dynamic = False

    # Static scraping
    if not dynamic:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, cookies=cookies, timeout=30)
        response.raise_for_status()
        content = response.text

    # Parse with BeautifulSoup
    soup = BeautifulSoup(content, 'html.parser')

    # Extract basic data
    data = {
        'url': url,
        'title': soup.title.string if soup.title else None,
        'scraped_at': datetime.now().isoformat(),
        'headings': [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])],
        'paragraphs': [p.get_text(strip=True) for p in soup.find_all('p')],
        'links': [{'text': a.get_text(strip=True), 'href': a.get('href')}
                  for a in soup.find_all('a', href=True)],
    }

    return data


def save_output(data, output_format, output_dir='.tmp'):
    """Save scraped data in specified format."""
    Path(output_dir).mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if output_format == 'json':
        output_path = Path(output_dir) / f'scraped_data_{timestamp}.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved to: {output_path}")
        return str(output_path)

    elif output_format == 'csv':
        import csv
        output_path = Path(output_dir) / f'scraped_data_{timestamp}.csv'
        # Flatten data for CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['URL', 'Title', 'Scraped At'])
            writer.writerow([data['url'], data['title'], data['scraped_at']])
        print(f"Saved to: {output_path}")
        return str(output_path)

    elif output_format == 'sheet':
        print("Sheet format requires additional upload step.")
        print("First saving as JSON intermediate...")
        json_path = save_output(data, 'json', output_dir)
        print(f"Use: python execution/upload_to_sheet.py --input {json_path}")
        return json_path

    else:
        raise ValueError(f"Unsupported format: {output_format}")


def main():
    parser = argparse.ArgumentParser(description='Scrape a single website')
    parser.add_argument('--url', required=True, help='URL to scrape')
    parser.add_argument('--output-format', default='json',
                       choices=['json', 'csv', 'sheet'],
                       help='Output format')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between requests in seconds')
    parser.add_argument('--dynamic', action='store_true',
                       help='Use Playwright for JavaScript rendering')
    parser.add_argument('--cookies', help='Path to cookies JSON file')

    args = parser.parse_args()

    try:
        data = scrape_site(
            args.url,
            delay=args.delay,
            dynamic=args.dynamic,
            cookies_path=args.cookies
        )
        output_path = save_output(data, args.output_format)
        print(f"Success! Output: {output_path}")

    except requests.RequestException as e:
        print(f"Error scraping {args.url}: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
