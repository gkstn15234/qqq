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

# OpenAI 모델 선택 (기본값: gpt-4.1)
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1')

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

# ==================== 모델별 설정 ====================
MODEL_CONFIGS = {
    'gpt-4.1': {
        'max_tokens': 32768,
        'temperature': 0.7,
        'description': 'GPT-4.1 - 최신 고성능 모델'
    },
    'gpt-4o-mini': {
        'max_tokens': 16384,
        'temperature': 0.7,
        'description': 'GPT-4o Mini - 빠르고 효율적인 모델'
    },
    'gpt-4o': {
        'max_tokens': 4096,
        'temperature': 0.7,
        'description': 'GPT-4o - 균형잡힌 성능 모델'
    },
    'gpt-4': {
        'max_tokens': 8192,
        'temperature': 0.7,
        'description': 'GPT-4 - 고품질 모델'
    },
    'gpt-3.5-turbo': {
        'max_tokens': 4096,
        'temperature': 0.7,
        'description': 'GPT-3.5 Turbo - 비용 효율적인 모델'
    }
}

def get_scraping_statistics():
    """AI 스크래퍼 실행 결과 통계 가져오기 (사이트맵별 분류 포함)"""
    try:
        db_path = 'processed_articles.db'
        if not os.path.exists(db_path):
            return {
                'total_processed': 0,
                'today_processed': 0,
                'last_run': 'N/A',
                'news_sitemap': 0,
                'general_sitemap': 0
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
        
        # 사이트맵별 분류 (URL 패턴 기반 추정)
        cursor.execute("""
            SELECT COUNT(*) FROM processed_articles 
            WHERE url LIKE '%/news/%' OR url LIKE '%/breaking/%'
            AND DATE(processed_date) = ?
        """, (today,))
        news_sitemap = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM processed_articles 
            WHERE (url NOT LIKE '%/news/%' AND url NOT LIKE '%/breaking/%')
            AND DATE(processed_date) = ?
        """, (today,))
        general_sitemap = cursor.fetchone()[0]
        
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
            'last_run': last_run,
            'news_sitemap': news_sitemap,
            'general_sitemap': general_sitemap
        }
        
    except Exception as e:
        print(f"통계 가져오기 실패: {e}")
        return {
            'total_processed': 0,
            'today_processed': 0,
            'last_run': 'Error',
            'news_sitemap': 0,
            'general_sitemap': 0
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
        import frontmatter
    except ImportError:
        print("Warning: frontmatter module not found. Using basic file counting.")
        return count_articles_basic()
    
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
        model_config = MODEL_CONFIGS.get(OPENAI_MODEL, MODEL_CONFIGS['gpt-4.1'])
        
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

🗺️ **사이트맵별 분류**:
  • 📰 뉴스 사이트맵 (20%): {scraping_stats['news_sitemap']}개
  • 📄 일반 사이트맵 (200개): {scraping_stats['general_sitemap']}개

📰 **현재 발행된 기사 현황**:
      • 🚗 일반사이트맵(자동차): {article_counts['automotive']}개
  • 💰 뉴스사이트맵(경제): {article_counts['economy']}개
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
    # 환경변수 디버깅
    print(f"🔍 Email Debug Info:")
    print(f"   SENDER_EMAIL: {'✅ 설정됨' if SENDER_EMAIL else '❌ 없음'}")
    print(f"   SENDER_PASSWORD: {'✅ 설정됨' if SENDER_PASSWORD else '❌ 없음'}")
    print(f"   RECIPIENT_EMAIL: {'✅ 설정됨' if RECIPIENT_EMAIL else '❌ 없음'}")
    print(f"   OPENAI_API_KEY: {'✅ 설정됨' if OPENAI_API_KEY else '❌ 없음'}")
    
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
        print("❌ 이메일 설정이 완료되지 않았습니다.")
        print("   필요한 환경변수: SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL")
        return False
    
    try:
        print("📧 이메일 전송 시작...")
        
        # 이메일 내용 생성
        print("   📝 이메일 내용 생성 중...")
        subject = "🤖 오코노미 AI 기사 자동화 보고서"
        body = create_report_email_content()
        
        # 이메일 메시지 객체 생성
        print("   📨 이메일 메시지 객체 생성 중...")
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL
        msg.set_content(body)
        
        # Gmail SMTP 서버에 연결하여 이메일 발송
        print("   🔗 Gmail SMTP 서버 연결 중...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            print("   🔐 로그인 시도 중...")
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            print("   📤 이메일 전송 중...")
            smtp.send_message(msg)
        
        print("✅ 보고서 이메일 발송 성공!")
        print(f"📧 수신자: {RECIPIENT_EMAIL}")
        print(f"⏰ 발송 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ SMTP 인증 실패: {e}")
        print("   💡 확인사항:")
        print("      - Gmail 앱 비밀번호가 올바른지 확인")
        print("      - 2단계 인증이 활성화되어 있는지 확인")
        print("      - 앱 비밀번호를 사용하고 있는지 확인")
        return False
    except smtplib.SMTPConnectError as e:
        print(f"❌ SMTP 연결 실패: {e}")
        print("   💡 네트워크 연결을 확인해주세요")
        return False
    except smtplib.SMTPRecipientsRefused as e:
        print(f"❌ 수신자 주소 거부: {e}")
        print("   💡 수신자 이메일 주소를 확인해주세요")
        return False
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {e}")
        print(f"   🔍 에러 타입: {type(e).__name__}")
        import traceback
        print(f"   📋 상세 에러:\n{traceback.format_exc()}")
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

def test_email_connection():
    """이메일 연결 테스트 함수"""
    print("🧪 이메일 연결 테스트 시작...")
    
    # 환경변수 확인
    print(f"📋 환경변수 확인:")
    print(f"   SENDER_EMAIL: {SENDER_EMAIL[:5]}***@{SENDER_EMAIL.split('@')[1] if SENDER_EMAIL and '@' in SENDER_EMAIL else 'None'}")
    print(f"   SENDER_PASSWORD: {'***설정됨***' if SENDER_PASSWORD else '❌ 없음'}")
    print(f"   RECIPIENT_EMAIL: {RECIPIENT_EMAIL[:3]}***@{RECIPIENT_EMAIL.split('@')[1] if RECIPIENT_EMAIL and '@' in RECIPIENT_EMAIL else 'None'}")
    
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
        print("❌ 환경변수가 설정되지 않았습니다!")
        return False
    
    try:
        print("🔗 SMTP 서버 연결 테스트...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            print("🔐 로그인 테스트...")
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            print("✅ 이메일 연결 테스트 성공!")
            return True
            
    except smtplib.SMTPAuthenticationError:
        print("❌ Gmail 인증 실패!")
        print("💡 해결방법:")
        print("   1. Gmail 2단계 인증 활성화")
        print("   2. 앱 비밀번호 생성 (https://myaccount.google.com/apppasswords)")
        print("   3. 생성된 앱 비밀번호를 SENDER_PASSWORD에 설정")
        return False
    except Exception as e:
        print(f"❌ 연결 테스트 실패: {e}")
        return False

# 메인 실행 부분
if __name__ == "__main__":
    import sys
    
    # 명령행 인자 처리
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test":
            # 이메일 연결 테스트
            print("=" * 50)
            print("🧪 이메일 시스템 테스트")
            print("=" * 50)
            success = test_email_connection()
            if success:
                print("\n✅ 이메일 시스템이 정상적으로 작동합니다!")
            else:
                print("\n❌ 이메일 시스템에 문제가 있습니다.")
            print("=" * 50)
            
        elif command == "error":
            # 에러 이메일 발송
            error_msg = sys.argv[2] if len(sys.argv) > 2 else "스크래퍼 실행 중 오류가 발생했습니다"
            send_error_email(error_msg)
            
        elif command == "send":
            # 강제 보고서 이메일 발송
            print("📧 보고서 이메일 강제 발송...")
            send_report_email()
            
        else:
            print("사용법:")
            print("  python send_email.py test    # 이메일 연결 테스트")
            print("  python send_email.py send    # 보고서 이메일 발송")
            print("  python send_email.py error   # 에러 이메일 발송")
    else:
        # 기본 동작: 보고서 이메일 발송
        send_report_email() 