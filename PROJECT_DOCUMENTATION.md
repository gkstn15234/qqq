# 🤖 오코노미 (okonomis.com) AI 뉴스 자동화 시스템

## 📋 프로젝트 개요

오코노미는 AI 기반 자동화 뉴스 사이트로, 웹 스크래핑, AI 기사 재작성, 이미지 최적화, 자동 배포가 통합된 완전 자동화 시스템입니다.

### 🎯 주요 기능
- **AI 기사 재작성**: OpenAI GPT-4o-mini를 활용한 완전 새로운 기사 생성
- **자동 카테고리 분류**: 자동차(`automotive`) / 경제(`economy`) 자동 분류
- **이미지 최적화**: Cloudflare Images를 통한 CDN 최적화
- **SEO 최적화**: Google News, 구조화 데이터, 다중 사이트맵 지원
- **자동 배포**: GitHub Actions + Cloudflare Pages 연동
- **이메일 보고서**: 처리 결과 자동 이메일 발송

## 🏗️ 시스템 아키텍처

```
[사이트맵 크롤링] → [AI 기사 재작성] → [이미지 업로드] → [파일 생성] → [자동 배포]
        ↓                ↓               ↓            ↓           ↓
   [RSS 파싱]      [OpenAI API]   [Cloudflare]   [GitHub]  [Cloudflare Pages]
                                                     ↓
                                              [이메일 보고서]
```

### 🔄 자동화 플로우

1. **GitHub Actions 트리거** (수동 또는 스케줄링)
2. **사이트맵 다운로드** (`https://www.reportera.co.kr/news-sitemap.xml`)
3. **기사 URL 추출** (XML 파싱)
4. **중복 체크** (SQLite DB + 파일 시스템)
5. **기사 콘텐츠 추출** (BeautifulSoup)
6. **AI 재작성**:
   - 제목 재작성 (구조 유지, 내용 변경)
   - 본문 완전 재작성 (새로운 시각과 표현)
   - 태그 자동 생성
7. **이미지 처리**:
   - 원본 이미지 다운로드
   - Cloudflare Images 업로드
   - 콘텐츠 내 랜덤 배치
8. **마크다운 생성** (SEO 메타데이터 포함)
9. **Git 커밋/푸시**
10. **Cloudflare Pages 자동 배포**
11. **이메일 보고서 발송**

## 📁 프로젝트 구조

```
blogai2/
├── 🤖 AI & 자동화
│   ├── ai_scraper.py           # 메인 AI 스크래퍼
│   ├── send_email.py           # 이메일 보고서 시스템
│   ├── processed_articles.db   # 처리된 기사 DB (SQLite)
│   └── requirements.txt        # Python 의존성
│
├── ⚙️ GitHub Actions
│   └── .github/workflows/
│       ├── auto-scraper.yml    # 자동화 워크플로우
│       └── hugo.yml.disabled   # Hugo 배포 (비활성화)
│
├── 🎨 Hugo 사이트
│   ├── config.yaml            # Hugo 설정
│   ├── layouts/               # 템플릿 시스템
│   │   ├── _default/          # 기본 레이아웃
│   │   │   ├── baseof.html    # 베이스 템플릿
│   │   │   ├── single.html    # 기사 페이지
│   │   │   ├── list.html      # 카테고리 페이지
│   │   │   └── rss.xml        # RSS 피드
│   │   ├── index.html         # 메인 페이지
│   │   ├── partials/          # 재사용 컴포넌트
│   │   │   ├── head.html      # <head> 태그
│   │   │   ├── header.html    # 헤더
│   │   │   ├── footer.html    # 푸터
│   │   │   └── critical-css.html # 인라인 CSS
│   │   ├── shortcodes/        # Hugo 숏코드
│   │   │   ├── webp-image.html    # WebP 이미지
│   │   │   └── discover-image.html # 구글 디스커버 이미지
│   │   └── sitemap templates/ # 사이트맵 (7개)
│   │       ├── sitemap.xml    # 메인 사이트맵 인덱스
│   │       ├── index.postsitemap.xml     # 기사 사이트맵
│   │       ├── index.sitemapnews.xml     # Google News 사이트맵
│   │       ├── index.sitemapgeneral.xml  # 일반 사이트맵
│   │       ├── index.sitemaplocal.xml    # 지역 사이트맵
│   │       ├── index.sitemapauthors.xml  # 작성자 사이트맵
│   │       ├── index.sitemappages.xml    # 페이지 사이트맵
│   │       └── index.sitemapvideo.xml    # 비디오 사이트맵
│   │
│   ├── content/               # 콘텐츠 파일
│   │   ├── automotive/        # 자동차 기사
│   │   ├── economy/           # 경제 기사
│   │   ├── authors/           # 작성자 정보
│   │   ├── about.md           # 회사 소개
│   │   ├── contact.md         # 연락처
│   │   ├── privacy.md         # 개인정보처리방침
│   │   ├── terms.md           # 이용약관
│   │   └── editorial-guidelines.md # 편집 지침
│   │
│   └── static/               # 정적 파일
│       ├── css/
│       │   └── style.css     # 메인 스타일
│       ├── js/
│       │   └── main.js       # JavaScript
│       ├── images/           # 이미지 파일
│       ├── robots.txt        # 검색엔진 크롤링 설정
│       └── _headers          # Cloudflare 헤더 설정
│
├── 🚀 배포 설정
│   ├── .cloudflare/
│   │   └── pages.toml        # Cloudflare Pages 설정
│   ├── _redirects            # URL 리다이렉트 규칙
│   └── public/               # 빌드 결과물 (자동 생성)
│
└── 📚 문서
    ├── README.md             # 기본 사용법
    ├── SETUP_GUIDE.md        # 설정 가이드
    └── PROJECT_DOCUMENTATION.md # 이 문서
```

## 🔧 기술 스택

### Backend & 자동화
- **Python 3.11+**: 메인 언어
- **OpenAI GPT-4o-mini**: AI 기사 재작성
- **BeautifulSoup4**: 웹 스크래핑
- **SQLite**: 중복 방지 데이터베이스
- **GitHub Actions**: CI/CD 자동화

### Frontend & CMS
- **Hugo 0.147.9**: 정적 사이트 생성기
- **Go Templates**: 템플릿 엔진
- **Bootstrap 5**: CSS 프레임워크
- **Vanilla JavaScript**: 클라이언트 스크립트

### 인프라 & 서비스
- **Cloudflare Pages**: 호스팅 & CDN
- **Cloudflare Images**: 이미지 최적화 & CDN
- **GitHub**: 소스 코드 & 버전 관리
- **Gmail SMTP**: 이메일 발송

## ⚙️ 환경 설정

### 1. GitHub Secrets 설정

Repository → Settings → Secrets and variables → Actions

| Secret Name | 설명 | 필수 여부 |
|------------|------|----------|
| `OPENAI_API_KEY` | OpenAI API 키 | ✅ 필수 |
| `CLOUDFLARE_API_TOKEN` | Cloudflare Images API 토큰 | 🔶 권장 |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare 계정 ID | 🔶 권장 |
| `SENDER_EMAIL` | Gmail 발송자 이메일 | 🔶 권장 |
| `SENDER_PASSWORD` | Gmail 앱 비밀번호 | 🔶 권장 |
| `RECIPIENT_EMAIL` | 보고서 수신 이메일 | 🔶 권장 |

### 2. Cloudflare Pages 설정

#### 빌드 설정
```yaml
Build command: hugo --minify --gc
Build output directory: public
Root directory: / (루트)
```

#### 환경 변수
```
HUGO_VERSION=0.147.9
HUGO_ENV=production
HUGO_ENVIRONMENT=production
NODE_VERSION=18
```

## 🚀 사용법

### 수동 실행
1. GitHub Actions 탭으로 이동
2. "Auto Content Scraper" 워크플로우 선택
3. "Run workflow" 클릭

### 자동 스케줄링 (옵션)
`.github/workflows/auto-scraper.yml`에 cron 추가:
```yaml
on:
  schedule:
    - cron: '0 */6 * * *'  # 6시간마다 실행
```

### 로컬 개발
```bash
# 의존성 설치
pip install -r requirements.txt

# Hugo 서버 실행
hugo server -D

# 스크래퍼 테스트 실행
python ai_scraper.py
```

## 📊 데이터 플로우

### 입력 데이터
1. **사이트맵 XML**: `https://www.reportera.co.kr/news-sitemap.xml`
2. **기사 URL**: 사이트맵에서 추출된 개별 기사 링크
3. **원본 콘텐츠**: HTML에서 추출한 제목, 본문, 이미지

### 처리 과정
1. **중복 체크**: URL 해시 기반 SQLite DB 조회
2. **AI 처리**:
   - 제목: 구조 유지하면서 내용 변경
   - 본문: 완전 새로운 시각으로 재작성
   - 태그: 기존 + AI 생성 추가 태그
3. **카테고리 분류**: 키워드 기반 자동 분류
4. **이미지 처리**: Cloudflare Images 업로드 + CDN 최적화

### 출력 데이터
1. **마크다운 파일**: YAML front matter + 본문
2. **SQLite 레코드**: 처리 완료 기사 정보
3. **Git 커밋**: 자동 커밋 메시지
4. **이메일 보고서**: 처리 결과 통계

## 🎨 테마 & 디자인

### 레이아웃 구조
- **메인 페이지**: 헤드라인 + 주요 기사 + 최신 뉴스
- **기사 페이지**: 브레드크럼 + 본문 + 관련 기사 + 사이드바
- **카테고리 페이지**: 카테고리별 기사 목록
- **반응형 디자인**: 모바일 우선 설계

### SEO 최적화
- **구조화 데이터**: NewsArticle, Organization 스키마
- **Open Graph**: 소셜 미디어 최적화
- **Google News**: 전용 사이트맵 및 메타데이터
- **다중 사이트맵**: 용도별 7개 사이트맵 생성

## 🔒 보안 & 성능

### 보안 조치
- **API 키 보호**: GitHub Secrets 사용
- **CORS 설정**: Cloudflare 헤더 설정
- **입력 검증**: 스크래핑 데이터 검증 및 정리

### 성능 최적화
- **이미지 최적화**: Cloudflare Images + WebP 지원
- **캐시 설정**: Cloudflare Pages 캐시 규칙
- **CSS 인라인**: Critical CSS 인라인화
- **지연 로딩**: 이미지 lazy loading

## 📈 모니터링 & 로깅

### 자동 모니터링
- **이메일 보고서**: 처리 결과 자동 발송
- **GitHub Actions 로그**: 상세 실행 로그
- **DB 통계**: 누적 처리 통계

### 오류 처리
- **AI API 재시도**: 최대 3회 재시도
- **이미지 업로드 실패**: 원본 URL 사용
- **스크래핑 실패**: 건너뛰고 계속 진행

## 🛠️ 커스터마이징

### 새로운 카테고리 추가
1. `ai_scraper.py`의 `categorize_article()` 함수 수정
2. `content/` 폴더에 새 카테고리 디렉토리 생성
3. 사이트맵 템플릿에 새 카테고리 추가
4. 메뉴 설정 (`config.yaml`) 업데이트

### AI 모델 변경
`config.yaml` 또는 GitHub Secrets에서 `OPENAI_MODEL` 설정:
- `gpt-3.5-turbo`: 빠르고 경제적
- `gpt-4o-mini`: 균형 잡힌 성능 (기본값)
- `gpt-4o`: 최고 품질

### 디자인 커스터마이징
- `static/css/style.css`: 메인 스타일
- `layouts/partials/critical-css.html`: 인라인 CSS
- `layouts/`: Hugo 템플릿 수정

## 🚨 문제 해결

### 일반적인 문제

1. **AI 재작성 실패**
   - OpenAI API 키 확인
   - API 사용량 한도 확인
   - 네트워크 연결 확인

2. **이미지 표시 안됨**
   - Cloudflare Images 설정 확인
   - variant 설정 확인 (기본 URL 사용)
   - 원본 이미지 URL 접근성 확인

3. **빌드 실패**
   - Hugo 버전 확인 (0.147.9 권장)
   - YAML front matter 문법 오류 확인
   - 이미지 경로 확인

4. **중복 기사 생성**
   - SQLite DB 초기화: `rm processed_articles.db`
   - 해시 알고리즘 확인
   - URL 정규화 확인

### 로그 확인 방법
1. **GitHub Actions**: Repository → Actions 탭
2. **Cloudflare Pages**: Cloudflare Dashboard → Pages → Deployments
3. **이메일 보고서**: 설정된 수신 이메일 확인

## 📞 지원 & 연락처

- **개발자**: 윤신애
- **이메일**: hangil9910@gmail.com
- **회사**: 오코노미
- **사이트**: https://okonomis.com

---
*이 문서는 오토코미 AI 뉴스 자동화 시스템의 전체 구조와 사용법을 설명합니다.*
*최종 업데이트: 2025년 7월 20일* 