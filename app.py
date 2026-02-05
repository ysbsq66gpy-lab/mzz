#!/usr/bin/env python3
"""Flask web app for keyword news search via Google News RSS."""

from flask import Flask, request, jsonify, send_from_directory
import requests
import xml.etree.ElementTree as ET
import urllib.parse
import re
import os
from email.utils import parsedate_to_datetime
from datetime import datetime
import pytz
from bs4 import BeautifulSoup
import time

app = Flask(__name__, template_folder='templates')

def extract_image_from_url(url):
    """Extract main image from news article URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Try multiple image selectors
        image_selectors = [
            'meta[property="og:image"]',
            'meta[name="og:image"]',
            'meta[property="twitter:image"]',
            'meta[name="twitter:image"]',
            'img[src*="jpg"], img[src*="jpeg"], img[src*="png"], img[src*="webp"]'
        ]
        
        for selector in image_selectors:
            if selector.startswith('meta'):
                meta = soup.select_one(selector)
                if meta and meta.get('content'):
                    img_url = meta['content']
                    if img_url.startswith('http'):
                        return img_url
            else:
                img = soup.select_one(selector)
                if img and img.get('src'):
                    img_url = img['src']
                    if img_url.startswith('http'):
                        return img_url
                    elif img_url.startswith('//'):
                        return 'https:' + img_url
                    elif img_url.startswith('/'):
                        base_url = '/'.join(url.split('/')[:3])
                        return base_url + img_url
        
        return ''
    except Exception as e:
        print(f"Error extracting image from {url}: {e}")
        return ''

@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')

@app.route('/api/search_keyword', methods=['POST'])
def search_keyword():
    """Fetch news articles related to a keyword using Google News RSS.
    Expected JSON: {"keyword": "some term"}
    Returns a list of items with title, link, snippet, and Korean timezone time.
    """
    data = request.get_json(silent=True) or {}
    kw = data.get('keyword', '').strip()
    if not kw:
        return jsonify(error='keyword is required'), 400
    
    # Build Google News RSS URL (Korean edition)
    query = urllib.parse.quote_plus(kw)
    rss_url = f'https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko'
    
    try:
        resp = requests.get(rss_url, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = []
        
        for i, item in enumerate(root.iter('item')):
            if i >= 10:  # Limit to 10 results for performance
                break
                
            title_el = item.find('title')
            link_el = item.find('link')
            desc_el = item.find('description')
            pub_el = item.find('pubDate')
            
            title = title_el.text if title_el is not None else ''
            link = link_el.text if link_el is not None else ''
            
            # Remove HTML tags from description
            desc = desc_el.text if desc_el is not None else ''
            desc_text = re.sub(r'<[^>]+>', '', desc)
            
            pub = pub_el.text if pub_el is not None else ''
            
            # Extract image from the actual news article
            image_url = ''
            if link:
                image_url = extract_image_from_url(link)
                time.sleep(0.5)  # Rate limiting
            
            items.append({'title': title, 'link': link, 'snippet': desc_text, 'time': pub, 'image': image_url})
        
        # Helper function to parse RFC 2822 date
        def _parse_time(t):
            try:
                return parsedate_to_datetime(t) if t else datetime.min
            except Exception:
                return datetime.min
        
        # Helper function to convert to Korean timezone
        def _format_time_kst(t):
            """Convert RFC 2822 time to Korean timezone (KST) formatted string."""
            try:
                dt = parsedate_to_datetime(t) if t else None
                if dt:
                    kst = pytz.timezone('Asia/Seoul')
                    dt_kst = dt.astimezone(kst)
                    return dt_kst.strftime('%Y년 %m월 %d일 %H:%M:%S')
                return ''
            except Exception:
                return ''
        
        # Add formatted KST time to each item
        for item in items:
            item['time_kst'] = _format_time_kst(item.get('time'))
        
        # Sort items by publication date descending (most recent first)
        items.sort(key=lambda x: _parse_time(x.get('time')), reverse=True)
        
        return jsonify(results=items)
    except Exception as e:
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5005))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
