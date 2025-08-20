import os
import re

def fix_yaml_frontmatter():
    """YAML 프론트매터의 따옴표 문제를 수정합니다."""
    automotive_dir = "content/automotive"
    
    # 새로 생성된 파일들 (20250817-20250821)
    pattern = r'2025081[7-9]|2025082[01]'
    
    fixed_count = 0
    
    for filename in os.listdir(automotive_dir):
        if re.search(pattern, filename) and filename.endswith('.md'):
            filepath = os.path.join(automotive_dir, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # title과 description의 따옴표 문제 수정
            # 이중 따옴표 안의 따옴표를 이스케이프 처리
            content = re.sub(
                r'title: "([^"]*"[^"]*)"', 
                lambda m: f'title: "{m.group(1).replace(\'"\', \'&quot;\')}"', 
                content
            )
            
            # 또는 단일 따옴표로 감싸기
            content = re.sub(
                r'title: "([^"]*"[^"]*)"',
                r"title: '\1'",
                content
            )
            
            content = re.sub(
                r'description: "([^"]*"[^"]*)"',
                r"description: '\1'",
                content
            )
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            fixed_count += 1
            print(f"수정됨: {filename}")
    
    print(f"총 {fixed_count}개 파일 수정 완료")

if __name__ == "__main__":
    fix_yaml_frontmatter()