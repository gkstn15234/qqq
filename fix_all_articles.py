#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob

def fix_single_file(filepath):
    """단일 파일의 헤딩을 수정"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        lines = content.split('\n')
        fixed_lines = []
        in_frontmatter = False
        frontmatter_dashes = 0
        changes_made = False
        
        for line in lines:
            # YAML frontmatter 감지
            if line.strip() == '---':
                frontmatter_dashes += 1
                if frontmatter_dashes == 1:
                    in_frontmatter = True
                elif frontmatter_dashes == 2:
                    in_frontmatter = False
                fixed_lines.append(line)
                continue
            
            # frontmatter 내부는 건드리지 않음
            if in_frontmatter:
                fixed_lines.append(line)
                continue
            
            # H1 제거 (# 로 시작)
            if line.startswith('# '):
                print(f"  ❌ H1 제거: {line[:40]}...")
                changes_made = True
                continue
            
            # H2를 H5로 변경 (## 을 ##### | 로)
            elif line.startswith('## '):
                new_line = line.replace('## ', '##### | ')
                print(f"  🔄 H2→H5: {line[:30]} → {new_line[:30]}...")
                fixed_lines.append(new_line)
                changes_made = True
            
            else:
                fixed_lines.append(line)
        
        if changes_made:
            new_content = '\n'.join(fixed_lines)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        
        return False
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    # content 디렉토리의 모든 .md 파일 찾기
    md_files = []
    for root, dirs, files in os.walk('content'):
        for file in files:
            if file.endswith('.md'):
                filepath = os.path.join(root, file)
                # 시스템 파일 제외
                if not any(x in file for x in ['_index.md', 'about.md', 'contact.md', 'privacy.md', 'terms.md', 'editorial-guidelines.md', 'youth-protection.md']):
                    md_files.append(filepath)
    
    print(f"🔍 Found {len(md_files)} article files")
    
    processed = 0
    for filepath in md_files:
        filename = os.path.basename(filepath)
        print(f"\n📄 Processing: {filename}")
        
        if fix_single_file(filepath):
            processed += 1
            print(f"  ✅ Updated!")
        else:
            print(f"  ⏭️ No changes needed")
    
    print(f"\n📊 Summary: {processed}/{len(md_files)} files updated")

if __name__ == "__main__":
    main() 