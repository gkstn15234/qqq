#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob

def safe_fix_article(filepath):
    """UTF-8 인코딩을 안전하게 처리하면서 H1 제거, H2를 H5로 변경"""
    try:
        # UTF-8로 안전하게 읽기
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        new_lines = []
        frontmatter_count = 0
        in_frontmatter = False
        changes_made = False
        
        for line in lines:
            # YAML frontmatter 추적
            if line.strip() == '---':
                frontmatter_count += 1
                if frontmatter_count == 1:
                    in_frontmatter = True
                elif frontmatter_count == 2:
                    in_frontmatter = False
                new_lines.append(line)
                continue
            
            # frontmatter 내부는 수정하지 않음
            if in_frontmatter:
                new_lines.append(line)
                continue
            
            # frontmatter 끝난 후에만 처리
            if frontmatter_count >= 2:
                # H1 태그 제거
                if line.startswith('# ') and not line.startswith('##'):
                    print(f"  🗑️ H1 제거: {line[:40]}...")
                    changes_made = True
                    continue  # 이 줄 제거
                
                # H2를 H5로 변경
                elif line.startswith('## '):
                    new_line = line.replace('## ', '##### | ')
                    print(f"  🔄 H2→H5: {line[:25]} → {new_line[:30]}...")
                    new_lines.append(new_line)
                    changes_made = True
                    continue
            
            new_lines.append(line)
        
        if changes_made:
            # UTF-8로 안전하게 쓰기
            with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
                f.write('\n'.join(new_lines))
            return True
        
        return False
        
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        return False

# 기사 파일 수집
print("🔍 기사 파일 수집 중...")
article_files = []

# economy 폴더
for filepath in glob.glob('content/economy/*.md'):
    article_files.append(filepath)

# automotive 폴더  
for filepath in glob.glob('content/automotive/*.md'):
    article_files.append(filepath)

print(f"📁 수정할 기사: {len(article_files)}개")

# 각 파일 처리
fixed_count = 0
for filepath in article_files:
    filename = os.path.basename(filepath)
    print(f"\n📄 처리 중: {filename}")
    
    if safe_fix_article(filepath):
        fixed_count += 1
        print(f"  ✅ 수정 완료!")
    else:
        print(f"  ⏭️ 변경사항 없음")

print(f"\n🎯 최종 결과: {fixed_count}/{len(article_files)} 파일 수정됨")
print("✅ UTF-8 인코딩으로 안전하게 처리되었습니다!") 