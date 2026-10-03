import os, sys, re, unicodedata
from pathlib import Path
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

def clean_key(s):
    if not s: return ''
    s = unicodedata.normalize('NFKC', str(s))
    s = re.sub(r'[0-9０-９\.\s\-\—\―\:\：\(\)\（\）\「\」\『\』\【\】\・\…\、\。]', '', s)
    return s.lower()

def similarity(a, b):
    return SequenceMatcher(None, clean_key(a), clean_key(b)).ratio()

# Load original HTML generated from captures
src_html = Path(r"C:\Users\tonbo\Desktop\主要登場人物.html").read_text(encoding='utf-8')
soup = BeautifulSoup(src_html, 'html.parser')

# Correct Title
true_title = "「対話」がやってきた"
soup.title.string = true_title

# 1. Clean meta-descriptions / noise
for p in soup.find_all(['p', 'div', 'blockquote', 'li']):
    t = p.get_text(strip=True)
    if any(k in t for k in [
        'テキスト情報が含まれていないため', '代替テキスト（Alt Text）を作成しました',
        '画像の説明：', '画面構成', '視覚要素', '配置された大きな三角形', 'バックパックを背負った人物のイラスト'
    ]):
        p.decompose()

# 2. Fix the First H1 / Front Matter
h1_tags = soup.find_all('h1')
for h1 in h1_tags:
    if '主要登場人物' in h1.get_text():
        h1.name = 'h2'
    elif '対話' in h1.get_text():
        h1.decompose() # It's document title

# Ensure 序章 heading exists
has_joshou = False
for h in soup.find_all(['h1', 'h2', 'h3']):
    if '序章' in h.get_text() or '風の話' in h.get_text():
        has_joshou = True
        break

if not has_joshou:
    # Insert 序章 before the first paragraph of the intro
    for p in soup.find_all('p'):
        if 'うち、は、形骸化した志望動機' in p.get_text():
            new_h2 = soup.new_tag('h2')
            new_h2.string = "序章 風の話――手懐けられる責任"
            p.insert_before(new_h2)
            break

# Ensure 目次 exists and clean nav
for nav in soup.find_all('nav'):
    nav.decompose()

toc_h = None
for h in soup.find_all(['h1', 'h2', 'h3']):
    if '目次' in h.get_text():
        toc_h = h
        toc_h.name = 'h2'
        break

# TOC items list for 『「対話」がやってきた』
toc_items = [
    '序章 風の話――手懐けられる責任',
    '風、土、人',
    '「対話」という万能薬',
    '上がり',
    '第一章 水の話――合理性はどこから',
    '現場の合理性',
    'ことばが走り、ことばで転ぶ',
    '制度・構造に規定される人間',
    '水臭い、水を得た魚、水に流す',
    '第二章 理の話――「無理」が生まれる場所',
    '臆病者の安全地帯',
    '対話が会社にやってきた',
    '仕組みを変えれば「合理性」が変わる',
    '鋭い人と理',
    '「お客様に寄り添う」「自律的な行動」「風通しの良い職場」',
    '第三章 青の話――声を上げるということ',
    '2週目のカイゼン',
    '青二才はゆく',
    '第四章 器の話――「なかったことにしない」',
    '話せない組織、話せばどうにかなる組織',
    'なかったことにしない',
    '対話による組織風土改革',
    '内部通報制度の経緯整理と再設計',
    '十字架とりんご',
    '担当さん',
    '「今じゃない」',
    '無数の選択肢',
    '第五章 人の話――風土ではなく残るもの',
    '制度の仕掛け',
    '正しくて疲れる',
    '報われるのか',
    '〈評価面談の前に、少し話せるか〉',
    '経営者',
    '構造と対話を結ぶ人',
    '碧い光',
    '終章 碧い森の話',
    '自称デザイナー',
    'また嫌われるやつ',
    '碧の魔法'
]

# Normalize headings
all_headings = []
for i, h in enumerate(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])):
    if h == toc_h: continue
    t = h.get_text(strip=True)
    if any(k in t for k in ["序章", "終章", "第一章", "第二章", "第三章", "第四章", "第五章", "第1章", "第2章", "第3章", "第4章", "第5章", "主要登場人物", "目次", "あとがき", "参考文献", "著者紹介"]):
        h.name = 'h2'
    elif '⏱' in t:
        h.name = 'h2'
    else:
        h.name = 'h3'
    uid = f"section-{i+1}"
    h['id'] = uid
    all_headings.append({
        'id': uid,
        'elem': h,
        'text': t,
        'clean': clean_key(t)
    })

# Build TOC
nav_tag = soup.new_tag('nav', **{'aria-label': '目次'})
ol_tag = soup.new_tag('ol')
nav_tag.append(ol_tag)

last_idx = 0
for it in toc_items:
    c_t = clean_key(it)
    best_h = None
    best_score = 0
    best_i = -1
    
    for i in range(last_idx, len(all_headings)):
        h = all_headings[i]
        sim = similarity(c_t, h['clean'])
        if c_t in h['clean'] or h['clean'] in c_t:
            sim = max(sim, 0.90)
        if sim > best_score:
            best_score = sim
            best_h = h
            best_i = i
            if sim >= 0.90:
                break
                
    li_tag = soup.new_tag('li')
    if best_h and best_score >= 0.40:
        if best_i >= last_idx:
            last_idx = best_i
        a_tag = soup.new_tag('a', href=f"#{best_h['id']}")
        a_tag.string = it
        li_tag.append(a_tag)
    else:
        li_tag.string = it
    ol_tag.append(li_tag)

if toc_h:
    toc_h.insert_after(nav_tag)

# Save to Desktop as 「対話」がやってきた.html
target_file = Path(r"C:\Users\tonbo\Desktop\「対話」がやってきた.html")
target_file.write_text(str(soup), encoding='utf-8')
print("Successfully generated:", target_file)
