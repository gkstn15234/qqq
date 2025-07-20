import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import re
import os
from datetime import datetime, timezone, timedelta
import time
import random
import sys
import hashlib
import json
import base64
from urllib.parse import urlparse, urljoin
import sqlite3
from unidecode import unidecode

# AI 관련 import
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

def get_env_var(name, default=None):
    """환경변수 가져오기"""
    return os.environ.get(name, default)

def rebuild_hugo_site():
    """Hugo 사이트 재빌드 (새 기사를 메인페이지에 반영)"""
    try:
        import subprocess
        print("🔨 Rebuilding Hugo site to reflect new articles...")
        
        # Hugo 빌드 명령 실행
        result = subprocess.run(
            ['hugo', '--gc', '--minify'], 
            capture_output=True, 
            text=True, 
            timeout=30,
            cwd=os.getcwd()
        )
        
        if result.returncode == 0:
            print("✅ Hugo site rebuilt successfully!")
            return True
        else:
            print(f"⚠️ Hugo build warning: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️ Hugo build timed out after 30 seconds")
        return False
    except FileNotFoundError:
        print("⚠️ Hugo not found - install Hugo or ensure it's in PATH")
        return False
    except Exception as e:
        print(f"⚠️ Hugo rebuild error: {e}")
        return False

def init_processed_db():
    """처리된 기사 추적을 위한 SQLite DB 초기화"""
    db_path = 'processed_articles.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            hash TEXT,
            processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    return db_path

def is_article_processed(url, title, article_hash):
    """기사가 이미 처리되었는지 DB에서 확인 (강화된 URL 체크)"""
    db_path = 'processed_articles.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. URL 직접 체크 (가장 확실한 방법)
    cursor.execute('SELECT COUNT(*) FROM processed_articles WHERE url = ?', (url,))
    url_count = cursor.fetchone()[0]
    
    if url_count > 0:
        conn.close()
        return True
    
    # 2. 해시 기반 체크 (제목+URL 조합)
    cursor.execute('SELECT COUNT(*) FROM processed_articles WHERE hash = ?', (article_hash,))
    hash_count = cursor.fetchone()[0]
    
    conn.close()
    return hash_count > 0

def mark_article_processed(url, title, article_hash):
    """기사를 처리됨으로 DB에 기록"""
    db_path = 'processed_articles.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO processed_articles (url, title, hash)
            VALUES (?, ?, ?)
        ''', (url, title, article_hash))
        
        conn.commit()
    except Exception as e:
        print(f"⚠️ Failed to mark article as processed: {e}")
    finally:
        conn.close()

def clean_filename(title):
    """제목을 파일명으로 사용할 수 있도록 정리"""
    filename = re.sub(r'[^\w\s-]', '', title)
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename.strip('-').lower()

def create_url_slug(title):
    """제목을 URL 슬러그로 변환 (영문, 3~4단어로 제한)"""
    try:
        # 한글을 영문으로 변환 (unidecode 사용)
        slug = unidecode(title)
        # 특수문자 제거, 공백을 하이픈으로
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        # 소문자로 변환, 앞뒤 하이픈 제거
        slug = slug.strip('-').lower()
        
        # 3~4단어로 제한 (하이픈으로 구분된 단어 기준)
        words = slug.split('-')
        if len(words) > 4:
            # 첫 4개 단어만 사용
            slug = '-'.join(words[:4])
        elif len(words) < 3 and len(words) > 0:
            # 2단어 이하인 경우 그대로 유지 (너무 짧지 않도록)
            pass
        
        # 최대 길이 제한 (안전장치)
        if len(slug) > 50:
            slug = slug[:50].rstrip('-')
            
        return slug
    except:
        # unidecode 실패 시 기본 방식 사용
        return clean_filename(title)

def categorize_article(title, content, tags):
    """기사를 카테고리별로 분류"""
    title_lower = title.lower()
    content_lower = content.lower()
    all_tags = [tag.lower() for tag in tags]
    
    # 자동차 관련 키워드
    car_keywords = [
        'car', 'auto', 'vehicle', '자동차', '차량', '승용차', '트럭', '버스',
        '현대', '기아', '삼성', '테슬라', 'tesla', 'hyundai', 'kia',
        '전기차', 'ev', 'electric', '수소차', 'hydrogen',
        '엔진', '모터', '배터리', '충전', '주행', '운전',
        '폴드', 'fold', '갤럭시', 'galaxy', '스마트폰', 'smartphone'
    ]
    
    # 경제 관련 키워드  
    economy_keywords = [
        'economy', 'economic', '경제', '금융', '투자', '주식', '코스피', '증시',
        '달러', '원화', '환율', '금리', '인플레이션', '물가',
        '기업', '회사', '매출', '이익', '손실', '실적',
        '정책', '정부', '은행', '중앙은행'
    ]
    
    # 기술/IT 관련 키워드
    tech_keywords = [
        'tech', 'technology', 'it', '기술', '소프트웨어', '하드웨어',
        'ai', '인공지능', '머신러닝', '딥러닝', 
        '앱', 'app', '플랫폼', 'platform', '서비스',
        '구글', 'google', '애플', 'apple', '마이크로소프트', 'microsoft'
    ]
    
    # 키워드 매칭 점수 계산
    car_score = sum(1 for keyword in car_keywords if keyword in title_lower or keyword in content_lower or keyword in all_tags)
    economy_score = sum(1 for keyword in economy_keywords if keyword in title_lower or keyword in content_lower or keyword in all_tags)
    
    # automotive 또는 economy 카테고리만 사용
    if car_score >= economy_score:
        return 'automotive'
    else:
        return 'economy'

def get_article_hash(title, url):
    """기사의 고유 해시 생성 (중복 방지용)"""
    content = f"{title}{url}"
    return hashlib.md5(content.encode()).hexdigest()[:8]

def check_existing_articles(output_dir, article_hash, title, url):
    """강화된 기사 중복 체크 (서브디렉토리 포함) - URL 우선"""
    if not os.path.exists(output_dir):
        return False
    
    # 제목 기반 유사도 체크를 위한 정규화
    normalized_title = re.sub(r'[^\w\s]', '', title.lower()).strip()
    
    # 루트 디렉토리와 모든 서브디렉토리 검사
    for root, dirs, files in os.walk(output_dir):
        for filename in files:
            if filename.endswith('.md'):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # 1. URL 기반 체크 (최우선 - 가장 확실)
                        if f'source_url: "{url}"' in content:
                            return True
                        
                        # 2. 해시 기반 체크
                        if f"hash: {article_hash}" in content:
                            return True
                        
                        # 3. 제목 유사도 체크 (보완적)
                        title_match = re.search(r'title: "([^"]+)"', content)
                        if title_match:
                            existing_title = title_match.group(1)
                            existing_normalized = re.sub(r'[^\w\s]', '', existing_title.lower()).strip()
                            
                            # 제목이 95% 이상 유사하면 중복으로 판단
                            if normalized_title and existing_normalized:
                                title_words = set(normalized_title.split())
                                existing_words = set(existing_normalized.split())
                                if title_words and existing_words:
                                    similarity = len(title_words & existing_words) / len(title_words | existing_words)
                                    if similarity > 0.95:
                                        return True
                                
                except Exception:
                    continue
    return False

def create_manual_rewrite(original_content, title):
    """AI 실패 시 수동으로 기사 재작성 - 극단적 변형"""
    try:
        # 원본 콘텐츠를 문단별로 분리
        paragraphs = original_content.split('\n\n')
        rewritten_paragraphs = []
        
        # 문체 변형을 위한 표현 사전
        style_transforms = {
            "발표했다": ["공개했다", "밝혔다", "알렸다", "전했다", "공표했다"],
            "증가했다": ["늘어났다", "상승했다", "확대됐다", "성장했다", "오름세를 보였다"],
            "감소했다": ["줄어들었다", "하락했다", "축소됐다", "내림세를 보였다", "둔화됐다"],
            "계획이다": ["예정이다", "방침이다", "구상이다", "의도다", "계획을 세웠다"],
            "문제가": ["이슈가", "우려가", "쟁점이", "과제가", "난제가"],
            "중요하다": ["핵심적이다", "주요하다", "결정적이다", "필수적이다", "관건이다"],
            "진행됐다": ["이뤄졌다", "추진됐다", "실시됐다", "개최됐다", "펼쳐졌다"]
        }
        
        # 접속사 및 시작 표현 다양화
        connectors = [
            "한편", "또한", "이와 관련해", "특히", "더불어", "아울러", 
            "그런 가운데", "이런 상황에서", "주목할 점은", "눈여겨볼 대목은",
            "업계에 따르면", "전문가들은", "관계자들에 의하면"
        ]
        
        # 각 문단을 극단적으로 재구성
        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue
                
            sentences = paragraph.split('.')
            if len(sentences) > 1:
                rewritten_sentences = []
                
                for j, sentence in enumerate(sentences):
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    
                    # 1. 표현 사전을 활용한 어휘 변경
                    for original, alternatives in style_transforms.items():
                        if original in sentence:
                            import random
                            sentence = sentence.replace(original, random.choice(alternatives))
                    
                    # 2. 문장 구조 변형
                    if "는" in sentence and "이다" in sentence:
                        # "A는 B이다" → "B로 나타나는 것이 A다"
                        parts = sentence.split("는")
                        if len(parts) == 2:
                            subject = parts[0].strip()
                            predicate = parts[1].strip()
                            if "이다" in predicate:
                                predicate = predicate.replace("이다", "로 확인되는 것이")
                                sentence = f"{predicate} {subject}다"
                    
                    # 3. 숫자 표현 변형
                    import re
                    percent_pattern = r'(\d+)%'
                    sentence = re.sub(percent_pattern, lambda m: f"100명 중 {m.group(1)}명", sentence)
                    
                    # 4. 문장 시작 다양화
                    if j == 0 and i > 0:
                        connector = connectors[i % len(connectors)]
                        if not any(sentence.startswith(conn) for conn in connectors):
                            sentence = f"{connector} {sentence.lower()}"
                    
                    # 5. 질문형/감탄형 변형 (일부 문장을)
                    if j % 3 == 0 and "중요" in sentence:
                        sentence = sentence.replace("중요하다", "중요하지 않을까?")
                    elif "놀라운" in sentence or "주목" in sentence:
                        sentence = sentence + "!"
                    
                    rewritten_sentences.append(sentence)
                
                if rewritten_sentences:
                    # 문장 순서도 일부 변경
                    if len(rewritten_sentences) > 2:
                        # 마지막 문장을 앞으로 이동 (때때로)
                        if i % 2 == 0:
                            last_sentence = rewritten_sentences.pop()
                            rewritten_sentences.insert(0, last_sentence)
                    
                    rewritten_paragraphs.append('. '.join(rewritten_sentences) + '.')
            else:
                # 단일 문장도 변형
                paragraph = paragraph.strip()
                for original, alternatives in style_transforms.items():
                    if original in paragraph:
                        import random
                        paragraph = paragraph.replace(original, random.choice(alternatives))
                rewritten_paragraphs.append(paragraph)
        
        # 35~60대 독자층을 위한 기본 구조로 재구성 (H5 하나에 <br> 두 줄 + 썸네일 + 본문 + H2 소제목)
        rewritten_content = f"""##### **{title}의 핵심 내용 요약**<br>**업계 동향과 향후 전망 분석**

{chr(10).join(rewritten_paragraphs[:3])}

## 핵심 포인트

{chr(10).join(rewritten_paragraphs[3:6]) if len(rewritten_paragraphs) > 3 else ''}

## 상세 분석

{chr(10).join(rewritten_paragraphs[6:]) if len(rewritten_paragraphs) > 6 else ''}

**이번 이슈는 업계에 중요한 시사점을 제공하고 있으며**, 향후 동향에 대한 지속적인 관심이 필요해 보입니다.
"""
        
        return rewritten_content.strip()
        
    except Exception as e:
        print(f"⚠️ Manual rewrite failed: {e}")
        # 최소한의 기본 구조라도 생성 (H5 하나에 <br> 두 줄 + H2 소제목)
        return f"""##### **업계 주요 동향 핵심 분석**<br>**{title} 영향과 시장 전망**

본 기사는 현재 업계의 주요 동향을 다루고 있습니다.

## 핵심 포인트

관련 업계에서는 이번 사안에 대해 **높은 관심을 보이고 있으며**, 다양한 의견이 제기되고 있는 상황입니다.

## 향후 전망

이러한 변화는 시장에 중대한 영향을 미칠 것으로 예상되며, **관련 기업들의 대응 전략이 주목받고 있습니다**.

*본 기사는 신뢰할 수 있는 정보를 바탕으로 작성되었습니다.*
"""

def upload_to_cloudflare_images(image_url, api_token, account_id):
    """Cloudflare Images에 이미지 업로드"""
    try:
        # 이미지 다운로드
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        img_response = requests.get(image_url, headers=headers, timeout=10)
        img_response.raise_for_status()
        
        # Cloudflare Images API 호출
        upload_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/images/v1"
        
        files = {
            'file': ('image.jpg', img_response.content, 'image/jpeg')
        }
        headers = {
            'Authorization': f'Bearer {api_token}'
        }
        
        response = requests.post(upload_url, files=files, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        if result.get('success'):
            # Cloudflare Images URL 반환 (새로운 account hash 사용)
            image_id = result['result']['id']
            account_hash = "BhPWbivJAhTvor9c-8lV2w"  # 새로운 account hash
            cloudflare_url = f"https://imagedelivery.net/{account_hash}/{image_id}/public"
            print(f"📸 Cloudflare image URL: {cloudflare_url}")
            return cloudflare_url
        else:
            print(f"❌ Cloudflare upload failed: {result}")
            return None  # 실패 시 None 반환
            
    except Exception as e:
        print(f"⚠️ Failed to upload image to Cloudflare: {e}")
        return None  # 실패 시 None 반환

def rewrite_with_ai(original_content, title, api_key, api_type="openai"):
    """AI를 사용하여 기사 재작성"""
    if not api_key:
        raise Exception("No AI API key provided - AI rewrite is mandatory")
    
    # 최대 3번 재시도
    for attempt in range(3):
        try:
            print(f"🤖 AI rewrite attempt {attempt + 1}/3...")
            if api_type == "openai" and HAS_OPENAI:
                client = OpenAI(api_key=api_key)
                
                prompt = f"""
다음 원본 기사를 분석하여 **완전히 새로운 관점과 문체**로 재창작해주세요.
원본 작성자가 자신의 글이라고 인식할 수 없을 정도로 **혁신적으로 변형**해주세요.

제목: {title}

원본 기사:
{original_content}

**극단적 변형 요구사항:**
1. **문체 완전 변경**: 원본이 딱딱하면 친근하게, 친근하면 전문적으로 바꿔주세요
2. **시작 각도 혁신**: 원본과 전혀 다른 관점에서 사건을 접근해주세요
3. **문장 구조 파괴**: 원본의 문장 패턴을 완전히 해체하고 재구성해주세요
4. **어휘 선택 변화**: 같은 의미의 다른 표현, 다른 뉘앙스로 바꿔주세요
5. **논리 흐름 재배치**: 정보 제시 순서를 완전히 재배열해주세요
6. **스타일 정체성 변경**: 마치 성격이 다른 기자가 쓴 것처럼 만들어주세요
7. **표현 기법 다변화**: 
   - 질문형/서술형/감탄형을 다양하게 활용
   - 비유와 은유 표현 추가
   - 숫자 표현 방식 변경 (예: "30%" → "10명 중 3명")
8. **감정 톤 변경**: 원본의 감정적 톤을 완전히 다르게 설정
9. **독자 관점 전환**: 다른 독자층에게 말하는 것처럼 톤앤매너 변경
10. **핵심 사실만 보존**: 날짜, 수치, 고유명사, 핵심 사실은 정확히 유지

**시인성 향상을 위한 굵게 처리 (최우선):**
- **핵심 키워드와 중요 정보**를 반드시 **굵게** 표시
- **수치, 날짜, 기업명, 제품명** 등은 모두 **굵게** 처리
- **주요 변화나 결론**은 **굵게** 강조
- **독자가 꼭 기억해야 할 내용**은 **굵게** 표시
- 문단마다 최소 2-3개의 **굵은 키워드** 포함
- **35-60대 독자층**이 핵심만 빠르게 파악할 수 있도록 **굵게** 활용

**문체 변형 예시:**
- 원본: "회사가 발표했다" → 변형: "**업체 측이 공개한** 바에 따르면"
- 원본: "증가했다" → 변형: "**상승세를 보이고** 있다", "**늘어나는 추세**다"
- 원본: "문제가 있다" → 변형: "**우려스러운 상황**이 벌어지고 있다"

**헤딩 구조 (절대 엄수):**
##### [첫 번째 줄 요약]<br>[두 번째 줄 요약]

**헤딩 사용 규칙:**
- H5(#####): 하나의 태그 안에 <br>로 두 줄 작성 (| 작대기 사용하지 않음)
- H2(##): 모든 소제목에 사용 (H3, H4, H6 절대 금지!)
- H1(#): 사용 금지 (Hugo에서 자동 생성)

**H2 소제목 작성 규칙:**
- 콜론(:), 느낌표(!), 물음표(?) 등 특수기호 사용 금지
- 자연스러운 명사형 또는 서술형으로 작성
- 예시: "주요 변화 동향", "시장 반응과 전망", "업계 분석 결과"

**기사 구조 (절대 준수):**
1. H5 요약: ##### **첫 번째 줄**<br>**두 번째 줄**
2. 도입 본문: 2-3개 문단 (H2 없이 바로 본문으로 시작, **굵은 키워드** 포함)
3. H2 소제목 + 본문 반복 (각 문단마다 **핵심 정보 굵게** 처리)

**H5 요약 필수 형식:**
##### **500마력 전기 SUV 국내 상륙 예고**<br>**럭셔리와 오프로드 능력 모두 갖춰**

**기사 시작 구조 예시:**
##### **핵심 내용 요약**<br>**부가 설명 요약**

업계에서는 이번 발표가 **시장에 큰 변화**를 가져올 것으로 전망하고 있다. 

관련 전문가들은 이러한 움직임이 향후 **업계 전반에 미칠 파급효과**를 주목하고 있으며, 다양한 분석이 제기되고 있는 상황이다.

특히 이번 사안은 **기존 시장 구조에 새로운 변수**로 작용할 것으로 예상되며, 관련 기업들의 **대응 전략**에도 관심이 집중되고 있다.

## 주요 변화 동향

(이후 H2 + 본문 반복, 모든 문단에 **중요 키워드 굵게** 처리...)

**최종 목표: 원본 작성자가 "이건 내 글이 아니야!"라고 할 정도로 완전히 다른 작품을 만들어주세요.**
같은 사건을 다룬 전혀 다른 기자의 독립적인 취재 기사처럼 작성해주되, **핵심 정보는 굵게 강조**하여 35-60대 독자층이 **빠르게 핵심을 파악**할 수 있도록 해주세요.
"""
                
                response = client.chat.completions.create(
                    model="gpt-4.1",  # gpt-4o-mini → gpt-4.1로 변경
                    messages=[
                        {"role": "system", "content": "당신은 창작 전문가입니다. 원본 텍스트를 완전히 새로운 스타일로 변형하여 원저작자도 인식할 수 없게 만드는 재창작의 달인입니다. 같은 사실을 전혀 다른 표현과 구조로 재탄생시키는 것이 당신의 특기입니다. 문체, 톤, 구조, 표현을 혁신적으로 바꿔서 완전히 새로운 작품을 만들어주세요. 특히 핵심 정보는 **굵게** 표시하여 35-60대 독자층이 빠르게 이해할 수 있도록 하는 것이 중요합니다."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.8
                )
                
                rewritten = response.choices[0].message.content.strip()
                # YAML 안전성을 위해 YAML 구분자만 정리 (따옴표는 보존)
                rewritten = rewritten.replace('```', '').replace('---', '—')  # YAML 구분자 문제 방지
                print(f"✅ AI rewrite successful on attempt {attempt + 1}")
                return rewritten
                
        except Exception as e:
            print(f"❌ AI rewrite attempt {attempt + 1} failed: {e}")
            if attempt < 2:  # 마지막 시도가 아니면 재시도
                time.sleep(2)  # 2초 대기 후 재시도
                continue
            else:
                print("🚨 All AI rewrite attempts failed - raising exception")
                raise Exception(f"AI rewrite failed after 3 attempts: {e}")
    
    raise Exception("AI rewrite failed - unexpected end of function")

def generate_ai_tags(title, content, existing_tags, api_key, api_type="openai"):
    """AI를 사용하여 추가 태그 생성"""
    if not api_key:
        print("⚠️ No AI API key - using default tags")
        return existing_tags + ["뉴스", "이슈"]
    
    for attempt in range(3):
        try:
            print(f"🏷️ AI tag generation attempt {attempt + 1}/3...")
            if api_type == "openai" and HAS_OPENAI:
                client = OpenAI(api_key=api_key)
                
                prompt = f"""
기사 내용을 분석하여 **독창적이고 차별화된** 태그 2개를 생성해주세요.
기존 태그와는 완전히 다른 관점에서 접근해주세요.

제목: {title}
내용: {content[:500]}...
기존 태그: {', '.join(existing_tags)}

**창의적 태그 생성 요구사항:**
1. 기존 태그와 중복되지 않는 새로운 관점
2. 해당 업계의 전문 용어나 트렌드 반영
3. 검색 키워드로 활용 가능한 실용적 태그
4. 35~60대 독자층이 관심 가질만한 주제

**태그 스타일 예시:**
- "미래전망", "업계동향", "전문가분석", "시장변화"
- "투자포인트", "소비트렌드", "기술혁신", "정책영향"

JSON 배열로만 응답: ["태그1", "태그2"]
"""
                
                response = client.chat.completions.create(
                    model="gpt-4.1",  # gpt-4o-mini → gpt-4.1로 변경
                    messages=[
                        {"role": "system", "content": "당신은 창의적 태그 생성 전문가입니다. 기존과는 완전히 다른 관점에서 독창적이고 차별화된 태그를 만들어내는 마케팅 전략가입니다. 독자의 관심을 끌고 검색 효과를 극대화하는 혁신적인 태그를 생성합니다."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=100,
                    temperature=0.7
                )
                
                result = response.choices[0].message.content.strip()
                # JSON 파싱 시도
                try:
                    new_tags = json.loads(result)
                    if isinstance(new_tags, list) and len(new_tags) >= 2:
                        print(f"✅ AI tag generation successful on attempt {attempt + 1}")
                        return existing_tags + new_tags[:2]
                except:
                    pass
                    
        except Exception as e:
            print(f"❌ AI tag generation attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(1)
                continue
            else:
                print("⚠️ All AI tag attempts failed - using default tags")
                return existing_tags + ["뉴스", "이슈"]
    
    return existing_tags + ["뉴스", "이슈"]

def rewrite_title_with_ai(original_title, content, api_key, api_type="openai"):
    """AI를 사용하여 제목 재작성 (구조 유지, 내용 변경)"""
    if not api_key:
        print("⚠️ No AI API key provided, keeping original title")
        return original_title
    
    for attempt in range(3):
        try:
            print(f"📝 AI title rewrite attempt {attempt + 1}/3...")
            if api_type == "openai" and HAS_OPENAI:
                client = OpenAI(api_key=api_key)
            
            prompt = f"""
원본 제목의 **구조와 형식을 100% 완벽하게 유지**하되, 본문 내용에 맞게 **따옴표 안의 내용만 변경**해주세요.

원본 제목: {original_title}

본문 내용 (핵심만):
{content[:1000]}...

**절대 엄수 요구사항:**
1. **따옴표 위치 완전 보존**: "큰따옴표", '작은따옴표' 위치와 개수 절대 변경 금지
2. **구두점 완전 보존**: ..(두 점), ,(쉼표), -(하이픈) 등 모든 특수기호 위치 그대로
3. **문장 패턴 완전 보존**: [인용문].. [설명], '[감정표현]' 패턴 100% 유지
4. **길이 패턴 유지**: 각 구간(인용문, 설명, 감정표현)의 길이를 원본과 비슷하게
5. **내용만 교체**: 따옴표 안의 단어들과 설명 부분만 본문에 맞게 자연스럽게 변경

**완벽한 구조 유지 예시:**
원본: "롤스로이스도 긴장하겠네".. 곧 한국 상륙하는 500마력 럭셔리 SUV, '기대감 폭발'
변형: "벤츠도 당황하겠어".. 내년 출시 예정인 800마력 전기 세단, '화제 집중'

원본: "이건 혁신이다".. 새로운 AI 기술 도입한 스마트폰, '관심 급증'  
변형: "정말 놀랍다".. 최신 배터리 탑재한 전기 트럭, '주목 폭발'

**절대 금지사항:**
- 따옴표 개수나 위치 변경
- 구두점(.., , 등) 위치나 개수 변경  
- 문장 구조([인용].. [설명], '[감정]') 변경
- 원본에 없는 새로운 구두점 추가

**목표: 원본 구조는 100% 동일하되, 본문 내용에 정확히 맞는 키워드로만 교체**

새로운 제목만 출력 (설명이나 부가 텍스트 없이):
"""
            
            response = client.chat.completions.create(
                model="gpt-4.1",  # gpt-4o-mini → gpt-4.1로 변경
                messages=[
                    {"role": "system", "content": "당신은 제목 구조 완벽 보존 전문가입니다. 원본 제목의 형식, 구두점, 따옴표 위치를 절대 변경하지 않고 오직 내용 키워드만 교체하는 것이 특기입니다. 구조 보존을 최우선으로 하며, 원본 패턴을 100% 유지합니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.5  # 더 일관된 결과를 위해 낮춤
            )
            
            new_title = response.choices[0].message.content.strip()
            # 앞뒤 시스템 따옴표만 제거 (내용의 따옴표는 보존)
            new_title = new_title.strip('"').strip("'")
            # YAML 구분자만 정리 (따옴표는 보존)
            new_title = new_title.replace('---', '—').replace('```', '')
            print(f"✅ AI title rewrite successful on attempt {attempt + 1}")
            print(f"📝 Title rewritten: {original_title[:50]}... → {new_title[:50]}...")
            return new_title
            
        except Exception as e:
            print(f"❌ AI title rewrite attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(1)
                continue
            else:
                print("⚠️ All AI title rewrite attempts failed - using original title")
                return original_title
    
    return original_title

def extract_content_from_url(url):
    """URL에서 기사 내용 추출 (새로운 구조 대응)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 제목 추출
        title_elem = soup.find('h1', class_='entry-title')
        if not title_elem:
            return None
        title = title_elem.get_text().strip()
        
        # 메타 정보 추출 - 항상 윤신애로 설정 (UTF-8 안전)
        author = "윤신애"
        
        # 태그 추출
        tags = ["뉴스", "이슈"]  # 기본 태그
        tags_section = soup.find('span', class_='tags-links')
        if tags_section:
            tag_links = tags_section.find_all('a', rel='tag')
            for tag_link in tag_links:
                tag_text = tag_link.get_text().strip()
                if tag_text not in tags:
                    tags.append(tag_text)
        
        # 내용 추출
        content_elem = soup.find('div', class_='entry-content')
        if not content_elem:
            return None
        
        # 광고 제거
        for ad in content_elem.find_all('div', class_='repoad'):
            ad.decompose()
        for ad in content_elem.find_all('ins', class_='adsbygoogle'):
            ad.decompose()
        
        # 공유 버튼 제거
        for share in content_elem.find_all('ul', class_='share-list'):
            share.decompose()
        
        # 이미지 URL 수집 (순서 무시하고 섞어서 수집 - 원본 위치와 완전히 다르게)
        images = []
        for img in content_elem.find_all('img'):
            img_src = img.get('src')
            if img_src and ('wp-content/uploads' in img_src or 'reportera.b-cdn.net' in img_src):
                # 절대 URL로 변환
                if img_src.startswith('//'):
                    img_src = 'https:' + img_src
                elif img_src.startswith('/'):
                    img_src = 'https://www.reportera.co.kr' + img_src
                elif not img_src.startswith('http'):
                    img_src = 'https://www.reportera.co.kr/' + img_src
                images.append(img_src)
        
        # 원본 이미지 순서를 완전히 섞어서 배치 (원본과 다르게)
        import random
        if images:
            random.shuffle(images)  # 이미지 순서 무작위로 섞기
        
        # 텍스트 내용 추출 (이미지 완전 제거 - 원본 위치 정보 삭제)
        paragraphs = []
        for elem in content_elem.children:
            if hasattr(elem, 'name') and elem.name:
                if elem.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5']:
                    # 이미지 태그 완전 제거 (원본 위치 정보 삭제)
                    for img in elem.find_all('img'):
                        img.decompose()
                    
                    # 피겨 태그도 제거 (이미지 캡션 포함)
                    for figure in elem.find_all('figure'):
                        figure.decompose()
                        
                    # <br> 태그를 줄바꿈으로 변환
                    for br in elem.find_all('br'):
                        br.replace_with('\n')
                    
                    text = elem.get_text().strip()
                    # 이미지 관련 텍스트 패턴 제거
                    text = re.sub(r'\[이미지.*?\]', '', text)
                    text = re.sub(r'\(사진.*?\)', '', text)
                    text = re.sub(r'사진=.*', '', text)
                    text = re.sub(r'이미지=.*', '', text)
                    
                    if text and not text.startswith('(adsbygoogle'):
                        if elem.name in ['h2', 'h3', 'h4', 'h5']:
                            # 소제목에서 특수기호 제거
                            clean_text = text.replace(':', '').replace('!', '').replace('?', '').replace('|', '').strip()
                            paragraphs.append(f"\n## {clean_text}\n")  # H2로 변환
                        else:
                            paragraphs.append(text)
        
        content = '\n\n'.join(paragraphs)
        
        # 요약문 생성 (YAML safe - 따옴표 보존)
        if paragraphs:
            description = paragraphs[0][:150] + "..."
            # YAML 안전성을 위한 기본 정리 (따옴표는 HTML 엔티티로 보존)
            description = description.replace('"', '&quot;').replace('\n', ' ').replace('\r', ' ')
            description = re.sub(r'\s+', ' ', description).strip()
        else:
            description = ""
        
        return {
            'title': title,
            'description': description,
            'content': content,
            'images': images,
            'url': url,
            'author': author,
            'tags': tags
        }
    
    except Exception as e:
        print(f"❌ Error extracting content from {url}: {e}")
        return None

def analyze_image_text_content(image_url, api_key):
    """AI Vision으로 이미지에 텍스트가 있는지 분석 (뉴스 관련 이미지 제외)"""
    if not api_key:
        return False  # API 키 없으면 텍스트 없다고 가정
    
    try:
        if HAS_OPENAI:
            client = OpenAI(api_key=api_key)
            
            # GPT-4.1로 먼저 시도, 실패하면 gpt-4o 사용
            models_to_try = ["gpt-4.1", "gpt-4o"]
            
            for model in models_to_try:
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "이 이미지를 분석해주세요:\n1. 뉴스 관련: '연합뉴스', '뉴스1', 'YONHAP', 'NEWS', '기자', '제공', '출처' 등 뉴스 기관 관련 텍스트나 로고가 있나요?\n2. 기타 텍스트: 한글, 영어, 숫자 등 기타 텍스트가 포함되어 있나요?\n\n뉴스 관련이 있으면 'NEWS_TEXT', 기타 텍스트가 있으면 'HAS_TEXT', 텍스트가 없으면 'NO_TEXT'로만 답변해주세요."
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": image_url
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=20
                    )
                    
                    result = response.choices[0].message.content.strip().upper()
                    
                    # 뉴스 관련 텍스트가 있으면 제외 (True 반환 = 텍스트 있음)
                    if "NEWS_TEXT" in result:
                        print(f"🚫 뉴스 관련 텍스트 감지로 제외 ({model}): {image_url[:50]}...")
                        return True  # 텍스트 있음으로 처리하여 제외
                    
                    # 기타 텍스트 확인
                    has_text = "HAS_TEXT" in result
                    print(f"🔍 이미지 텍스트 분석 ({model}): {image_url[:50]}... → {'텍스트 있음' if has_text else '텍스트 없음'}")
                    return has_text
                    
                except Exception as model_error:
                    if "gpt-4.1" in model:
                        print(f"⚠️ {model} Vision 지원 안함, gpt-4o로 재시도...")
                        continue  # 다음 모델 시도
                    else:
                        print(f"⚠️ {model} 이미지 분석 실패: {model_error}")
                        break  # gpt-4o도 실패하면 종료
            
    except Exception as e:
        print(f"⚠️ 이미지 분석 실패: {e}")
        return False  # 분석 실패 시 텍스트 없다고 가정
    
    return False

def generate_contextual_alt_text(paragraph_text, title, api_key):
    """문맥에 맞는 alt 텍스트 AI 생성"""
    if not api_key:
        return "기사 관련 이미지"
    
    try:
        if HAS_OPENAI:
            client = OpenAI(api_key=api_key)
            
            prompt = f"""
다음 기사의 제목과 문단을 보고, 이 위치에 들어갈 이미지의 alt 텍스트를 생성해주세요.
이미지가 본문 내용과 관련성이 높도록 의미 있는 alt 텍스트를 만들어주세요.

기사 제목: {title}
해당 문단: {paragraph_text[:200]}...

요구사항:
1. 본문 내용과 연관성 있는 alt 텍스트
2. SEO에 도움이 되는 키워드 포함
3. 10-15자 내외의 간결한 텍스트
4. 자연스러운 한국어 표현
5. **35~60대 독자층이 이해하기 쉬운 용어 사용**

alt 텍스트만 출력해주세요:
"""
            
            response = client.chat.completions.create(
                model="gpt-4.1",  # gpt-4o-mini → gpt-4.1로 변경
                messages=[
                    {"role": "system", "content": "당신은 SEO 전문가입니다. 본문 내용과 잘 어울리는 이미지 alt 텍스트를 생성합니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.7
            )
            
            alt_text = response.choices[0].message.content.strip()
            # 따옴표 제거 및 정리
            alt_text = alt_text.strip('"').strip("'").strip()
            return alt_text if alt_text else "기사 관련 이미지"
    except:
        pass
    
    return "기사 관련 이미지"

def extract_h5_summary(content):
    """AI 생성 콘텐츠에서 H5 요약 추출하고 본문에서 제거"""
    lines = content.split('\n')
    h5_summary = ""
    content_without_h5 = []
    
    for line in lines:
        if line.startswith('##### '):
            # H5 내용 추출 (##### 제거하고 저장)
            h5_content = line.replace('##### ', '').strip()
            # <br> 태그를 공백으로 변환 (HTML 태그 제거)
            h5_content = h5_content.replace('<br>', ' ').replace('<br/>', ' ').replace('<br />', ' ')
            # **볼드 마크다운 제거**
            h5_content = h5_content.replace('**', '')
            # 특수문자 제거
            special_chars = [':', '!', '?', '*', '#', '|', '&', '<', '>', '[', ']', '{', '}']
            for char in special_chars:
                h5_content = h5_content.replace(char, '')
            # 연속된 공백 정리
            h5_content = re.sub(r'\s+', ' ', h5_content).strip()
            h5_summary = h5_content
        else:
            # H5가 아닌 내용은 본문에 유지
            content_without_h5.append(line)
    
    # 빈 줄 정리
    while content_without_h5 and not content_without_h5[0].strip():
        content_without_h5.pop(0)
    
    return h5_summary, '\n'.join(content_without_h5)

def generate_section_for_image(image_url, title, existing_content, api_key):
    """남은 이미지를 위한 H2 소제목 + 본문 생성"""
    if not api_key:
        return {
            'heading': "관련 정보",
            'content': "해당 분야의 추가적인 동향과 분석 내용입니다."
        }
    
    try:
        if HAS_OPENAI:
            client = OpenAI(api_key=api_key)
            
            prompt = f"""
기사 제목: {title}
기사 내용 요약: {existing_content[:500]}...

위 기사와 관련된 추가 섹션을 만들어주세요.

요구사항:
1. H2 소제목 1개 (특수기호 없이, 자연스럽게)
2. 본문 2-3문장 (기사와 연관성 있게, **중요 키워드는 굵게** 표시)
3. 35-60대 독자층에게 유익한 내용
4. **핵심 정보는 굵게** 처리하여 시인성 향상

JSON 형식으로 응답:
{{"heading": "소제목", "content": "본문 내용"}}
"""
            
            response = client.chat.completions.create(
                model="gpt-4.1",  # gpt-4o-mini → gpt-4.1로 변경
                messages=[
                    {"role": "system", "content": "당신은 기사 작성 전문가입니다. 주어진 기사와 연관성 있는 추가 섹션을 만드는 전문가입니다. 핵심 정보는 **굵게** 표시하여 35-60대 독자층이 빠르게 이해할 수 있도록 합니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            result = response.choices[0].message.content.strip()
            try:
                import json
                section_data = json.loads(result)
                return section_data
            except:
                # JSON 파싱 실패 시 기본값
                return {
                    'heading': "추가 분석",
                    'content': "관련 업계의 동향과 전망에 대한 **추가 정보**입니다."
                }
                
    except Exception as e:
        print(f"⚠️ 추가 섹션 생성 실패: {e}")
        return {
            'heading': "관련 동향",
            'content': "해당 분야의 **최신 동향과 분석**을 제공합니다."
        }

def insert_images_with_structure(content, cloudflare_images, title="", ai_api_key=None, category="economy"):
    """원본과 완전히 다른 위치에 이미지 배치: 우리만의 새로운 구조"""
    if not cloudflare_images:
        return content
    
    lines = content.split('\n')
    result_lines = []
    h5_count = 0
    h2_count = 0
    paragraph_count = 0
    
    # 이미지를 완전히 새로운 규칙으로 배치하기 위해 이미지들을 다시 섞기
    import random
    shuffled_images = cloudflare_images.copy()
    random.shuffle(shuffled_images)  # 원본 순서와 완전히 다르게
    
    # 우리만의 이미지 배치 전략 (썸네일은 텍스트 없는 이미지 우선 선택)
    thumbnail_image = None
    section_images = shuffled_images.copy()
    
    if shuffled_images:
        if category == "automotive":
            print("🚗 자동차 카테고리: 모든 이미지 사용 (필터링 없음)")
            # 자동차는 필터링 없이 첫 번째 이미지 사용
            thumbnail_image = section_images.pop(0)
            print(f"✅ 첫 번째 이미지를 썸네일로 선택: {thumbnail_image[:50]}...")
        else:
            print("🔍 Economy: AI Vision으로 뉴스 텍스트 없는 썸네일 엄격 선별 중...")
            
            # AI Vision으로 텍스트 없는 이미지 찾기 (Economy 카테고리 - 더 많이 체크)
            text_free_images = []
            text_images = []
            
            # 최대 모든 이미지를 체크 (API 비용보다 품질 우선)
            for img_url in section_images:
                has_text = analyze_image_text_content(img_url, ai_api_key)
                if has_text:
                    text_images.append(img_url)
                    print(f"🚫 뉴스/텍스트 이미지 제외: {img_url[:50]}...")
                else:
                    text_free_images.append(img_url)
                    print(f"✅ 텍스트 없는 이미지 발견: {img_url[:50]}...")
                
                # 텍스트 없는 이미지를 찾으면 바로 사용 (효율성)
                if len(text_free_images) >= 1:
                    break
            
            # 텍스트 없는 이미지 우선 선택
            if text_free_images:
                thumbnail_image = text_free_images[0]
                section_images.remove(thumbnail_image)
                print(f"🎯 Economy 썸네일 확정: 텍스트 없는 이미지 사용 {thumbnail_image[:50]}...")
            else:
                print("⚠️ Economy: 모든 이미지에 텍스트 있음 - 첫 번째 이미지 사용")
                thumbnail_image = section_images.pop(0)
                print(f"📸 Economy 썸네일 대안: {thumbnail_image[:50]}...")
    
    image_positions = {
        'thumbnail': thumbnail_image,
        'section_images': section_images
    }
    
    thumbnail_inserted = False
    section_image_index = 0
    
    for i, line in enumerate(lines):
        result_lines.append(line)
        
        # H5 줄은 Hugo 테마에서 별도 처리하므로 이미지 삽입하지 않음
        if line.startswith('##### '):
            # H5 줄은 그대로 두되 이미지는 삽입하지 않음 (Hugo에서 처리)
            pass
        
        # 문단 카운트 (일반 텍스트) - 이미지 삽입하지 않음
        elif line.strip() and not line.startswith('#') and not line.startswith('!'):
            paragraph_count += 1
            # H2 뒤에만 이미지를 넣으므로 문단에는 이미지 삽입하지 않음
        
        # H2 소제목 처리 (모든 H2 뒤에 이미지 배치)
        elif line.startswith('## '):
            h2_count += 1
            
            # 모든 H2 소제목 뒤에 이미지 배치 (카테고리별 필터링)
            while section_image_index < len(image_positions['section_images']):
                image_url = image_positions['section_images'][section_image_index]
                section_image_index += 1
                
                # 카테고리별 이미지 필터링
                use_image = True
                if category == "economy" and ai_api_key:
                    # Economy는 뉴스 텍스트 있는 이미지 제외
                    has_text = analyze_image_text_content(image_url, ai_api_key)
                    if has_text:
                        print(f"🚫 Economy H2 섹션: 뉴스 텍스트 이미지 제외 {image_url[:50]}...")
                        use_image = False
                        continue  # 다음 이미지 시도
                # Automotive는 모든 이미지 사용 (use_image = True 유지)
                
                if use_image:
                    if ai_api_key:
                        alt_text = generate_contextual_alt_text(line, title, ai_api_key)
                    else:
                        alt_text = line.replace('## ', '').replace('**', '').strip()
                    
                    result_lines.append("")
                    result_lines.append(f"![{alt_text}]({image_url})")
                    result_lines.append("*출처: 온라인 커뮤니티*")
                    result_lines.append("")
                    break  # 이미지 사용했으므로 루프 종료
    
    # 남은 이미지들을 H2 소제목 + 이미지 + 본문 형태로 배치
    remaining_images = image_positions['section_images'][section_image_index:]
    if remaining_images:
        print(f"📝 남은 이미지 {len(remaining_images)}개를 추가 섹션으로 생성 중...")
        
        # 기존 콘텐츠 요약 (AI 섹션 생성용)
        existing_content = '\n'.join(result_lines)
        
        for idx, image_url in enumerate(remaining_images):
            # 카테고리별 이미지 필터링
            use_image = True
            if category == "economy" and ai_api_key:
                # Economy는 뉴스 텍스트 있는 이미지 제외
                has_text = analyze_image_text_content(image_url, ai_api_key)
                if has_text:
                    print(f"🚫 Economy 추가섹션: 뉴스 텍스트 이미지 제외 {image_url[:50]}...")
                    continue  # 이 이미지는 건너뛰기
            # Automotive는 모든 이미지 사용
            
            # AI로 섹션 생성
            section_data = generate_section_for_image(image_url, title, existing_content, ai_api_key)
            
            # H2 소제목 추가
            result_lines.append("")
            result_lines.append(f"## {section_data['heading']}")
            result_lines.append("")
            
            # 이미지 추가
            if ai_api_key:
                alt_text = generate_contextual_alt_text(section_data['content'], title, ai_api_key)
            else:
                alt_text = section_data['heading']
            
            result_lines.append(f"![{alt_text}]({image_url})")
            result_lines.append("*출처: 온라인 커뮤니티*")
            result_lines.append("")
            
            # 본문 추가
            result_lines.append(section_data['content'])
            result_lines.append("")
            
            print(f"✅ 추가 섹션 생성: {section_data['heading']}")
    
    return '\n'.join(result_lines)

def validate_yaml_string(text):
    """YAML에서 안전한 문자열로 변환 (HTML 엔티티 제거, 특수문자 정리)"""
    if not text:
        return ""
    
    import html
    # HTML 엔티티 디코딩 (&quot; → " 등)
    safe_text = html.unescape(str(text))
    
    # 기본 정리 (HTML 구분자만 정리, 내용 따옴표는 보존)
    safe_text = safe_text.replace('\n', ' ').replace('\r', ' ')
    safe_text = safe_text.replace('---', '—').replace('```', '')
    
    # 특수문자 제거 (H5용)
    special_chars = [':', '!', '?', '*', '#', '|', '&', '<', '>', '[', ']', '{', '}']
    for char in special_chars:
        safe_text = safe_text.replace(char, '')
    
    # 연속된 공백 정리
    safe_text = re.sub(r'\s+', ' ', safe_text).strip()
    
    # 길이 제한
    if len(safe_text) > 200:
        safe_text = safe_text[:200] + "..."
    
    return safe_text

def create_markdown_file(article_data, output_dir, article_index=0, general_count=0, total_count=0, cloudflare_account_id=None, cloudflare_api_token=None, ai_api_key=None):
    """마크다운 파일 생성 (AI 재작성 및 이미지 처리 포함)"""
    # 🛡️ 강화된 다단계 중복 체크
    article_hash = get_article_hash(article_data['title'], article_data['url'])
    
    # 1. URL 기반 DB 체크 (최우선 - 가장 빠르고 확실)
    db_path = 'processed_articles.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM processed_articles WHERE url = ?', (article_data['url'],))
    url_exists = cursor.fetchone()[0] > 0
    conn.close()
    
    if url_exists:
        print(f"⏭️ Skipping duplicate article (URL in DB): {article_data['title'][:50]}...")
        return False
    
    # 2. 전체 DB 기반 중복 체크 (해시 포함)
    if is_article_processed(article_data['url'], article_data['title'], article_hash):
        print(f"⏭️ Skipping duplicate article (Hash in DB): {article_data['title'][:50]}...")
        return False
    
    # 3. 파일 기반 중복 체크 (안전장치 - 파일시스템과 DB 불일치 대비)
    if check_existing_articles(output_dir, article_hash, article_data['title'], article_data['url']):
        print(f"⏭️ Skipping duplicate article (Found in Files): {article_data['title'][:50]}...")
        # DB에도 기록하여 다음번엔 더 빠르게 스킵
        mark_article_processed(article_data['url'], article_data['title'], article_hash)
        return False
    
    print(f"🤖 Processing NEW article with AI: {article_data['title'][:50]}...")
    
    # AI로 제목 재작성 (구조 유지, 내용 변경)
    new_title = rewrite_title_with_ai(
        article_data['title'],
        article_data['content'],
        ai_api_key
    )
    
    # AI 제목 재작성 실패 시 기사 생성 건너뛰기
    if not new_title or new_title == article_data['title']:
        print(f"⚠️ AI title rewrite failed, skipping article: {article_data['title'][:50]}...")
        return False
    
    # AI로 기사 재작성
    rewritten_content = rewrite_with_ai(
        article_data['content'], 
        new_title,  # 새로운 제목 사용
        ai_api_key
    )
    
    # AI 기사 재작성 실패 시 기사 생성 건너뛰기
    if not rewritten_content or rewritten_content == article_data['content']:
        print(f"⚠️ AI content rewrite failed, skipping article: {new_title[:50]}...")
        return False
    
    # H5 요약을 YAML용으로 분리
    h5_summary, content_without_h5 = extract_h5_summary(rewritten_content)
    print(f"📝 H5 요약 추출: {h5_summary[:50]}..." if h5_summary else "⚠️ H5 요약 없음")
    
    # AI로 태그 추가 생성
    enhanced_tags = generate_ai_tags(
        new_title,  # 새로운 제목 사용
        article_data['content'],
        article_data['tags'],
        ai_api_key
    )
    
    # Cloudflare에 이미지 업로드 (원본 순서와 완전히 다르게 - 역순으로)
    cloudflare_images = []
    if cloudflare_api_token and cloudflare_account_id and article_data['images']:
        # 원본과 다르게 역순으로 업로드하여 위치 완전 변경
        reversed_images = list(reversed(article_data['images'][:5]))  # 역순 + 최대 5개
        print(f"📸 Uploading {len(reversed_images)} images to Cloudflare (in reverse order)...")
        
        for img_url in reversed_images:
            cf_url = upload_to_cloudflare_images(img_url, cloudflare_api_token, cloudflare_account_id)
            if cf_url:  # 성공한 경우만 추가 (원본 순서와 완전히 다름)
                cloudflare_images.append(cf_url)
            time.sleep(1)  # API 제한 고려
    
    # 카테고리 분배: 처음 20%는 일반사이트맵(automotive), 나머지 80%는 뉴스사이트맵(economy)
    if article_index < general_count:
        category = 'automotive'  # 일반사이트맵으로 배치
        print(f"📋 일반사이트맵 배치 ({article_index + 1}/{general_count})")
    else:
        category = 'economy'  # 뉴스사이트맵으로 배치
        print(f"📰 뉴스사이트맵 배치 ({article_index + 1 - general_count}/{total_count - general_count})")
    
    # 이미지를 원본과 완전히 다른 위치에 배치 (H5 제거된 본문 사용, 카테고리별 필터링)
    final_content = insert_images_with_structure(content_without_h5, cloudflare_images, new_title, ai_api_key, category)
    
    # URL 슬러그 생성 (새 제목 기반)
    title_slug = create_url_slug(new_title)
    
    # 카테고리별 디렉토리 생성
    category_dir = os.path.join(output_dir, category)
    os.makedirs(category_dir, exist_ok=True)
    
    # 파일명 생성: 카테고리/제목-영문.md
    filename = f"{title_slug}.md"
    filepath = os.path.join(category_dir, filename)
    
    # 파일명 중복 방지
    counter = 1
    while os.path.exists(filepath):
        filename = f"{title_slug}-{counter}.md"
        filepath = os.path.join(category_dir, filename)
        counter += 1
    
    # 현재 날짜 (한국 시간대)
    kst = timezone(timedelta(hours=9))
    current_date = datetime.now(kst).strftime("%Y-%m-%dT%H:%M:%S+09:00")
    
    # YAML-safe description 생성
    safe_description = validate_yaml_string(article_data['description'])
    
    # YAML-safe title 생성  
    safe_title = validate_yaml_string(new_title)
    
    # 마크다운 생성 (UTF-8 안전한 author 필드)
    safe_author = "윤신애"  # 하드코딩으로 인코딩 문제 방지
    
    # 날짜 포맷팅 (한국 시간대)
    kst_date = datetime.now(kst)
    formatted_date = kst_date.strftime("%Y년 %m월 %d일 %H:%M")
    
    # 카테고리 한글명
    category_korean = "Economy" if category == "economy" else "Automotive"
    
    # YAML 안전한 제목 처리 (따옴표 이스케이프)
    yaml_safe_title = new_title.replace('"', '\\"') if new_title else safe_title
    yaml_safe_h5 = h5_summary.replace('"', '\\"') if h5_summary else ""
    
    markdown_content = f"""---
title: "{yaml_safe_title}"
description: "{safe_description}"
date: {current_date}
author: "{safe_author}"
categories: ["{category}"]
tags: {json.dumps(enhanced_tags, ensure_ascii=False)}
hash: {article_hash}
source_url: "{article_data['url']}"
url: "/{category}/{title_slug}/"
h5_summary: "{yaml_safe_h5}"
"""
    
    # Cloudflare Images만 사용 (원본 이미지 사용하지 않음)
    if cloudflare_images:
        thumbnail_image = cloudflare_images[0]
        markdown_content += f'images: {json.dumps(cloudflare_images, ensure_ascii=False)}\n'
        markdown_content += f'thumbnail: "{thumbnail_image}"\n'
        markdown_content += f'image: "{thumbnail_image}"\n'  # Open Graph용
        markdown_content += f'featured_image: "{thumbnail_image}"\n'  # 테마별 호환성
        markdown_content += f'image_width: 1200\n'  # Google Discover 최적화
        markdown_content += f'image_height: 630\n'  # Google Discover 최적화
    
    # SEO 최적화 추가 필드
    markdown_content += f'slug: "{title_slug}"\n'
    markdown_content += f'type: "post"\n'
    markdown_content += f'layout: "single"\n'
    markdown_content += f'news_keywords: "{", ".join(enhanced_tags[:5])}"\n'  # Google News 최적화
    markdown_content += f'robots: "index, follow"\n'  # 검색엔진 크롤링 허용
    
    markdown_content += f"""draft: false
---

{final_content}
"""
    
    # 파일 저장
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # 📝 DB에 처리 완료 기록 (파일 생성 성공 후에만)
        mark_article_processed(article_data['url'], article_data['title'], article_hash)
        
        print(f"✅ Created: {category}/{os.path.basename(filepath)}")
        
        # Hugo 사이트 재빌드 (메인페이지에 새 기사 반영)
        rebuild_hugo_site()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create file {filepath}: {e}")
        return False

def main():
    """메인 함수"""
    # 환경변수에서 설정 읽기 (새로운 Cloudflare 설정)
    sitemap_url = get_env_var('SITEMAP_URL', 'https://www.reportera.co.kr/news-sitemap.xml')
    cloudflare_account_id = get_env_var('CLOUDFLARE_ACCOUNT_ID', '5778a7b9867a82c2c6ad6d104d5ebb6d')
    cloudflare_api_token = get_env_var('CLOUDFLARE_API_TOKEN', 'XLz-RMI1mpfrTEqLnKylT6t8tJEO7Drcx0zopcGf')
    ai_api_key = get_env_var('OPENAI_API_KEY')
    
    # 처리된 기사 DB 초기화
    init_processed_db()
    
    if len(sys.argv) > 1:
        sitemap_url = sys.argv[1]
    
    print(f"🚀 Starting AI-powered scraper...")
    print(f"📥 Sitemap: {sitemap_url}")
    print(f"🤖 AI Rewrite: {'✅' if ai_api_key else '❌'}")
    print(f"☁️ Cloudflare Images: {'✅' if cloudflare_api_token else '❌'}")
    
    # 사이트맵 다운로드
    try:
        response = requests.get(sitemap_url)
        response.raise_for_status()
        sitemap_content = response.text
        print(f"✅ Downloaded sitemap: {len(sitemap_content):,} bytes")
    except Exception as e:
        print(f"❌ Error downloading sitemap: {e}")
        sys.exit(1)
    
    # URL 추출 (뉴스 사이트맵)
    news_urls = []
    try:
        root = ET.fromstring(sitemap_content)
        # news sitemap 네임스페이스
        namespaces = {
            '': 'http://www.sitemaps.org/schemas/sitemap/0.9',
            'news': 'http://www.google.com/schemas/sitemap-news/0.9'
        }
        
        for url_elem in root.findall('.//url', namespaces):
            loc_elem = url_elem.find('loc', namespaces)
            if loc_elem is not None:
                url = loc_elem.text
                if url and url.startswith('https://www.reportera.co.kr/'):
                    news_urls.append(url)
                    
    except Exception as e:
        print(f"⚠️ Error parsing XML: {e}")
        # 대안 파싱
        lines = sitemap_content.split('\n')
        for line in lines:
            if '<loc>' in line and '</loc>' in line:
                start = line.find('<loc>') + 5
                end = line.find('</loc>')
                if start > 4 and end > start:
                    url = line[start:end]
                    if url.startswith('https://www.reportera.co.kr/'):
                        news_urls.append(url)
    
    # 원본 수집은 100% 뉴스 사이트맵에서만
    urls = news_urls  # 뉴스 URL만 사용
    import random
    random.shuffle(urls)  # 순서 섞기
    
    # 내 사이트 배치 계획: 20% 일반사이트맵 + 80% 뉴스사이트맵
    total_articles = len(urls)
    general_count = min(200, int(total_articles * 0.2))  # 일반사이트맵 최대 200개
    news_count = total_articles - general_count  # 나머지는 뉴스사이트맵
    
    print(f"📊 원본 수집 및 배치 계획:")
    print(f"   🗞️ 뉴스 사이트맵에서 수집: {len(news_urls)}개")
    print(f"   🎯 총 처리 대상: {len(urls)}개")
    print(f"   📋 일반사이트맵 배치: {general_count}개 (20%)")
    print(f"   📰 뉴스사이트맵 배치: {news_count}개 (80%)")
    
    # 🔥 분배된 기사 처리
    print(f"🔍 스마트 사이트맵 분배 완료 - {len(urls)}개 URL 처리 시작")
    
    # 출력 디렉토리
    output_dir = 'content'
    os.makedirs(output_dir, exist_ok=True)
    
    # 📊 처리 전 중복 체크 통계
    duplicate_count = 0
    db_path = 'processed_articles.db'
    
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for url in urls:
            cursor.execute('SELECT COUNT(*) FROM processed_articles WHERE url = ?', (url,))
            if cursor.fetchone()[0] > 0:
                duplicate_count += 1
        
        conn.close()
    
    print(f"📈 Processing Statistics:")
    print(f"   🔗 Total URLs: {len(urls)}")
    print(f"   🔄 Already processed: {duplicate_count}")
    print(f"   🆕 New to process: {len(urls) - duplicate_count}")
    
    # 처리 통계
    processed = 0
    skipped = 0
    failed = 0
    
    for i, url in enumerate(urls):
        print(f"\n📄 [{i+1}/{len(urls)}] Processing: {url.split('/')[-2:]}")
        
        # 🛡️ URL 기반 사전 중복 체크 (빠른 스킵)
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM processed_articles WHERE url = ?', (url,))
            is_processed = cursor.fetchone()[0] > 0
            conn.close()
            
            if is_processed:
                print(f"⏭️ Skipping already processed URL: {url}")
                skipped += 1
                continue
        
        article_data = extract_content_from_url(url)
        
        if article_data:
            if create_markdown_file(
                article_data, 
                output_dir,
                i,  # article_index
                general_count,  # general_count
                len(urls),  # total_count
                cloudflare_account_id,
                cloudflare_api_token,
                ai_api_key
            ):
                processed += 1
                print(f"🎯 Progress: {processed} processed, {skipped} skipped, {failed} failed")
            else:
                skipped += 1
        else:
            failed += 1
            print(f"❌ Failed to extract content from: {url}")
        
        # API 제한 고려 대기 (처리량에 따라 조정)
        if processed > 0 and processed % 10 == 0:
            print(f"⏸️ Processed {processed} articles, taking a short break...")
            time.sleep(5)  # 10개마다 5초 대기
        else:
            time.sleep(random.uniform(1, 2))
    
    print(f"\n📊 Final Processing Summary:")
    print(f"✅ Successfully Processed: {processed}")
    print(f"⏭️ Skipped (Duplicates): {skipped}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Total URLs Checked: {len(urls)}")
    
    if processed > 0:
        print(f"🎉 Successfully created {processed} new AI-rewritten articles!")
        print(f"💾 Database updated with {processed + skipped} processed URLs")
    else:
        print("ℹ️ No new articles were created - all URLs already processed or failed")
    
    # 📊 DB 상태 확인
    try:
        db_path = 'processed_articles.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM processed_articles')
        total_processed = cursor.fetchone()[0]
        conn.close()
        print(f"🗄️ Total articles in database: {total_processed}")
    except Exception as e:
        print(f"⚠️ Could not check database: {e}")
    
    # 📧 이메일 보고서 발송
    print(f"\n📧 Sending email report...")
    try:
        # send_email.py의 함수 import 및 실행
        import importlib.util
        
        # send_email.py 모듈 동적 로드
        spec = importlib.util.spec_from_file_location("send_email", "send_email.py")
        if spec and spec.loader:
            send_email_module = importlib.util.module_from_spec(spec)
            sys.modules["send_email"] = send_email_module
            spec.loader.exec_module(send_email_module)
            
            # 이메일 보고서 발송
            email_success = send_email_module.send_report_email()
            if email_success:
                print("✅ Email report sent successfully!")
            else:
                print("⚠️ Email report failed to send")
        else:
            print("⚠️ Could not load send_email.py module")
            
    except Exception as e:
        print(f"⚠️ Email sending error: {e}")
        print("📧 Skipping email report...")

if __name__ == "__main__":
    main() 