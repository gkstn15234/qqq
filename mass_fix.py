#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re

def fix_file(filepath):
    """단일 파일의 H1 제거, H2를 H5로 변경"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 변경 추적
        original = content
        
        # H1 라인 제거 (YAML frontmatter 이후의 # 라인)
        lines = content.split('\n')
        new_lines = []
        frontmatter_end = False
        dash_count = 0
        
        for line in lines:
            if line.strip() == '---':
                dash_count += 1
                if dash_count == 2:
                    frontmatter_end = True
                new_lines.append(line)
                continue
            
            # frontmatter 끝난 후 첫 번째 H1 제거
            if frontmatter_end and line.startswith('# ') and not line.startswith('##'):
                print(f"  🗑️ H1 제거: {line[:40]}...")
                continue
            
            # H2를 H5로 변경
            if line.startswith('## '):
                new_line = line.replace('## ', '##### | ')
                print(f"  🔄 H2→H5: {line[:30]} → {new_line[:30]}...")
                new_lines.append(new_line)
                continue
            
            new_lines.append(line)
        
        new_content = '\n'.join(new_lines)
        
        if new_content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        
        return False
        
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        return False

# 모든 기사 파일 찾기
article_files = []
for root, dirs, files in os.walk('content'):
    for file in files:
        if file.endswith('.md'):
            # 시스템 파일 제외
            if file not in ['_index.md', 'about.md', 'contact.md', 'privacy.md', 
                           'terms.md', 'editorial-guidelines.md', 'youth-protection.md', 'yoon-shin-ae.md']:
                article_files.append(os.path.join(root, file))

print(f"🔍 수정할 기사: {len(article_files)}개")

fixed_count = 0
for filepath in article_files:
    filename = os.path.basename(filepath)
    print(f"\n📄 수정중: {filename}")
    
    if fix_file(filepath):
        fixed_count += 1
        print(f"  ✅ 완료!")
    else:
        print(f"  ⏭️ 변경사항 없음")

print(f"\n🎯 완료: {fixed_count}/{len(article_files)} 파일 수정됨") 