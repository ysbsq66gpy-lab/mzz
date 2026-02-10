#!/usr/bin/env python3
"""Flask web app for keyword news search via Google News RSS."""

from flask import Flask, request, jsonify, send_from_directory
import requests
import xml.etree.ElementTree as ET
import urllib.parse
import re
import os
import json
from email.utils import parsedate_to_datetime
from datetime import datetime
import pytz
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder='templates')

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
        # Add User-Agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        resp = requests.get(rss_url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError as e:
            return jsonify(error=f'RSS 파싱 오류: {str(e)}'), 500

        items = []
        
        for i, item in enumerate(root.iter('item')):
            if i >= 20:  # Increase to 20 items
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
            
            items.append({
                'title': title, 
                'link': link, 
                'snippet': desc_text, 
                'time': pub
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

@app.route('/api/ai_analyze', methods=['POST'])
def ai_analyze():
    """Analyze news results using Google GenAI SDK (Gemini)."""
    data = request.get_json(silent=True) or {}
    items = data.get('items', [])
    if not items:
        return jsonify(error='분석할 뉴스 항목이 없습니다.'), 400
    
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return jsonify(error='AI API Key가 설정되지 않았습니다. .env 파일을 확인해주세요!'), 500

    try:
        # Initialize client with the new SDK
        client = genai.Client(api_key=api_key)
        
        # Prepare content for AI (limit to top 10 for tokens and speed)
        content = "\n".join([f"- 제목: {item['title']}\n  요약: {item['snippet']}" for item in items[:10]])
        
        prompt = f"""
        당신은 전문 뉴스 분석가입니다. 아래 제공된 뉴스 목록을 바탕으로 다음 4가지를 수행해주세요:
        1. 핵심 내용 3줄 요약 (리스트 형식)
        2. 전체적인 뉴스 분위기(감정) 분석 (긍정/부정/중립 및 짧은 이유)
        3. 이 뉴스들이 시사하는 비즈니스/사회적 인사이트 한 문장
        4. 사용자가 더 찾아보면 좋을 만한 연관 키워드 3개 (리스트 형식)

        뉴스 목록:
        {content}

        응답은 반드시 아래 JSON 형식을 지켜주세요:
        {{
            "summary": ["요약1", "요약2", "요약3"],
            "sentiment": "분석 결과",
            "insight": "인사이트 내용",
            "keywords": ["키워드1", "키워드2", "키워드3"]
        }}
        JSON 형식 외에 다른 말은 절대 하지 마세요.
        """

        # Try multiple models in order of preference
        models_to_try = [
            'gemini-3.0-flash',
            'gemini-3-flash-preview',
            'gemini-2.0-flash',
            'gemini-2.0-flash-exp',
            'gemini-1.5-flash',
            'gemini-1.5-pro',
        ]
        
        analysis_result = None
        error_logs = []

        for model_name in models_to_try:
            try:
                print(f"DEBUG: Attempting AI analysis with {model_name}...")
                
                # New SDK call format
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                
                if response and response.text:
                    # Robust JSON extraction using regex
                    json_str = response.text
                    # Combine multiple regex substitutions to be safer
                    # First try to find JSON block
                    json_match = re.search(r'\{[\s\S]*\}', json_str)
                    if json_match:
                        json_str = json_match.group(0)
                    
                    try:
                        analysis_result = json.loads(json_str)
                        print(f"DEBUG: Successfully got response from {model_name}")
                        break
                    except json.JSONDecodeError as je:
                         error_msg = f"JSON Decode Error for {model_name}: {str(je)}"
                         print(f"DEBUG: {error_msg}")
                         error_logs.append(error_msg)
                         continue

            except Exception as e:
                error_msg = f"Model {model_name} failed: {str(e)}"
                print(f"DEBUG: {error_msg}")
                error_logs.append(error_msg)
                continue
        
        if analysis_result:
            return jsonify(analysis_result)
        else:
            # Join all errors for debugging
            all_errors = "\n".join(error_logs)
            raise Exception(f"모든 AI 모델이 실패했습니다. 시도한 모델들의 에러 내역:\n{all_errors}")

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"AI ERROR DETAILS:\n{error_msg}")
        return jsonify(error=f'AI 분석 중 오류가 발생했습니다: {str(e)}'), 500

@app.route('/api/debug_ai')
def debug_ai():
    """Debug endpoint to check AI environment."""
    import sys
    try:
        api_key = os.environ.get('GEMINI_API_KEY')
        key_status = "Set" if api_key else "Not Set"
        if api_key:
             key_status += f" (Length: {len(api_key)}, Starts with: {api_key[:4]}...)"
        
        # SDK Version check
        sdk_version = "Unknown"
        try:
            from importlib.metadata import version
            sdk_version = version("google-genai")
        except:
             pass

        # Try to initialize client
        client_status = "Not Initialized"
        try:
            if api_key:
                client = genai.Client(api_key=api_key)
                client_status = "Initialized (Lazy)"
        except Exception as e:
            client_status = f"Initialization Error: {str(e)}"

        return jsonify({
            "python_version": sys.version,
            "google_genai_sdk_version": sdk_version,
            "api_key_status": key_status,
            "client_status": client_status,
            "note": "Using new google-genai SDK. List models not directly supported in debug view yet."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5005))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
