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
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 문제가 되는 따옴표들을 단순하게 제거하거나 변경
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    if line.startswith('title: '):
                        # 제목에서 문제가 되는 따옴표들을 처리
                        if '…' in line and '"' in line:
                            # 따옴표를 단일 따옴표로 변경
                            title_content = line[7:].strip()
                            if title_content.startswith('"') and title_content.endswith('"'):
                                inner_content = title_content[1:-1]
                                # 내부 따옴표 제거
                                inner_content = inner_content.replace('"', '').replace("'", '')
                                lines[i] = f'title: "{inner_content}"'
                
                new_content = '\n'.join(lines)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                fixed_count += 1
                print(f"수정됨: {filename}")
                
            except Exception as e:
                print(f"오류 발생 {filename}: {e}")
    
    print(f"총 {fixed_count}개 파일 수정 완료")

if __name__ == "__main__":
    fix_yaml_frontmatter()