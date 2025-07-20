#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

def fix_article_file(filepath):
    """단일 기사 파일의 H1 제거, H2를 H5로 변경"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        new_lines = []
        in_frontmatter = False
        frontmatter_dash_count = 0
        changes_made = False
        
        for i, line in enumerate(lines):
            # YAML frontmatter 추적
            if line.strip() == '---':
                frontmatter_dash_count += 1
                if frontmatter_dash_count == 1:
                    in_frontmatter = True
                elif frontmatter_dash_count == 2:
                    in_frontmatter = False
                new_lines.append(line)
                continue
            
            # frontmatter 내부는 건드리지 않음
            if in_frontmatter:
                new_lines.append(line)
                continue
            
            # frontmatter 종료 후 처리
            if frontmatter_dash_count >= 2:
                # H1 태그 제거 (# 로 시작하는 줄)
                if line.startswith('# ') and not line.startswith('##'):
                    print(f"  🗑️ H1 제거: {line[:40]}...")
                    changes_made = True
                    continue  # 이 줄을 완전히 제거
                
                # H2를 H5로 변경
                elif line.startswith('## '):
                    new_line = line.replace('## ', '##### | ')
                    print(f"  🔄 H2→H5: {line[:25]} → {new_line[:30]}...")
                    new_lines.append(new_line)
                    changes_made = True
                    continue
            
            new_lines.append(line)
        
        if changes_made:
            new_content = '\n'.join(new_lines)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        
        return False
        
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        return False

# 수정할 기사 파일만 선별
article_files = []

# economy 폴더
economy_dir = 'content/economy'
if os.path.exists(economy_dir):
    for file in os.listdir(economy_dir):
        if file.endswith('.md'):
            article_files.append(os.path.join(economy_dir, file))

# automotive 폴더  
automotive_dir = 'content/automotive'
if os.path.exists(automotive_dir):
    for file in os.listdir(automotive_dir):
        if file.endswith('.md'):
            article_files.append(os.path.join(automotive_dir, file))

print(f"🔍 수정할 기사: {len(article_files)}개")

fixed_count = 0
for filepath in article_files:
    filename = os.path.basename(filepath)
    print(f"\n📄 수정중: {filename}")
    
    if fix_article_file(filepath):
        fixed_count += 1
        print(f"  ✅ 완료!")
    else:
        print(f"  ⏭️ 변경사항 없음")

print(f"\n🎯 최종 결과: {fixed_count}/{len(article_files)} 파일 수정됨") 