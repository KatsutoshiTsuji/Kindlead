from pathlib import Path
import re
from bs4 import BeautifulSoup
import unicodedata

def normalize_text(text):
    text = unicodedata.normalize('NFKC', text)
    return text.strip()

html_path = Path("D:/Katsutoshi/AntiGravity/Kindlead/output.html")
soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")

book_title = "高く売れるものだけ作るドイツ人、いいものを安く売ってしまう日本人"

# 1. 冒頭のheader内のh1を確実に唯一のh1に設定
main_tag = soup.find('main')
header_tag = soup.find('header')

if header_tag:
    for h in header_tag.find_all(['h1', 'h2', 'h3', 'h4']):
        h.name = 'h1'

# 2. main内の見出し階層を論理的に再構築
for h in main_tag.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
    text = normalize_text(h.get_text())
    
    # 判定ルール
    # [Level 2] 章レベル: 「目次」「序章」「第X章」「第Ｘ章」「終章」「謝辞」「著者紹介」「奥付」「カバーデザイン」
    is_chapter = False
    if any(k in text for k in ["目次", "序章", "終章", "謝辞", "著者紹介", "奥付", "カバーデザイン", "著作権", "岩本晃"]):
        is_chapter = True
    elif re.match(r'^第[0-9０-９一二三四五六七八九十]+章', text):
        is_chapter = True
    elif re.match(r'^[0-9０-９]+章\s', text):
        is_chapter = True
        
    if is_chapter:
        h.name = 'h2'
        continue
        
    # [Level 3] 節レベル: 「1 」「2 」「1.」「2.」「1　」「2　」などの大節、または主要な節
    is_section = False
    if re.match(r'^[0-9０-９]+[\s\.\　]', text) and not re.match(r'^[0-9０-９]+\.[0-9０-９]+', text):
        is_section = True
    elif re.match(r'^[一二三四五六七八九十]+[\s\.\　]', text):
        is_section = True
    elif any(k in text for k in ["隠れたチャンピオン", "日本の労働生産性", "フラウンホーファー", "インダストリー4"]):
        # 主要キーワードの節
        if len(text) < 40 and not is_chapter:
            is_section = True

    if is_section:
        h.name = 'h3'
        continue
        
    # [Level 4] 小見出し・項・図表レベル: 「図表X」「凡例」「1.1」など
    if re.match(r'^図表|^凡例|^\([0-9]+\)|^（[0-9]+）', text):
        h.name = 'h4'
        continue
        
    # それ以外の本文内見出し
    # 元がh1/h2だったものはh3またはh4に下げる
    if h.name in ['h1', 'h2']:
        h.name = 'h3'
    elif h.name == 'h3':
        h.name = 'h4'

# 3. IDを綺麗に整理
for idx, h in enumerate(main_tag.find_all(['h2', 'h3', 'h4', 'h5']), 1):
    h['id'] = f"section-{idx}"

# 4. 目次リンクを再構築
headings = []
for h in main_tag.find_all(['h2', 'h3', 'h4']):
    text = normalize_text(h.get_text())
    if "目次" in text:
        continue
    headings.append({
        'id': h['id'],
        'text': text,
        'norm': re.sub(r'[^a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', '', text).lower()
    })

# 目次リスト内のリンク付け
last_idx = -1
for elem in main_tag.find_all(['ol', 'ul']):
    # 目次リストのみ
    for li in elem.find_all('li'):
        li_text = normalize_text(li.get_text())
        norm_li = re.sub(r'[^a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', '', li_text).lower()
        if len(norm_li) < 2:
            continue
            
        best_match = None
        best_score = 0
        best_i = -1
        
        for i, hd in enumerate(headings):
            norm_hd = hd['norm']
            if not norm_hd:
                continue
            score = 0
            if norm_li == norm_hd:
                score = 100
            elif norm_li in norm_hd or norm_hd in norm_li:
                common_len = min(len(norm_li), len(norm_hd))
                score = (common_len / max(len(norm_li), len(norm_hd))) * 80
                
            if i >= last_idx:
                score += 15
                
            if score > best_score and score > 45:
                best_score = score
                best_match = hd
                best_i = i
                
        if best_match:
            last_idx = best_i
            link_tag = soup.new_tag('a', href=f"#{best_match['id']}")
            link_tag.string = li.get_text()
            li.clear()
            li.append(link_tag)

# 保存
html_path.write_text(str(soup), encoding="utf-8")
print("見出しツリーの完全階層化（H1->H2->H3->H4）と目次リンクの再構築が完了しました！")
