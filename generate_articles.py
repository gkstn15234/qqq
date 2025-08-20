import os
import re
import random
from datetime import datetime, timedelta

def get_existing_articles():
    """기존 기사 파일들을 가져옵니다."""
    automotive_dir = "content/automotive"
    articles = []
    
    for filename in os.listdir(automotive_dir):
        if filename.endswith('.md'):
            filepath = os.path.join(automotive_dir, filename)
            articles.append(filepath)
    
    return articles

def read_article_content(filepath):
    """기사 파일의 내용을 읽습니다."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def update_article_metadata(content, new_date, new_time, article_number):
    """기사의 메타데이터를 새로운 날짜와 시간으로 업데이트합니다."""
    date_str = new_date.strftime('%Y-%m-%d')
    datetime_str = f"{date_str}T{new_time}:00+09:00"
    new_slug_date = new_date.strftime('%Y%m%d')
    
    # 기존 파일명에서 날짜 부분 추출
    original_slug_match = re.search(r'slug: "([^"]+)"', content)
    if original_slug_match:
        original_slug = original_slug_match.group(1)
        # 날짜 부분을 새로운 날짜로 교체
        base_name = re.sub(r'-\d{8}-\d{2}$', '', original_slug)
        new_slug = f"{base_name}-{new_slug_date}-{article_number:02d}"
    else:
        new_slug = f"article-{new_slug_date}-{article_number:02d}"
    
    # URL 업데이트
    new_url = f"/automotive/{new_slug}/"
    
    # 날짜 업데이트
    content = re.sub(r'date: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00', 
                     f'date: {datetime_str}', content)
    
    # slug 업데이트
    content = re.sub(r'slug: "[^"]+"', f'slug: "{new_slug}"', content)
    
    # URL 업데이트
    content = re.sub(r'url: "[^"]+"', f'url: "{new_url}"', content)
    
    return content, new_slug

def generate_articles_for_date(existing_articles, target_date, articles_per_day=10):
    """특정 날짜에 대해 기사들을 생성합니다."""
    generated_files = []
    
    # 시간 설정 (08:30부터 17:30까지 1시간 간격)
    start_hour = 8
    start_minute = 30
    
    for i in range(articles_per_day):
        # 기존 기사 중 랜덤 선택
        source_article = random.choice(existing_articles)
        
        # 시간 계산
        hour = start_hour + i
        time_str = f"{hour:02d}:{start_minute:02d}"
        
        # 기사 내용 읽기
        content = read_article_content(source_article)
        
        # 메타데이터 업데이트
        updated_content, new_slug = update_article_metadata(
            content, target_date, time_str, i + 1
        )
        
        # 새 파일명 생성
        new_filename = f"{new_slug}.md"
        new_filepath = os.path.join("content/automotive", new_filename)
        
        # 새 파일 작성
        with open(new_filepath, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        generated_files.append(new_filepath)
        print(f"생성됨: {new_filename}")
    
    return generated_files

def main():
    """메인 함수"""
    print("기사 대량 생성 시작...")
    
    # 기존 기사들 가져오기
    existing_articles = get_existing_articles()
    print(f"기존 기사 {len(existing_articles)}개 발견")
    
    # 생성할 날짜들 (8월 17일부터 21일까지)
    start_date = datetime(2025, 8, 17)
    all_generated_files = []
    
    for day_offset in range(5):  # 5일간
        target_date = start_date + timedelta(days=day_offset)
        print(f"\n{target_date.strftime('%Y년 %m월 %d일')} 기사 생성 중...")
        
        generated_files = generate_articles_for_date(existing_articles, target_date)
        all_generated_files.extend(generated_files)
    
    print(f"\n✅ 총 {len(all_generated_files)}개 기사 생성 완료!")
    print("생성된 파일들:")
    for filepath in all_generated_files:
        print(f"  - {filepath}")

if __name__ == "__main__":
    main()