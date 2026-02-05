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
import asyncio
import aiohttp
import concurrent.futures

app = Flask(__name__, template_folder='templates')

def extract_image_from_url_simple(url):
    """Quick image extraction using only meta tags without full page load"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8'
        }
        
        # Only fetch first 50KB to save time
        resp = requests.get(url, headers=headers, timeout=5, stream=True)
        resp.raise_for_status()
        
        content = ''
        for chunk in resp.iter_content(chunk_size=1024, decode_unicode=True):
            content += chunk if isinstance(chunk, str) else chunk.decode('utf-8', errors='ignore')
            if len(content) > 50000:  # Stop after 50KB
                break
            if '</head>' in content:  # Stop after head section
                break
        
        # Look for Open Graph and Twitter images
        og_match = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', content, re.IGNORECASE)
        if og_match:
            img_url = og_match.group(1)
            if img_url.startswith('http'):
                return img_url
            elif img_url.startswith('//'):
                return 'https:' + img_url
            elif img_url.startswith('/'):
                base_url = '/'.join(url.split('/')[:3])
                return base_url + img_url
        
        twitter_match = re.search(r'<meta[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']', content, re.IGNORECASE)
        if twitter_match:
            img_url = twitter_match.group(1)
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
            if i >= 5:  # Limit to 5 results for speed
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
            
            # Extract image from the actual news article (non-blocking)
            image_url = ''
            if link:
                image_url = extract_image_from_url_simple(link)
            
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
