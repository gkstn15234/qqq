import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import re
import os
from datetime import datetime
import time
import random
import sys
import hashlib
import json
import base64
from urllib.parse import urlparse, urljoin

# AI 관련 import
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

def get_env_var(name, default=None):
    """환경변수 가져오기"""
    return os.environ.get(name, default)

def clean_filename(title):
    """제목을 파일명으로 사용할 수 있도록 정리"""
    filename = re.sub(r'[^\w\s-]', '', title)
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename.strip('-').lower()

def get_article_hash(title, url):
    """기사의 고유 해시 생성 (중복 방지용)"""
    content = f"{title}{url}"
    return hashlib.md5(content.encode()).hexdigest()[:8]

def check_existing_articles(output_dir, article_hash):
    """기존 기사 중복 체크"""
    if not os.path.exists(output_dir):
        return False
    
    for filename in os.listdir(output_dir):
        if filename.endswith('.md'):
            filepath = os.path.join(output_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if f"hash: {article_hash}" in content:
                        return True
            except Exception:
                continue
    return False

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
            # Cloudflare Images URL 반환
            image_id = result['result']['id']
            return f"https://imagedelivery.net/{account_id}/{image_id}/public"
        else:
            print(f"❌ Cloudflare upload failed: {result}")
            return image_url
            
    except Exception as e:
        print(f"⚠️ Failed to upload image to Cloudflare: {e}")
        return image_url

def rewrite_with_ai(original_content, title, api_key, api_type="openai"):
    """AI를 사용하여 기사 재작성"""
    if not api_key:
        print("⚠️ No AI API key provided, skipping rewrite")
        return original_content
    
    try:
        if api_type == "openai" and HAS_OPENAI:
            client = OpenAI(api_key=api_key)
            
            prompt = f"""
다음 기사를 완전히 새로운 관점에서 재작성해주세요. 
원본의 핵심 정보는 유지하되, 문체와 구성을 완전히 바꿔주세요.
SEO에 최적화된 자연스러운 한국어로 작성해주세요.

제목: {title}

원본 기사:
{original_content}

재작성 요구사항:
1. 문단 구성을 완전히 새롭게 배치
2. 표현 방식을 다르게 변경
3. 핵심 사실은 정확히 유지
4. 자연스럽고 읽기 쉬운 문체
5. 마크다운 형식으로 출력
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
            return rewritten
            
    except Exception as e:
        print(f"❌ AI rewrite failed: {e}")
        return original_content
    
    return original_content

def generate_ai_tags(title, content, existing_tags, api_key, api_type="openai"):
    """AI를 사용하여 추가 태그 생성"""
    if not api_key:
        return existing_tags
    
    try:
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
                    return existing_tags + new_tags[:2]
            except:
                pass
                
    except Exception as e:
        print(f"❌ AI tag generation failed: {e}")
    
    return existing_tags

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
        
        # 메타 정보 추출
        meta_elem = soup.find('div', class_='entry-meta')
        author = "김한수"  # 기본값
        if meta_elem:
            author_elem = meta_elem.find('span', class_='author-name')
            if author_elem:
                author = author_elem.get_text().strip()
        
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
                            paragraphs.append(f"\n## {text}\n")
                        else:
                            paragraphs.append(text)
        
        content = '\n\n'.join(paragraphs)
        
        # 요약문 생성
        description = paragraphs[0][:150] + "..." if paragraphs else ""
        
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

def shuffle_images_in_content(content, cloudflare_images):
    """콘텐츠 내에 이미지를 랜덤하게 재배치"""
    if not cloudflare_images:
        return content
    
    paragraphs = content.split('\n\n')
    
    # 이미지를 랜덤하게 섞기
    shuffled_images = cloudflare_images.copy()
    random.shuffle(shuffled_images)
    
    # 문단 사이에 이미지 삽입
    result_paragraphs = []
    image_index = 0
    
    for i, paragraph in enumerate(paragraphs):
        result_paragraphs.append(paragraph)
        
        # 2-3개 문단마다 이미지 삽입 (랜덤)
        if i > 0 and i % random.randint(2, 3) == 0 and image_index < len(shuffled_images):
            image_url = shuffled_images[image_index]
            result_paragraphs.append(f"\n![기사 이미지]({image_url})\n")
            image_index += 1
    
    # 남은 이미지들을 마지막에 추가
    while image_index < len(shuffled_images):
        image_url = shuffled_images[image_index]
        result_paragraphs.append(f"\n![기사 이미지]({image_url})\n")
        image_index += 1
    
    return '\n\n'.join(result_paragraphs)

def create_markdown_file(article_data, output_dir, cloudflare_account_id=None, cloudflare_api_token=None, ai_api_key=None):
    """마크다운 파일 생성 (AI 재작성 및 이미지 처리 포함)"""
    # 중복 체크
    article_hash = get_article_hash(article_data['title'], article_data['url'])
    
    if check_existing_articles(output_dir, article_hash):
        print(f"⏭️ Skipping duplicate article: {article_data['title']}")
        return False
    
    print(f"🤖 Processing with AI: {article_data['title'][:50]}...")
    
    # AI로 기사 재작성
    rewritten_content = rewrite_with_ai(
        article_data['content'], 
        article_data['title'], 
        ai_api_key
    )
    
    # AI로 태그 추가 생성
    enhanced_tags = generate_ai_tags(
        article_data['title'],
        article_data['content'],
        article_data['tags'],
        ai_api_key
    )
    
    # Cloudflare에 이미지 업로드
    cloudflare_images = []
    if cloudflare_api_token and cloudflare_account_id and article_data['images']:
        print(f"📸 Uploading {len(article_data['images'])} images to Cloudflare...")
        for img_url in article_data['images'][:5]:  # 최대 5개만
            cf_url = upload_to_cloudflare_images(img_url, cloudflare_api_token, cloudflare_account_id)
            cloudflare_images.append(cf_url)
            time.sleep(1)  # API 제한 고려
    
    # 이미지를 콘텐츠에 랜덤 재배치
    final_content = shuffle_images_in_content(rewritten_content, cloudflare_images)
    
    # 파일명 생성
    filename = clean_filename(article_data['title'])
    filepath = os.path.join(output_dir, f"{filename}.md")
    
    # 파일명 중복 방지
    counter = 1
    while os.path.exists(filepath):
        base_filename = clean_filename(article_data['title'])
        filepath = os.path.join(output_dir, f"{base_filename}-{counter}.md")
        counter += 1
    
    # 현재 날짜
    current_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00")
    
    # 마크다운 생성
    markdown_content = f"""---
title: "{article_data['title']}"
description: "{article_data['description']}"
date: {current_date}
author: "{article_data['author']}"
categories: ["자동차"]
tags: {json.dumps(enhanced_tags, ensure_ascii=False)}
hash: {article_hash}
source_url: "{article_data['url']}"
"""
    
    # 첫 번째 이미지를 썸네일로
    if cloudflare_images:
        markdown_content += f'images: ["{cloudflare_images[0]}"]\n'
    elif article_data['images']:
        markdown_content += f'images: ["{article_data["images"][0]}"]\n'
    
    markdown_content += f"""draft: false
---

{final_content}

---
*이 기사는 AI 기술을 활용하여 재작성되었습니다.*
"""
    
    # 파일 저장
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"✅ Created: {os.path.basename(filepath)}")
    return True

def main():
    """메인 함수"""
    # 환경변수에서 설정 읽기
    sitemap_url = get_env_var('SITEMAP_URL', 'https://www.reportera.co.kr/news-sitemap.xml')
    cloudflare_account_id = get_env_var('CLOUDFLARE_ACCOUNT_ID')
    cloudflare_api_token = get_env_var('CLOUDFLARE_API_TOKEN')
    ai_api_key = get_env_var('OPENAI_API_KEY')
    
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
    
    # 최신 20개 기사만 처리 (뉴스 사이트맵이므로)
    urls = urls[:20]
    
    # 출력 디렉토리
    output_dir = 'content/car'
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"🔍 Found {len(urls)} URLs to process")
    
    # 처리 통계
    processed = 0
    skipped = 0
    failed = 0
    
    for i, url in enumerate(urls):
        print(f"\n📄 [{i+1}/{len(urls)}] Processing: {url.split('/')[-1][:50]}...")
        
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
            else:
                skipped += 1
        else:
            failed += 1
        
        # API 제한 고려 대기
        time.sleep(random.uniform(1, 2))
    
    print(f"\n📊 Processing Summary:")
    print(f"✅ Processed: {processed}")
    print(f"⏭️ Skipped: {skipped}")
    print(f"❌ Failed: {failed}")
    
    if processed > 0:
        print(f"🎉 Successfully created {processed} AI-rewritten articles!")
    else:
        print("ℹ️ No new articles were created.")

if __name__ == "__main__":
    main() 