# HamoniKR Chatbot Virtual Environment Setup

## 문제 해결 방안

HamoniKR Chatbot에서 발생한 OpenAI 라이브러리 버전 호환성 문제를 해결하기 위해 가상환경을 자동으로 관리하는 스마트 런처를 구현했습니다.

## 문제점

1. **OpenAI 라이브러리 버전 충돌**: 사용자가 설치한 `pip` 패키지가 시스템 패키지와 충돌
2. **의존성 버전 불일치**: `proxies` 파라미터 등 API 변경으로 인한 호환성 문제
3. **GTK 바인딩 접근**: 가상환경에서 시스템 GTK 패키지 접근 필요

## 해결책

### 1. 스마트 런처 시스템

패키지의 실행 파일(`/usr/bin/hamonikr-chatbot`)이 자동으로:

- 사용자 환경의 패키지 충돌을 감지
- 필요시 가상환경을 자동 생성/관리
- 적절한 OpenAI 버전 설치
- GTK 시스템 패키지 접근 보장

### 2. 버전 제약 명시

**requirements.txt**:
```
openai>=1.12.0,<2.0.0
packaging>=20.0
requests>=2.25.0
tqdm>=4.60.0
Babel>=2.9.0
pillow>=8.0.0
```

**debian/control**:
```
python3-openai (>= 1.12.0),
python3-packaging,
```

## 구현된 스크립트들

### 1. 개발용 스크립트

- `scripts/setup-venv-system.sh`: 시스템 패키지 접근 가능한 가상환경 설정
- `scripts/run-dev.sh`: 개발 환경에서 실행
- `scripts/hamonikr-chatbot-smart`: 스마트 런처 (개발/배포 겸용)

### 2. 배포용 스크립트

- `src/hamonikr-chatbot-launcher.in`: 패키지 설치 시 `/usr/bin/hamonikr-chatbot`로 설치됨

## 사용법

### 개발 환경

```bash
# 가상환경 설정
./scripts/setup-venv-system.sh

# 개발 버전 실행
./scripts/run-dev.sh

# 또는 스마트 런처 사용
./scripts/hamonikr-chatbot-smart --debug
```

### 사용자 환경

설치된 패키지는 자동으로 환경을 관리하므로 사용자는 단순히:

```bash
hamonikr-chatbot
```

실행하면 됩니다.

## 동작 원리

1. **충돌 감지**: 사용자 설치 패키지(`pip --user`) 확인
2. **호환성 검사**: 시스템 OpenAI 버전 확인
3. **환경 선택**:
   - 충돌/비호환 → 가상환경 사용
   - 깨끗한 환경 → 시스템 패키지 사용
4. **자동 설정**: 필요시 가상환경 생성 및 패키지 설치
5. **실행**: 적절한 환경에서 애플리케이션 실행

## 가상환경 위치

```
$HOME/.local/share/hamonikr-chatbot-venv/
```

## 장점

1. **투명성**: 사용자가 별도 설정 불필요
2. **안전성**: 시스템 패키지와 격리
3. **효율성**: 필요할 때만 가상환경 사용
4. **호환성**: GTK 등 시스템 패키지 접근 보장
5. **유지보수**: 자동 업데이트 및 관리

## 패키지 빌드 시 주의사항

1. `src/hamonikr-chatbot-launcher.in`의 placeholders 교체:
   - `@VERSION@` → 실제 버전
   - `@PKGDATA_DIR@` → `/usr/share/hamonikr-chatbot`
   - `@LOCALE_DIR@` → `/usr/share/locale`

2. 실행 파일을 `/usr/bin/hamonikr-chatbot`로 설치

3. requirements.txt를 패키지 데이터에 포함

## 문제 해결

사용자 환경에서 문제 발생 시:

```bash
# 가상환경 재설정
rm -rf ~/.local/share/hamonikr-chatbot-venv

# 충돌 패키지 제거
pip3 uninstall openai httpx anyio

# 재실행
hamonikr-chatbot
```

## 미래 개선사항

1. 버전별 캐시 디렉토리 분리
2. 자동 업데이트 메커니즘
3. 상세한 로깅 시스템
4. 의존성 Lock 파일 지원