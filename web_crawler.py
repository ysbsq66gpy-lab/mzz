#!/usr/bin/env python3
"""
Simple web crawler that fetches a page and extracts all hyperlinks.
Usage:
    python web_crawler.py <start_url> [max_depth]
"""

import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque


def crawl(start_url, max_depth=1):
    visited = set()
    queue = deque([(start_url, 0)])
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    while queue:
        url, depth = queue.popleft()
        if url in visited or depth > max_depth:
            continue
        visited.add(url)
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"[error] {url}: {e}", file=sys.stderr)
            continue
        print(f"[{depth}] {url}")
        if depth == max_depth:
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            link = urljoin(url, a["href"])
            # keep same domain as the start URL
            if urlparse(link).netloc == urlparse(start_url).netloc:
                queue.append((link, depth + 1))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python web_crawler.py <start_url> [max_depth]")
        sys.exit(1)
    start = sys.argv[1]
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    crawl(start, depth)
