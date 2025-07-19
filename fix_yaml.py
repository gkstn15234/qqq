#!/usr/bin/env python3
"""
YAML front matter 오류를 수정하는 스크립트
description 필드에서 여러 줄 문제를 해결
"""

import os
import re
import glob

def fix_yaml_description(file_path):
    """파일의 YAML description을 수정"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # YAML front matter 패턴 찾기
        yaml_pattern = r'^---\n(.*?)\n---\n(.*)$'
        match = re.match(yaml_pattern, content, re.DOTALL)
        
        if not match:
            return False
        
        yaml_content, body_content = match.groups()
        
        # 문제가 있는 description 패턴 찾기
        desc_pattern = r'description: "([^"]*\n[^"]*)"'
        desc_match = re.search(desc_pattern, yaml_content, re.DOTALL)
        
        if desc_match:
            # 여러 줄의 description을 한 줄로 변환
            old_desc = desc_match.group(1)
            
            # 첫 번째 줄만 사용하거나 적절한 요약 생성
            lines = [line.strip() for line in old_desc.split('\n') if line.strip()]
            
            if lines:
                # 마크다운 헤더나 특수문자 제거
                first_line = lines[0]
                first_line = re.sub(r'^#+\s*', '', first_line)  # 마크다운 헤더 제거
                first_line = first_line.replace('"', "'")  # 따옴표 처리
                
                # 150자로 제한
                if len(first_line) > 150:
                    first_line = first_line[:150] + "..."
                
                new_desc = first_line
            else:
                # 파일명에서 제목 추출
                filename = os.path.basename(file_path).replace('.md', '').replace('-', ' ')
                new_desc = f"{filename}에 대한 정보입니다."
            
            # YAML 수정
            new_yaml = yaml_content.replace(desc_match.group(0), f'description: "{new_desc}"')
            
            # 파일 다시 작성
            new_content = f"---\n{new_yaml}\n---\n{body_content}"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"✅ Fixed: {file_path}")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def main():
    """메인 함수"""
    print("🔧 YAML description 오류 수정 시작...")
    
    # content 디렉토리의 모든 마크다운 파일 찾기
    md_files = glob.glob('content/**/*.md', recursive=True)
    
    fixed_count = 0
    
    for file_path in md_files:
        if fix_yaml_description(file_path):
            fixed_count += 1
    
    print(f"\n📊 수정 완료: {fixed_count}개 파일 수정됨")

if __name__ == "__main__":
    main() 