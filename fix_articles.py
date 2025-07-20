#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 발행된 모든 기사의 헤딩 구조 수정 스크립트
- H1 태그 제거 (# 제목)
- H2를 H5로 변경 (## → ##### |)
- 세로 막대기 추가
"""

import os
import re
import glob

def fix_article_headings(content):
    """기사 내용의 헤딩 구조를 수정"""
    lines = content.split('\n')
    fixed_lines = []
    in_frontmatter = False
    frontmatter_count = 0
    
    for line in lines:
        # YAML frontmatter 영역 확인
        if line.strip() == '---':
            frontmatter_count += 1
            if frontmatter_count == 2:
                in_frontmatter = False
            elif frontmatter_count == 1:
                in_frontmatter = True
            fixed_lines.append(line)
            continue
        
        # frontmatter 내부는 수정하지 않음
        if in_frontmatter:
            fixed_lines.append(line)
            continue
        
        # H1 태그 제거 (# 로 시작하는 줄)
        if line.startswith('# ') and not line.startswith('##'):
            print(f"  ❌ H1 제거: {line[:50]}...")
            continue  # H1 줄 완전히 제거
        
        # H2를 H5로 변경하고 세로 막대기 추가
        elif line.startswith('## '):
            new_line = line.replace('## ', '##### | ')
            print(f"  🔄 H2→H5: {line[:30]} → {new_line[:30]}...")
            fixed_lines.append(new_line)
        
        # 이미 H5인데 세로 막대기가 없으면 추가
        elif re.match(r'^##### [^|]', line):
            new_line = re.sub(r'^##### ', '##### | ', line)
            print(f"  📝 H5 막대기 추가: {line[:30]} → {new_line[:30]}...")
            fixed_lines.append(new_line)
        
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def process_markdown_files(directory):
    """지정된 디렉토리의 모든 마크다운 파일 처리"""
    pattern = os.path.join(directory, "**/*.md")
    md_files = glob.glob(pattern, recursive=True)
    
    # 시스템 파일 제외
    exclude_files = ['_index.md', 'about.md', 'contact.md', 'privacy.md', 
                    'terms.md', 'editorial-guidelines.md', 'youth-protection.md']
    
    md_files = [f for f in md_files if not any(exclude in f for exclude in exclude_files)]
    
    print(f"📁 Found {len(md_files)} article files to process")
    
    processed_count = 0
    
    for file_path in md_files:
        try:
            print(f"\n📄 Processing: {os.path.basename(file_path)}")
            
            # 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # 헤딩 구조 수정
            fixed_content = fix_article_headings(original_content)
            
            # 변경사항이 있는 경우에만 저장
            if fixed_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                print(f"  ✅ Updated: {file_path}")
                processed_count += 1
            else:
                print(f"  ⏭️ No changes needed")
                
        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {e}")
    
    return processed_count

def main():
    """메인 함수"""
    print("🚀 Starting article heading structure fix...")
    print("🔧 Changes to apply:")
    print("   - Remove H1 tags (# title)")
    print("   - Convert H2 to H5 (## → ##### |)")
    print("   - Add vertical bar to H5 headings")
    
    content_dir = "content"
    
    if not os.path.exists(content_dir):
        print(f"❌ Content directory not found: {content_dir}")
        return
    
    processed = process_markdown_files(content_dir)
    
    print(f"\n📊 Summary:")
    print(f"✅ Successfully processed: {processed} files")
    print(f"🎯 All articles now follow the new heading structure!")

if __name__ == "__main__":
    main() 