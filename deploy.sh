#!/bin/bash

# 자동 배포 스크립트
# 사용법: ./deploy.sh "커밋 메시지"

set -e  # 에러 발생 시 스크립트 중단

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 자동 배포 시작...${NC}"

# 커밋 메시지 확인
if [ -z "$1" ]; then
    echo -e "${RED}❌ 커밋 메시지가 필요합니다.${NC}"
    echo "사용법: ./deploy.sh \"커밋 메시지\""
    exit 1
fi

COMMIT_MSG="$1"

# 1. Git 상태 확인
echo -e "\n${BLUE}📊 Git 상태 확인...${NC}"
git status

# 2. Python 문법 검사
echo -e "\n${BLUE}🔍 Python 문법 검사...${NC}"
python3 -m py_compile app.py cli_crawler.py web_crawler.py
echo -e "${GREEN}✓ 모든 Python 파일 문법 검사 통과${NC}"

# 3. 변경사항 추가
echo -e "\n${BLUE}📝 변경사항 추가...${NC}"
git add .

# 4. 커밋
echo -e "\n${BLUE}💾 커밋 생성...${NC}"
git commit -m "$COMMIT_MSG" || {
    echo -e "${RED}⚠️  커밋할 변경사항이 없거나 커밋에 실패했습니다.${NC}"
    exit 0
}

# 5. GitHub에 푸시
echo -e "\n${BLUE}⬆️  GitHub에 푸시...${NC}"
git push origin main

echo -e "\n${GREEN}✅ 배포 완료!${NC}"
echo -e "${BLUE}📦 GitHub Actions가 자동으로 테스트를 실행합니다.${NC}"
echo -e "${BLUE}🌐 Railway가 연결되어 있다면 자동으로 배포됩니다.${NC}"
echo -e "\n${BLUE}확인:${NC}"
echo "  - GitHub Actions: https://github.com/ysbsq66gpy-lab/mzz/actions"
echo "  - Railway: https://railway.app"
