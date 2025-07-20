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
    """AI 실패 시 수동으로 기사 재작성"""
    try:
        # 원본 콘텐츠를 문단별로 분리
        paragraphs = original_content.split('\n\n')
        rewritten_paragraphs = []
        
        # 각 문단을 재구성
        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue
                
            sentences = paragraph.split('.')
            if len(sentences) > 1:
                # 문장 순서 재배치 및 접속사 추가
                rewritten_sentences = []
                for j, sentence in enumerate(sentences):
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    
                    # 문장 시작을 다양하게 변경
                    if j == 0 and i > 0:
                        connectors = ["한편", "또한", "이와 관련해", "특히", "더불어", "아울러"]
                        if not any(sentence.startswith(conn) for conn in connectors):
                            sentence = f"{connectors[i % len(connectors)]} {sentence}"
                    
                    rewritten_sentences.append(sentence)
                
                if rewritten_sentences:
                    rewritten_paragraphs.append('. '.join(rewritten_sentences) + '.')
            else:
                rewritten_paragraphs.append(paragraph)
        
        # 35~60대 독자층을 위한 기본 구조로 재구성 (H1 제목 + H5 요약 + 썸네일 + 본문 + H2 소제목)
        rewritten_content = f"""
# {title}

##### | {title} 관련 주요 이슈를 간단히 요약한 내용

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
        # 최소한의 기본 구조라도 생성 (H1 제목 + H5 요약 + H2 소제목)
        return f"""
# {title}

##### | 업계 주요 동향에 대한 핵심 내용을 다룬 기사

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
다음 기사를 완전히 새로운 스타일로 재해석하여 창작해주세요.
원본의 핵심 사실과 데이터만 유지하고, 나머지는 모두 새롭게 작성해주세요.

제목: {title}

원본 기사:
{original_content}

창작 요구사항:
1. 제목을 더 매력적이고 흥미롭게 재작성
2. 도입부를 완전히 새로운 각도에서 시작
3. 문단 구조와 흐름을 독창적으로 재구성  
4. 표현 방식과 문체를 완전히 변경
5. 핵심 사실과 수치는 정확히 유지
6. SEO 친화적이고 독자의 관심을 끄는 문체
7. 마크다운 형식으로 출력 (H1 태그 사용 금지, H2는 H5로 변경)
8. 감정적 몰입과 스토리텔링 요소 추가
9. **35~60대 주 독자층을 위한 가독성 최적화**: 
   - 문장을 적절한 길이로 구성 (15~25단어)
   - 문단을 2~4문장으로 간결하게 구성
   - 복잡한 용어는 쉬운 표현으로 설명 추가
   - 핵심 포인트를 볼드(**텍스트**)로 강조
10. **헤딩 구조 규칙**: 
    - H1(#) 제목 사용 (기사 제목)
    - H5(#####) 요약 (전체 기사 한 줄 요약)
    - H2(##) 소제목 사용 (본문 소제목)
    - 구조: H1 제목 > H5 요약 > 썸네일 이미지 > 본문 > H2 소제목

마치 다른 기자가 같은 사건을 취재해서 완전히 다른 시각으로 쓴 것처럼 작성해주세요.
"""
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "당신은 전문 기자입니다. 기사를 자연스럽고 매력적으로 재작성하는 전문가입니다."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.7
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
다음 기사의 제목과 내용을 분석하여 적절한 태그 2개를 추가로 생성해주세요.
기존 태그와 중복되지 않게 하고, 한국어로 작성해주세요.

제목: {title}
내용: {content[:500]}...
기존 태그: {', '.join(existing_tags)}

새로운 태그 2개만 JSON 배열 형태로 응답해주세요.
예: ["태그1", "태그2"]
"""
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "당신은 SEO 전문가입니다. 기사에 맞는 최적의 태그를 생성합니다."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=100,
                    temperature=0.5
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
본문 내용을 참고하여 제목을 새롭게 재작성해주세요.

원본 제목: {original_title}

본문 내용 (요약):
{content[:1000]}...

재작성 요구사항:
1. 원본 제목의 구조와 길이를 최대한 유지
2. 본문의 핵심 내용을 반영한 새로운 제목
3. 더 흥미롭고 클릭하고 싶게 만들기
4. SEO에 최적화된 키워드 포함
5. 한국어 뉴스 제목 스타일 유지
6. 따옴표나 특수문자 활용 가능
7. **35~60대 독자층에게 매력적인 제목**: 
   - 명확하고 직관적인 표현 사용
   - 궁금증을 유발하는 요소 포함
   - 숫자나 구체적 정보 활용

새로운 제목만 출력해주세요:
"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 뉴스 제목 작성 전문가입니다. 흥미롭고 클릭률이 높은 제목을 만드는 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.8
            )
            
            new_title = response.choices[0].message.content.strip()
            # 앞뒤 시스템 따옴표만 제거 (내용의 따옴표는 보존)
            new_title = new_title.strip('"').strip("'")
            # YAML 구분자만 정리 (따옴표는 보존)
            new_title = new_title.replace('---', '—').replace('```', '')
            print(f"✅ AI title rewrite successful on attempt {attempt + 1}")
            print(f"📝 Title rewritten: {original_title[:30]}... → {new_title[:30]}...")
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
        
        # 이미지 URL 수집
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
        
        # 텍스트 내용 추출 (이미지 제외)
        paragraphs = []
        for elem in content_elem.children:
            if hasattr(elem, 'name') and elem.name:
                if elem.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5']:
                    # <br> 태그를 줄바꿈으로 변환
                    for br in elem.find_all('br'):
                        br.replace_with('\n')
                    
                    text = elem.get_text().strip()
                    if text and not text.startswith('(adsbygoogle'):
                        if elem.name in ['h2', 'h3', 'h4', 'h5']:
                            paragraphs.append(f"\n## {text}\n")  # H2로 유지
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
                model="gpt-4o-mini",
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

def insert_images_with_structure(content, cloudflare_images, title="", ai_api_key=None):
    """새로운 구조에 맞게 이미지 배치: H1 > H5 > 썸네일 > 본문 > H2 + 이미지"""
    if not cloudflare_images:
        return content
    
    lines = content.split('\n')
    result_lines = []
    thumbnail_inserted = False
    remaining_images = cloudflare_images.copy()
    
    # 썸네일 이미지 (첫 번째 이미지)
    thumbnail_image = remaining_images.pop(0) if remaining_images else None
    
    for i, line in enumerate(lines):
        result_lines.append(line)
        
        # H5 요약 뒤에 썸네일 이미지 삽입 (구글 디스커버 사이즈)
        if line.startswith('##### ') and not thumbnail_inserted and thumbnail_image:
            if ai_api_key:
                alt_text = generate_contextual_alt_text(line, title, ai_api_key)
            else:
                alt_text = f"{title} 관련 이미지"
            
            result_lines.append("")  # 빈 줄
            result_lines.append(f"![{alt_text}]({thumbnail_image})")
            result_lines.append("")  # 빈 줄
            thumbnail_inserted = True
        
        # H2 소제목 뒤에 이미지 삽입
        elif line.startswith('## ') and remaining_images:
            # 다음 몇 줄을 확인해서 본문이 있는지 체크
            next_content = ""
            for j in range(i+1, min(i+4, len(lines))):
                if j < len(lines) and lines[j].strip():
                    next_content += lines[j] + " "
            
            if next_content.strip():  # 본문이 있으면 이미지 추가
                image_url = remaining_images.pop(0)
                
                if ai_api_key:
                    alt_text = generate_contextual_alt_text(next_content[:200], title, ai_api_key)
                else:
                    alt_text = line.replace('## ', '').replace('**', '').strip()
                
                # H2 소제목 직후에 이미지 추가
                result_lines.append("")  # 빈 줄
                result_lines.append(f"![{alt_text}]({image_url})")
                result_lines.append("")  # 빈 줄
    
    # 남은 이미지가 있다면 마지막에 추가
    for image_url in remaining_images:
        if ai_api_key:
            alt_text = generate_contextual_alt_text("기사 관련", title, ai_api_key)
        else:
            alt_text = "관련 이미지"
        
        result_lines.append("")
        result_lines.append(f"![{alt_text}]({image_url})")
    
    return '\n'.join(result_lines)

def validate_yaml_string(text):
    """YAML에서 안전한 문자열로 변환 (따옴표 보존)"""
    if not text:
        return ""
    
    # 기본 정리 (따옴표는 HTML 엔티티로 변환하여 보존)
    safe_text = str(text).replace('"', '&quot;').replace('\n', ' ').replace('\r', ' ')
    safe_text = safe_text.replace('---', '—').replace('```', '')
    
    # 연속된 공백 정리
    safe_text = re.sub(r'\s+', ' ', safe_text).strip()
    
    # 길이 제한
    if len(safe_text) > 200:
        safe_text = safe_text[:200] + "..."
    
    return safe_text

def create_markdown_file(article_data, output_dir, cloudflare_account_id=None, cloudflare_api_token=None, ai_api_key=None):
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
    
    # AI로 태그 추가 생성
    enhanced_tags = generate_ai_tags(
        new_title,  # 새로운 제목 사용
        article_data['content'],
        article_data['tags'],
        ai_api_key
    )
    
    # Cloudflare에 이미지 업로드 (원본 이미지 사용하지 않음)
    cloudflare_images = []
    if cloudflare_api_token and cloudflare_account_id and article_data['images']:
        print(f"📸 Uploading {len(article_data['images'])} images to Cloudflare...")
        for img_url in article_data['images'][:5]:  # 최대 5개만
            cf_url = upload_to_cloudflare_images(img_url, cloudflare_api_token, cloudflare_account_id)
            if cf_url:  # 성공한 경우만 추가 (원본 이미지 사용하지 않음)
                cloudflare_images.append(cf_url)
            time.sleep(1)  # API 제한 고려
    
    # 이미지를 새로운 구조에 맞게 배치 (H1 > H5 > 썸네일 > 본문 > H2 + 이미지)
    final_content = insert_images_with_structure(rewritten_content, cloudflare_images, new_title, ai_api_key)
    
    # 카테고리 자동 분류 (새 제목 기반)
    category = categorize_article(new_title, article_data['content'], enhanced_tags)
    
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
    markdown_content = f"""---
title: "{safe_title}"
description: "{safe_description}"
date: {current_date}
author: "{safe_author}"
categories: ["{category}"]
tags: {json.dumps(enhanced_tags, ensure_ascii=False)}
hash: {article_hash}
source_url: "{article_data['url']}"
url: "/{category}/{title_slug}/"
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
    
    # URL 추출
    urls = []
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
                    urls.append(url)
                    
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
                        urls.append(url)
    
    # 🔥 모든 기사 처리 (제한 제거)
    print(f"🔍 Found {len(urls)} URLs in sitemap - processing ALL articles")
    
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