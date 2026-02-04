# 뉴스 키워드 검색 - News Keyword Search

Google처럼 디자인된 뉴스 키워드 검색 애플리케이션입니다.

## 기능

- Google News RSS에서 키워드 검색
- Google 스타일의 깔끔한 UI
- 검색 결과를 한국 시간(KST)으로 표시
- 최신순으로 자동 정렬 (가장 최근 뉴스 먼저)

## 기술 스택

- Flask (Python)
- Google News RSS API
- pytz (시간대 변환)

## 로컬 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python app.py
```

서버는 http://localhost:5005 에서 실행됩니다.

## Railway 배포

### 1단계: GitHub에 코드 푸시

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/your-repo.git
git push -u origin main
```

### 2단계: Railway에서 배포

1. [railway.app](https://railway.app)에 접속
2. GitHub 계정으로 로그인
3. "New Project" 클릭
4. "Deploy from GitHub repo" 선택
5. 저장소 선택
6. 자동으로 배포됨

배포된 URL은 Railway 대시보드에서 확인할 수 있습니다.

## API

### POST `/api/search_keyword`

뉴스 검색 API

**요청:**
```json
{
  "keyword": "검색어"
}
```

**응답:**
```json
{
  "results": [
    {
      "title": "기사 제목",
      "link": "https://...",
      "snippet": "요약",
      "time": "RFC 2822 형식",
      "time_kst": "2026년 2월 4일 12:36:00"
    }
  ]
}
```

## 라이선스

MIT
