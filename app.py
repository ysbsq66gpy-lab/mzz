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

app = Flask(__name__, template_folder='templates')

def get_real_url_from_google_news(google_url):
    """Follow Google News redirect to get actual news site URL with better session handling"""
    if not google_url or 'news.google.com' not in google_url:
        return google_url
        
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://news.google.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        # Use GET with stream=True to get headers without downloading full body immediately
        resp = session.get(google_url, headers=headers, allow_redirects=True, timeout=7, stream=True)
        final_url = resp.url
        
        # Check if we are still on Google News
        if 'news.google.com' in final_url and 'articles/' in google_url:
            # Sometimes Google returns a 200 with a JS/meta-refresh redirect instead of 302
            # Let's check a bit of content
            content_sample = ''
            for chunk in resp.iter_content(chunk_size=4096, decode_unicode=True):
                if isinstance(chunk, str):
                    content_sample += chunk
                else:
                    content_sample += chunk.decode('utf-8', errors='ignore')
                if len(content_sample) > 20000:
                    break
            
            # Look for common redirect patterns in body
            match = re.search(r'window\.location\.replace\(["\'](https?://[^"\']+)["\']\)', content_sample)
            if not match:
                match = re.search(r'url=(https?://[^"\']+)["\']', content_sample, re.IGNORECASE)
            if not match:
                match = re.search(r'href=["\'](https?://[^"\']+)["\']', content_sample)
                # Filter out google links
                if match and 'google.com' in match.group(1):
                    match = None
            
            if match:
                final_url = match.group(1)
                
        return final_url
    except Exception as e:
        print(f"Error following redirect from {google_url}: {e}")
        return google_url

def extract_image_from_url_simple(url):
    """Quick image extraction using only meta tags without full page load"""
    if not url or 'news.google.com' in url:
        return ''
        
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.google.com/'
        }
        
        # Increase timeout and fetch bit more content
        resp = requests.get(url, headers=headers, timeout=8, stream=True)
        resp.raise_for_status()
        
        content = ''
        for chunk in resp.iter_content(chunk_size=4096, decode_unicode=True):
            if isinstance(chunk, str):
                content += chunk
            else:
                try:
                    content += chunk.decode('utf-8', errors='ignore')
                except:
                    pass
            if len(content) > 150000: # 150KB
                break
            if '</head>' in content:
                break
        
        # Comprehensive list of image meta tags and order of priority
        patterns = [
            r'<meta[^>]*property=["\']og:image:secure_url["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image:secure_url["\']',
            r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
            r'<meta[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']twitter:image["\']',
            r'<link[^>]*rel=["\']image_src["\'][^>]*href=["\']([^"\']+)["\']',
            r'<link[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']image_src["\']',
            r'<meta[^>]*itemprop=["\']image["\'][^>]*content=["\']([^"\']+)["\']'
        ]
        
        from html import unescape
        
        for p in patterns:
            match = re.search(p, content, re.IGNORECASE)
            if match:
                img_url = match.group(1).strip()
                img_url = unescape(img_url)
                
                if img_url.startswith('http'):
                    return img_url
                elif img_url.startswith('//'):
                    return 'https:' + img_url
                elif img_url.startswith('/'):
                    base_url = '/'.join(url.split('/')[:3])
                    return base_url + img_url
        
        # Specific selectors for common news sites if meta tags fail
        # This is very limited but can help
        if 'yna.co.kr' in url: # Yonhap News
            match = re.search(r'class="img-con">.*?src="(.*?)"', content, re.S)
            if match:
                return 'https:' + match.group(1) if match.group(1).startswith('//') else match.group(1)

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
            if i >= 6:  # Slightly increase limit for more coverage
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
            
            # Follow Google News redirect to get real URL
            real_url = get_real_url_from_google_news(link) if link else ''
            
            # Extract image from the actual news article
            image_url = ''
            if real_url and not real_url.startswith('https://news.google.com'):
                image_url = extract_image_from_url_simple(real_url)
            
            items.append({
                'title': title, 
                'link': link, 
                'real_link': real_url,
                'snippet': desc_text, 
                'time': pub, 
                'image': image_url
            })
        
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
