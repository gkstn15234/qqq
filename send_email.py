import os
import smtplib
import feedparser
import requests
from email.message import EmailMessage
from datetime import datetime
import json
import pytz
import sqlite3

# GitHub Secrets를 통해 전달된 환경 변수에서 정보 가져오기
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# OpenAI 모델 선택 (기본값: gpt-4o-mini)
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

# 사용 가능한 모델들과 설정
MODEL_CONFIGS = {
    'gpt-3.5-turbo': {
        'max_tokens': 300,
        'temperature': 0.7,
        'description': '빠르고 효율적인 모델'
    },
    'gpt-4': {
        'max_tokens': 400,
        'temperature': 0.6,
        'description': '더 정확하고 상세한 분석'
    },
    'gpt-4-turbo': {
        'max_tokens': 500,
        'temperature': 0.7,
        'description': '최신 GPT-4 터보 모델'
    },
    'gpt-4o': {
        'max_tokens': 500,
        'temperature': 0.7,
        'description': '최신 GPT-4o 모델'
    },
    'gpt-4o-mini': {
        'max_tokens': 300,
        'temperature': 0.7,
        'description': '경제적인 GPT-4o 미니 모델'
    }
}

def get_scraping_statistics():
    """AI 스크래퍼 실행 결과 통계 가져오기"""
    try:
        db_path = 'processed_articles.db'
        if not os.path.exists(db_path):
            return {
                'total_processed': 0,
                'today_processed': 0,
                'last_run': 'N/A'
            }
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 전체 처리된 기사 수
        cursor.execute('SELECT COUNT(*) FROM processed_articles')
        total_processed = cursor.fetchone()[0]
        
        # 오늘 처리된 기사 수
        today = datetime.now(KST).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(*) FROM processed_articles 
            WHERE DATE(processed_date) = ?
        """, (today,))
        today_processed = cursor.fetchone()[0]
        
        # 마지막 실행 시간
        cursor.execute("""
            SELECT MAX(processed_date) FROM processed_articles
        """)
        last_run_result = cursor.fetchone()[0]
        last_run = last_run_result if last_run_result else 'N/A'
        
        conn.close()
        
        return {
            'total_processed': total_processed,
            'today_processed': today_processed,
            'last_run': last_run
        }
        
    except Exception as e:
        print(f"통계 가져오기 실패: {e}")
        return {
            'total_processed': 0,
            'today_processed': 0,
            'last_run': 'Error'
        }

def count_articles_basic():
    """frontmatter 없이 기본 파일 카운팅"""
    try:
        content_dir = 'content'
        if not os.path.exists(content_dir):
            return {'automotive': 0, 'economy': 0, 'total': 0, 'articles': []}
        
        automotive_count = 0
        economy_count = 0
        articles = []
        
        # automotive 카테고리
        automotive_dir = os.path.join(content_dir, 'automotive')
        if os.path.exists(automotive_dir):
            for filename in os.listdir(automotive_dir):
                if filename.endswith('.md') and filename != '_index.md':
                    automotive_count += 1
                    articles.append({
                        'title': filename.replace('.md', '').replace('-', ' ').title(),
                        'url': f"https://okonomis.com/automotive/{filename.replace('.md', '')}/",
                        'category': '자동차'
                    })
        
        # economy 카테고리  
        economy_dir = os.path.join(content_dir, 'economy')
        if os.path.exists(economy_dir):
            for filename in os.listdir(economy_dir):
                if filename.endswith('.md') and filename != '_index.md':
                    economy_count += 1
                    articles.append({
                        'title': filename.replace('.md', '').replace('-', ' ').title(),
                        'url': f"https://okonomis.com/economy/{filename.replace('.md', '')}/",
                        'category': '경제'
                    })
        
        total_count = automotive_count + economy_count
        return {
            'automotive': automotive_count,
            'economy': economy_count, 
            'total': total_count,
            'articles': articles
        }
    except Exception as e:
        print(f"Error counting articles: {e}")
        return {'automotive': 0, 'economy': 0, 'total': 0, 'articles': []}

def count_published_articles():
    """발행된 기사 수 계산 및 목록 반환"""
    try:
    try:
        import frontmatter
        except ImportError:
            print("Warning: frontmatter module not found. Using basic file counting.")
            return count_articles_basic()
            
        content_dir = 'content'
        if not os.path.exists(content_dir):
            return {'automotive': 0, 'economy': 0, 'total': 0, 'articles': []}
        
        automotive_count = 0
        economy_count = 0
        articles = []
        
        # automotive 카테고리
        automotive_dir = os.path.join(content_dir, 'automotive')
        if os.path.exists(automotive_dir):
            for filename in os.listdir(automotive_dir):
                if filename.endswith('.md') and filename != '_index.md':
                    automotive_count += 1
                    try:
                        with open(os.path.join(automotive_dir, filename), 'r', encoding='utf-8') as f:
                            post = frontmatter.load(f)
                            articles.append({
                                'title': post.metadata.get('title', filename),
                                'url': f"https://okonomis.com/automotive/{filename.replace('.md', '')}/",
                                'category': '자동차'
                            })
                    except:
                        pass
        
        # economy 카테고리
        economy_dir = os.path.join(content_dir, 'economy')
        if os.path.exists(economy_dir):
            for filename in os.listdir(economy_dir):
                if filename.endswith('.md') and filename != '_index.md':
                    economy_count += 1
                    try:
                        with open(os.path.join(economy_dir, filename), 'r', encoding='utf-8') as f:
                            post = frontmatter.load(f)
                            articles.append({
                                'title': post.metadata.get('title', filename),
                                'url': f"https://okonomis.com/economy/{filename.replace('.md', '')}/",
                                'category': '경제'
                            })
                    except:
                        pass
        
        return {
            'automotive': automotive_count,
            'economy': economy_count,
            'total': automotive_count + economy_count,
            'articles': articles
        }
        
    except Exception as e:
        print(f"기사 수 계산 실패: {e}")
        return {'automotive': 0, 'economy': 0, 'total': 0, 'articles': []}

def get_google_news():
    """Google 뉴스 RSS에서 최신 뉴스 가져오기"""
    try:
        # Google 뉴스 RSS URL (한국 뉴스)
        rss_url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
        feed = feedparser.parse(rss_url)
        
        news_items = []
        # 상위 5개 뉴스만 가져오기 (이메일에서는 간단히)
        for entry in feed.entries[:5]:
            news_items.append({
                'title': entry.title,
                'link': entry.link,
                'published': entry.published,
                'summary': entry.summary if hasattr(entry, 'summary') else ''
            })
        
        return news_items
    except Exception as e:
        print(f"뉴스 가져오기 실패: {e}")
        return []

def summarize_news_with_openai(news_items):
    """OpenAI API를 사용해서 뉴스 요약하기"""
    try:
        if not news_items:
            return "뉴스를 가져올 수 없습니다."
        
        # 뉴스 제목들을 하나의 텍스트로 합치기
        news_text = "\n".join([f"- {item['title']}" for item in news_items])
        
        # 선택된 모델의 설정 가져오기
        model_config = MODEL_CONFIGS.get(OPENAI_MODEL, MODEL_CONFIGS['gpt-4o-mini'])
        
        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': OPENAI_MODEL,
            'messages': [
                {
                    'role': 'system',
                    'content': '당신은 뉴스 요약 전문가입니다. 주요 뉴스들을 간결하고 이해하기 쉽게 요약해주세요.'
                },
                {
                    'role': 'user',
                    'content': f'다음 뉴스 제목들을 바탕으로 오늘의 주요 뉴스를 2-3줄로 간단히 요약해주세요:\n\n{news_text}'
                }
            ],
            'max_tokens': model_config['max_tokens'],
            'temperature': model_config['temperature']
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            print(f"OpenAI API 오류: {response.status_code}")
            return "뉴스 요약을 가져올 수 없습니다."
            
    except Exception as e:
        print(f"OpenAI API 호출 실패: {e}")
        return "뉴스 요약을 가져올 수 없습니다."

def create_report_email_content():
    """기사 자동화 보고서 이메일 내용 생성"""
    # 한국 시간으로 현재 시간 가져오기
    current_time = datetime.now(KST).strftime("%Y년 %m월 %d일 %H시 %M분 (KST)")
    
    # AI 스크래퍼 통계 가져오기
    scraping_stats = get_scraping_statistics()
    
    # 발행된 기사 수 계산
    article_counts = count_published_articles()
    
    # 간단한 뉴스 요약 (선택사항)
    news_summary = ""
    if OPENAI_API_KEY:
        news_items = get_google_news()
        if news_items:
            news_summary = summarize_news_with_openai(news_items)
    
    # 성공/실패 상태 판단
    status_emoji = "✅" if scraping_stats['today_processed'] > 0 else "⚠️"
    status_text = "성공" if scraping_stats['today_processed'] > 0 else "처리된 신규 기사 없음"
    
    body = f"""
🤖 **오코노미 AI 기사 자동화 보고서** {status_emoji}

📅 **실행 시간**: {current_time}
🎯 **실행 상태**: {status_text}

📊 **오늘의 처리 결과**:
  • 신규 처리: {scraping_stats['today_processed']}개 기사
  • 누적 처리: {scraping_stats['total_processed']}개 기사
  • 마지막 실행: {scraping_stats['last_run']}

📰 **현재 발행된 기사 현황**:
  • 🚗 자동차: {article_counts['automotive']}개
  • 💰 경제: {article_counts['economy']}개
  • 📈 전체: {article_counts['total']}개
"""

    # 발행된 기사 목록 추가
    if article_counts['articles']:
        body += f"""
📝 **발행된 기사 목록**:
"""
        for article in article_counts['articles']:
            # 제목에서 따옴표 제거 및 정리
            clean_title = article['title'].strip('"').replace('&quot;', '"')
            body += f"  • [{article['category']}] [{clean_title}]({article['url']})\n"

    body += f"""
🌐 **사이트**: https://okonomis.com

---
자동 발송 시스템 by 오코노미 AI
    """
    
    return body

def send_report_email():
    """기사 자동화 보고서 이메일 발송"""
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
        print("이메일 설정이 완료되지 않았습니다.")
        return False
    
    try:
        # 이메일 내용 생성
        subject = "🤖 오코노미 AI 기사 자동화 보고서"
        body = create_report_email_content()
        
        # 이메일 메시지 객체 생성
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL
        msg.set_content(body)
        
        # Gmail SMTP 서버에 연결하여 이메일 발송
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        
        print("✅ 보고서 이메일 발송 성공!")
        print(f"📧 수신자: {RECIPIENT_EMAIL}")
        print(f"⏰ 발송 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
        return True
        
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {e}")
        return False

def send_error_email(error_message="스크래퍼 실행 중 오류가 발생했습니다"):
    """에러 발생 시 이메일 보고서 발송"""
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
        print("이메일 설정이 완료되지 않았습니다.")
        return False
    
    try:
        # 한국 시간으로 현재 시간 가져오기
        current_time = datetime.now(KST).strftime("%Y년 %m월 %d일 %H시 %M분 (KST)")
        
        subject = "🚨 오코노미 AI 스크래퍼 오류 알림"
        body = f"""
🚨 **오코노미 AI 스크래퍼 실행 실패**

📅 **발생 시간**: {current_time}
❌ **상태**: 실행 실패

**오류 내용**:
{error_message}

스크래퍼 실행 중 문제가 발생했습니다.
GitHub Actions 로그를 확인하여 자세한 내용을 파악해주세요.

🔧 **확인 사항**:
• API 키 설정 상태
• 네트워크 연결 상태  
• 사이트맵 URL 접근 가능 여부
• 시스템 자원 상태

🌐 **GitHub Actions**: https://github.com/[repository]/actions
⚙️ **시스템**: GitHub Actions + n8n Automation

---
오코노미 AI 자동화 시스템 오류 알림
        """
        
        # 이메일 메시지 객체 생성
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL
        msg.set_content(body)
        
        # Gmail SMTP 서버에 연결하여 이메일 발송
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        
        print("🚨 Error report email sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error email sending failed: {e}")
        return False

def create_email_content():
    """기존 뉴스 브리핑 이메일 내용 생성 (호환성 유지)"""
    return create_report_email_content()

# 메인 실행 부분
if __name__ == "__main__":
    import sys
    
    # 명령행 인자로 에러 모드 체크
    if len(sys.argv) > 1 and sys.argv[1] == "error":
        error_msg = sys.argv[2] if len(sys.argv) > 2 else "스크래퍼 실행 중 오류가 발생했습니다"
        send_error_email(error_msg)
    else:
        # 기본 동작: 보고서 이메일 발송
        send_report_email() 