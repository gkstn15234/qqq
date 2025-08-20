import os
import re
from datetime import datetime

def fix_article_dates():
    """8월 12일~16일 기사들의 날짜를 올바르게 수정합니다."""
    automotive_dir = "content/automotive"
    
    # 날짜별 매핑
    date_mappings = {
        '20250812': '2025-08-12',
        '20250813': '2025-08-13', 
        '20250814': '2025-08-14',
        '20250815': '2025-08-15',
        '20250816': '2025-08-16'
    }
    
    fixed_count = 0
    
    for filename in os.listdir(automotive_dir):
        if filename.endswith('.md'):
            # 파일명에서 날짜 추출
            for file_date, correct_date in date_mappings.items():
                if file_date in filename:
                    filepath = os.path.join(automotive_dir, filename)
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # 파일명에서 시간 번호 추출 (예: -01, -02, ...)
                        time_match = re.search(rf'{file_date}-(\d{{2}})\.md$', filename)
                        if time_match:
                            time_number = int(time_match.group(1))
                            # 시간 계산 (08:30부터 1시간씩)
                            hour = 8 + (time_number - 1)
                            if hour > 17:  # 17시를 넘으면 다음날로
                                hour = 8 + ((time_number - 1) % 10)
                            time_str = f"{hour:02d}:30:00"
                        else:
                            time_str = "08:30:00"
                        
                        # date 필드 업데이트
                        new_datetime = f"{correct_date}T{time_str}+09:00"
                        content = re.sub(
                            r'date: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00',
                            f'date: {new_datetime}',
                            content
                        )
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        fixed_count += 1
                        print(f"수정됨: {filename} -> {new_datetime}")
                        
                    except Exception as e:
                        print(f"오류 발생 {filename}: {e}")
                    
                    break  # 한 파일은 한 번만 처리
    
    print(f"총 {fixed_count}개 파일 날짜 수정 완료")

if __name__ == "__main__":
    fix_article_dates()