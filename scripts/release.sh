#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 스크립트의 실제 위치 확인
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# 프로젝트 루트 디렉토리 (스크립트의 상위 디렉토리)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# 프로젝트 루트 디렉토리로 이동
cd "$PROJECT_ROOT"

echo -e "${YELLOW}프로젝트 디렉토리: ${NC}$PROJECT_ROOT"

# Git SSH 비대화식 설정 및 원격 URL 확인/변환
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -o BatchMode=yes}"

REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [ -z "$REMOTE_URL" ]; then
    echo -e "${RED}Error: git 원격 'origin'을 찾을 수 없습니다.${NC}"
    exit 1
fi

# HTTPS 원격이면 SSH 형식으로 자동 전환 (예: https://github.com/owner/repo.git -> git@github.com:owner/repo.git)
if [[ "$REMOTE_URL" =~ ^https://([^/]+)/(.+)$ ]]; then
    HOST="${BASH_REMATCH[1]}"
    PATH_PART="${BASH_REMATCH[2]}"
    PATH_PART="${PATH_PART%.git}"
    NEW_URL="git@${HOST}:${PATH_PART}.git"
    echo -e "${YELLOW}origin 원격을 SSH로 변경합니다:${NC} $NEW_URL"
    git remote set-url origin "$NEW_URL"
fi

# 현재 브랜치 확인
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "dev" ]; then
    echo -e "${RED}Error: dev 브랜치에서만 실행할 수 있습니다.${NC}"
    echo -e "${YELLOW}현재 브랜치: ${NC}$CURRENT_BRANCH"
    exit 1
fi

# 커밋되지 않은 변경사항 확인
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}Error: 커밋되지 않은 변경사항이 있습니다. 먼저 모든 변경사항을 커밋해주세요.${NC}"
    exit 1
fi

# 릴리즈 베이스 브랜치 탐지 (main 우선, 없으면 master)
git fetch origin
if git show-ref --verify --quiet refs/remotes/origin/main; then
    BASE_BRANCH="main"
elif git show-ref --verify --quiet refs/remotes/origin/master; then
    BASE_BRANCH="master"
else
    echo -e "${RED}Error: 원격에 main/master 브랜치가 없습니다. 릴리즈 베이스 브랜치를 찾을 수 없습니다.${NC}"
    exit 1
fi

# 베이스 브랜치와 dev 브랜치의 차이 확인
BASE_HEAD=$(git rev-parse origin/$BASE_BRANCH)
DEV_HEAD=$(git rev-parse origin/dev)

if [ "$BASE_HEAD" == "$DEV_HEAD" ]; then
    echo -e "${RED}Error: ${BASE_BRANCH} 브랜치와 dev 브랜치의 내용이 동일합니다.${NC}"
    echo -e "${YELLOW}릴리즈할 새로운 변경사항이 없습니다.${NC}"
    exit 1
fi

# 현재 버전 가져오기 (meson.build에서 추출)
CURRENT_VERSION_FROM_MESON=$(grep -Po "version:\s*'\K[^']+" meson.build | head -n1)
if [ -z "$CURRENT_VERSION_FROM_MESON" ]; then
    echo -e "${RED}Error: meson.build에서 현재 버전을 찾을 수 없습니다.${NC}"
    exit 1
fi
CURRENT_VERSION="v$CURRENT_VERSION_FROM_MESON"

# Git 태그에서도 확인하여 더 높은 버전이 있으면 사용
GIT_VERSION=$(git tag --sort=-v:refname | grep '^v' | head -n1 || echo "v0.0.0")
if [ "$GIT_VERSION" != "v0.0.0" ]; then
    # 버전 비교 (간단한 비교)
    if [[ "$GIT_VERSION" > "$CURRENT_VERSION" ]]; then
        CURRENT_VERSION="$GIT_VERSION"
    fi
fi

# 버전 증가 함수
increment_version() {
    local version=$1
    local increment_type=$2
    
    # v 접두사 제거
    version=${version#v}
    
    # 버전을 . 으로 분리
    IFS='.' read -ra VERSION_PARTS <<< "$version"
    
    major=${VERSION_PARTS[0]:-0}
    minor=${VERSION_PARTS[1]:-0}
    patch=${VERSION_PARTS[2]:-0}
    
    case $increment_type in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch|*)
            patch=$((patch + 1))
            ;;
    esac
    
    echo "v$major.$minor.$patch"
}

# 파라미터 파싱
AUTO_YES=false
VERSION_TYPE="patch"

for arg in "$@"; do
    case $arg in
        --yes|-yes|-y|-Y)
            AUTO_YES=true
            # -y 옵션만 사용하면 기본적으로 patch 버전으로 설정
            if [ $# -eq 1 ]; then
                VERSION_TYPE="patch"
            fi
            ;;
        major|minor|patch)
            VERSION_TYPE=$arg
            ;;
        *)
            echo -e "${RED}Error: 알 수 없는 파라미터: $arg${NC}"
            echo -e "${YELLOW}사용법: $0 [major|minor|patch] [--yes|-yes|-y|-Y]${NC}"
            echo -e "${YELLOW}       $0 -y  (patch 버전 자동 증가)${NC}"
            echo -e "${YELLOW}이 스크립트는 meson.build 버전과 debian/changelog를 업데이트합니다.${NC}"
            exit 1
            ;;
    esac
done

# 버전 타입 확인
if [[ ! "$VERSION_TYPE" =~ ^(major|minor|patch)$ ]]; then
    echo -e "${RED}Error: 버전 타입은 major, minor, patch 중 하나여야 합니다.${NC}"
    exit 1
fi

# 새 버전 생성
NEW_VERSION=$(increment_version $CURRENT_VERSION $VERSION_TYPE)

# meson.build 버전 업데이트
echo -e "\n${YELLOW}meson.build 버전 업데이트 중...${NC}"
echo -e "${YELLOW}업데이트 전 meson.build 버전:${NC}"
grep -n "^project(\|version:" meson.build | head -n2

# project() 라인의 version만 안전하게 1회 치환 (다른 의존성의 version 필드는 보존)
awk 'BEGIN{done=0} {
  if (!done && $0 ~ /^project\(/ && $0 ~ /version: \047[^\047]*\047/) {
    sub(/version: \047[^\047]*\047/, "version: \047"ENVIRON["NEW_VER_STR"]"\047")
    done=1
  }
  print
}' NEW_VER_STR="${NEW_VERSION#v}" meson.build > meson.build.tmp && mv meson.build.tmp meson.build

echo -e "${YELLOW}업데이트 후 meson.build 버전:${NC}"
grep -n "^project(\|version:" meson.build | head -n2

# (선택) 추가 메타데이터 파일이 있다면 여기서 갱신 가능

# debian/changelog 업데이트
if [ -f "debian/changelog" ]; then
    echo -e "\n${YELLOW}debian/changelog 버전 업데이트 중...${NC}"
    
    # 현재 배포판 이름 가져오기 (기본값: unstable)
    DISTRIBUTION=$(head -n1 debian/changelog | awk '{print $3}' | tr -d ';' || echo "unstable")
    
    # 변경사항 수집 (베이스 브랜치와 dev 브랜치 간 차이)
    CHANGELOG_ENTRIES=""
    while IFS= read -r line; do
        # 커밋 메시지에서 feat:, fix:, chore: 등을 제거하고 정리
        CLEAN_MSG=$(echo "$line" | sed -E 's/^[a-f0-9]+ //' | sed -E 's/^(feat|fix|chore|docs|style|refactor|test|build):\s*//')
        if [ -n "$CLEAN_MSG" ]; then
            CHANGELOG_ENTRIES="${CHANGELOG_ENTRIES}  * ${CLEAN_MSG}\n"
        fi
    done < <(git --no-pager log --oneline origin/$BASE_BRANCH..origin/dev --pretty=format:"%h %s")
    
    # dch 명령어가 있는지 확인
    if command -v dch &> /dev/null; then
        # dch를 사용하여 새 엔트리 추가
        DEBEMAIL="${DEBEMAIL:-root@hamonikr.org}" \
        DEBFULLNAME="${DEBFULLNAME:-HamoniKR}" \
        dch --package hamonikr-chatbot --newversion "${NEW_VERSION#v}" --distribution "$DISTRIBUTION" --noedit "Release ${NEW_VERSION}"
        
        # 변경사항 추가
        if [ -n "$CHANGELOG_ENTRIES" ]; then
            echo -e "$CHANGELOG_ENTRIES" | while IFS= read -r entry; do
                if [ -n "$entry" ]; then
                    dch --append "$entry"
                fi
            done
        fi
    else
        # dch가 없으면 수동으로 업데이트
        echo -e "${YELLOW}dch 명령어가 없습니다. 수동으로 debian/changelog를 업데이트합니다.${NC}"
        
        # 현재 날짜를 debian changelog 형식으로
        CHANGELOG_DATE=$(date -R)
        
        # 새 changelog 엔트리 생성
        NEW_ENTRY="hamonikr-chatbot (${NEW_VERSION#v}) $DISTRIBUTION; urgency=medium\n\n"
        if [ -n "$CHANGELOG_ENTRIES" ]; then
            NEW_ENTRY="${NEW_ENTRY}${CHANGELOG_ENTRIES}"
        else
            NEW_ENTRY="${NEW_ENTRY}  * Release ${NEW_VERSION}\n"
        fi
        NEW_ENTRY="${NEW_ENTRY}\n -- ${DEBFULLNAME:-HamoniKR} <${DEBEMAIL:-root@hamonikr.org}>  $CHANGELOG_DATE\n\n"
        
        # 기존 changelog 백업
        cp debian/changelog debian/changelog.bak
        
        # 새 엔트리를 파일 맨 위에 추가
        echo -e "$NEW_ENTRY" > debian/changelog.tmp
        cat debian/changelog.bak >> debian/changelog.tmp
        mv debian/changelog.tmp debian/changelog
    fi
    
    echo -e "${YELLOW}debian/changelog 업데이트 완료${NC}"
    head -n6 debian/changelog
fi

# 변경사항 요약 표시
echo -e "\n${YELLOW}변경사항 요약:${NC}"
git --no-pager log --oneline origin/$BASE_BRANCH..origin/dev

echo -e "\n${YELLOW}현재 버전: ${NC}$CURRENT_VERSION"
echo -e "${YELLOW}새로운 버전: ${NC}$NEW_VERSION"
echo -e "\n${GREEN}릴리즈 프로세스를 시작합니다...${NC}"

# 사용자 확인
if [ "$AUTO_YES" = true ]; then
    echo -e "\n${YELLOW}--yes 옵션이 설정되어 릴리즈를 자동으로 진행합니다.${NC}"
else
    read -p "계속 진행하시겠습니까? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}릴리즈가 취소되었습니다.${NC}"
        exit 1
    fi
fi

# 버전 변경사항 커밋
echo -e "\n${YELLOW}버전 변경사항 커밋${NC}"
git add meson.build
if [ -f "debian/changelog" ]; then
    git add debian/changelog
fi
git commit -m "chore: bump version to ${NEW_VERSION}"

# 릴리즈 프로세스 실행
echo -e "\n${YELLOW}1. ${BASE_BRANCH} 브랜치로 전환${NC}"
git checkout $BASE_BRANCH

echo -e "\n${YELLOW}2. ${BASE_BRANCH} 브랜치 업데이트${NC}"
git pull origin $BASE_BRANCH

echo -e "\n${YELLOW}3. dev 브랜치 머지${NC}"
git merge dev

echo -e "\n${YELLOW}4. 새로운 태그 생성${NC}"
git tag -a $NEW_VERSION -m "Release $NEW_VERSION"

echo -e "\n${YELLOW}5. 변경사항 푸시${NC}"
git push origin $BASE_BRANCH

echo -e "\n${YELLOW}6. 태그 푸시${NC}"
git push origin $NEW_VERSION

echo -e "\n${YELLOW}7. dev 브랜치로 복귀${NC}"
git checkout dev

echo -e "\n${YELLOW}8. dev 브랜치에 ${BASE_BRANCH}의 변경사항 동기화${NC}"
git merge $BASE_BRANCH
git push origin dev

echo -e "\n${GREEN}릴리즈 완료! 새 버전 ${NEW_VERSION}이 성공적으로 배포되었습니다.${NC}"
echo -e "${YELLOW}GitHub에서 릴리즈 노트를 작성하는 것을 잊지 마세요!${NC}"
