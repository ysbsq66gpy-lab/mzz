#!/usr/bin/env python3
"""CLI batch crawler.
Usage:
    python cli_crawler.py urls.txt
Each line in the input file should contain a URL to fetch.
The script fetches each URL, extracts title and body using the same logic as the Flask app,
stores the result in the SQLite database (articles.db), and prints a short summary.
"""

import sys
import os
import re
import sqlite3
import requests
from bs4 import BeautifulSoup

DB_PATH = os.path.join(os.path.dirname(__file__), 'articles.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            body TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def extract_article(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        # title
        title_tag = soup.find('meta', property='og:title')
        title = title_tag['content'] if title_tag else 'No title found'
        # body extraction (same fallback selectors as Flask app)
        article = soup.find('article', {'id': 'dic_area'})
        if not article:
            article = (
                soup.find('div', {'id': 'articleBody'})
                or soup.find('div', {'class': re.compile(r"article[_-]body", re.I)})
                or soup.find('div', {'class': re.compile(r"article[_-]content", re.I)})
                or soup.find('section', {'class': re.compile(r"article[_-]body", re.I)})
                or soup.find('article')
                or soup.find('div', {'class': re.compile(r"article[-_]?(body|content|text)", re.I)})
                or soup.find('section', {'class': re.compile(r"article[-_]?(body|content|text)", re.I)})
            )
        body = ''
        if article:
            for tag in article.find_all(['script', 'style']):
                tag.decompose()
            body = '\n'.join(
                p.get_text(strip=True)
                for p in article.find_all(['p', 'strong', 'div', 'span', 'h1', 'h2', 'h3'])
                if p.get_text(strip=True)
            )
        else:
            body = '본문을 찾을 수 없습니다.'
        return title, body
    except Exception as e:
        return 'Error', str(e)

def store_article(url, title, body):
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT OR REPLACE INTO articles (url, title, body) VALUES (?,?,?)',
            (url, title, body)
        )
        conn.commit()
    finally:
        conn.close()

def process_url(url):
    try:
        title, body = extract_article(url)
        store_article(url, title, body)
        print(f"[OK] {url} -> {title[:60]}")
    except Exception as e:
        print(f"[FAIL] {url}: {e}")

def main():
    if len(sys.argv) < 2:
        print('Usage: python cli_crawler.py <url_file>')
        sys.exit(1)
    path = sys.argv[1]
    if not os.path.isfile(path):
        print(f'File not found: {path}')
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            url = line.strip()
            if url:
                process_url(url)

if __name__ == '__main__':
    main()
