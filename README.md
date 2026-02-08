# 뉴스 키워드 검색 - News Keyword Search

Google처럼 디자인된 뉴스 키워드 검색 애플리케이션입니다.

## 🔗 사이트 바로가기
- **배포 주소**: [https://web-production-171e62.up.railway.app/](https://web-production-171e62.up.railway.app/)


## 기능

- **Google News RSS**: 최신 뉴스 키워드 검색
- **Google 스타일 UI**: 깔끔하고 직관적인 디자인
- **KST 시간 변환**: 모든 뉴스를 한국 시간으로 표시
- **✨ 코다리 AI 브리핑 (New)**:
  - **뉴스 3줄 요약**: 바쁜 일상을 위해 핵심만 콕!
  - **감정 분석**: 뉴스 분위기를 AI가 판단
  - **비즈니스 인사이트**: 뉴스 이면의 가치 추출
  - **연관 키워드**: 더 공부하면 좋을 키워드 추천

## ⚙️ 사전 설정 (AI 기능 사용 시)

AI 기능을 사용하려면 Google Gemini API 키가 필요합니다.

1. [Google AI Studio](https://aistudio.google.com/app/apikey)에서 API Key를 발급받습니다.
2. 프로젝트 루트 폴더에 `.env` 파일을 생성합니다.
3. 아래 내용을 입력합니다:
   ```env
   GEMINI_API_KEY=발급받은_키_입력
   ```

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

## 자동 배포

### 방법 1: 배포 스크립트 사용 (권장)

가장 간단한 방법입니다. 한 번의 명령으로 테스트, 커밋, 푸시를 모두 실행합니다.

```bash
# 배포 스크립트 실행
./deploy.sh "커밋 메시지"
```

스크립트가 자동으로:
1. ✓ Python 문법 검사
2. ✓ Git 변경사항 커밋
3. ✓ GitHub에 푸시
4. ✓ GitHub Actions 트리거 (자동 테스트)
5. ✓ Railway 자동 배포 (연동 시)

### 방법 2: Railway GitHub 연동

Railway에서 GitHub 저장소를 연결하면 `main` 브랜치에 푸시할 때마다 자동으로 배포됩니다.

**설정 방법:**

1. [railway.app](https://railway.app)에 접속
2. GitHub 계정으로 로그인
3. "New Project" 클릭
4. "Deploy from GitHub repo" 선택
5. `ysbsq66gpy-lab/mzz` 저장소 선택
6. 자동으로 배포됨

**이후 배포:**
```bash
# 코드 수정 후
./deploy.sh "기능 추가"
# Railway가 자동으로 배포합니다!
```

### 방법 3: 수동 배포

```bash
# 변경사항 커밋
git add .
git commit -m "커밋 메시지"
git push origin main
```

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
