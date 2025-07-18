# 🤖 AI 기반 자동 블로그 시스템 설정 가이드

## 🎯 시스템 개요

이 시스템은 다음과 같이 작동합니다:

```
n8n 스케줄 → GitHub Actions 트리거 → AI 스크래퍼 실행 → 
기사 추출 → AI 재작성 → Cloudflare 이미지 업로드 → 
이미지 랜덤 배치 → AI 태그 생성 → 마크다운 저장 → 
Git 커밋/푸시 → Cloudflare Pages 자동 배포
```

## 🔧 필요한 API 키 및 설정

### 1. OpenAI API 키 (필수)
- **용도**: 기사 AI 재작성, AI 태그 생성
- **획득 방법**: [OpenAI Platform](https://platform.openai.com/api-keys)
- **비용**: GPT-3.5-turbo 기준 매우 저렴 (기사당 약 100-200원)

### 2. Cloudflare API 토큰 (선택사항)
- **용도**: 이미지 자동 업로드 및 CDN 최적화
- **획득 방법**: 
  1. Cloudflare Dashboard → My Profile → API Tokens
  2. "Create Token" → "Cloudflare Images" 템플릿 사용
  3. Account 및 Zone 권한 설정

### 3. Cloudflare Account ID (선택사항)
- **획득 방법**: Cloudflare Dashboard → 우측 사이드바에서 확인

### 4. GitHub Personal Access Token
- **용도**: n8n에서 GitHub Actions 트리거
- **권한**: `repo`, `workflow`

## 📋 GitHub Repository Secrets 설정

Repository → Settings → Secrets and variables → Actions → New repository secret

| Secret Name | 설명 | 필수 여부 |
|------------|------|----------|
| `OPENAI_API_KEY` | OpenAI API 키 | ✅ 필수 |
| `CLOUDFLARE_API_TOKEN` | Cloudflare Images API 토큰 | 🔶 선택 |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare 계정 ID | 🔶 선택 |

## 🤖 n8n 워크플로우 설정

### 간단한 JSON 워크플로우:

```json
{
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "hours",
              "hoursInterval": 8
            }
          ]
        }
      },
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [420, 300],
      "id": "schedule-trigger",
      "name": "8시간마다 실행"
    },
    {
      "parameters": {
        "url": "https://api.github.com/repos/gkstn15234/blogai2/dispatches",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "event_type",
              "value": "scrape-content"
            },
            {
              "name": "client_payload",
              "value": "={{ { \"sitemap_url\": \"https://www.reportera.co.kr/news-sitemap.xml\", \"triggered_by\": \"n8n-schedule\", \"timestamp\": $now.toISO() } }}"
            }
          ]
        }
      },
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.1,
      "position": [640, 300],
      "id": "github-trigger",
      "name": "GitHub Actions 트리거",
      "credentials": {
        "httpHeaderAuth": {
          "id": "github-auth",
          "name": "GitHub Header Auth"
        }
      }
    }
  ],
  "connections": {
    "8시간마다 실행": {
      "main": [
        [
          {
            "node": "GitHub Actions 트리거",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
```

### n8n 인증 설정:
1. **Credential Type**: HTTP Header Auth
2. **Name**: `Authorization`
3. **Value**: `Bearer YOUR_GITHUB_TOKEN`

## 🚀 시스템 테스트

### 1. 수동 테스트
GitHub Repository → Actions → "Auto Content Scraper" → "Run workflow"

### 2. 로그 확인
- **GitHub Actions**: 각 단계별 진행 상황 확인
- **n8n**: 실행 기록 및 성공/실패 확인
- **Cloudflare Pages**: 자동 배포 상태 확인

## 🎛️ 시스템 조정

### 스케줄 변경
n8n에서 Schedule Trigger 노드 설정:
- **매 2시간**: `hoursInterval: 2`
- **매일 오전 9시**: `cronExpression: "0 9 * * *"`
- **매 30분**: `minutesInterval: 30`

### 처리할 기사 수 조정
`ai_scraper.py` 파일에서:
```python
# 최신 20개 기사만 처리 (뉴스 사이트맵이므로)
urls = urls[:20]  # 이 숫자를 조정
```

### AI 모델 변경
```python
model="gpt-4o-mini"  # 현재 설정 (빠르고 효율적)
# 다른 옵션: "gpt-3.5-turbo", "gpt-4" (더 비쌈)
```

## 💰 예상 비용

### OpenAI API (GPT-4o-mini)
- **기사 재작성**: 약 1,000 토큰/기사 × $0.00015/1K토큰 = 기사당 약 0.15원
- **태그 생성**: 약 100 토큰/기사 × $0.00015/1K토큰 = 기사당 약 0.015원
- **일일 20기사 기준**: 약 3-5원/일 (매우 저렴!)

### Cloudflare Images
- **무료 계층**: 월 100,000건 무료
- **유료**: $5/월 for 500,000건

### 총 예상 비용
- **최소** (AI만): 월 100-200원 (매우 저렴!)
- **풀옵션** (AI + Cloudflare): 월 5,100-5,200원

## 🔍 모니터링 및 디버깅

### 로그 확인 포인트
1. **n8n 실행 로그**: 웹훅 전송 성공 여부
2. **GitHub Actions 로그**: 각 단계별 상세 진행 상황
3. **AI 재작성 결과**: 품질 및 정확성 검토
4. **이미지 업로드 상태**: Cloudflare 성공/실패

### 문제 해결
- **AI 재작성 실패**: API 키 확인, 크레딧 잔액 확인
- **이미지 업로드 실패**: Cloudflare 토큰 권한 확인
- **중복 기사**: 해시 기반 중복 방지 시스템 작동 중

## 🎉 완료!

설정이 완료되면 시스템이 자동으로:
1. **정기적으로** 새 기사를 스크래핑
2. **AI로 재작성**하여 독창적인 콘텐츠 생성
3. **이미지를 최적화**하여 빠른 로딩
4. **SEO 태그 자동 생성**
5. **자동 배포**로 즉시 사이트 업데이트

완전한 **무인 자동화 블로그 시스템** 완성! 🚀 