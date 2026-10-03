from bs4 import BeautifulSoup
import re, unicodedata
from difflib import SequenceMatcher
from pathlib import Path

def clean_key(s):
    if not s: return ''
    s = unicodedata.normalize('NFKC', str(s))
    s = re.sub(r'[0-9０-９\.\s\-\—\―\:\：\(\)\（\）\「\」\『\』\【\】\・\…\、\。]', '', s)
    return s.lower()

def similarity(a, b):
    return SequenceMatcher(None, clean_key(a), clean_key(b)).ratio()

# Test building from original HTML content
raw_html = Path(r"C:\Users\tonbo\Downloads\誰のためのアクセシビリティ_.html").read_text(encoding='utf-8')
soup = BeautifulSoup(raw_html, 'html.parser')

# Remove any previous navs and meta paragraphs
for nav in soup.find_all('nav'):
    nav.decompose()
for p in soup.find_all('p'):
    t = p.get_text(strip=True)
    if any(k in t for k in ['テキスト情報が含まれていないため', '代替テキスト（Alt Text）を作成しました', '画像の説明：']):
        p.decompose()

# The genuine 31 TOC items from the book's TOC page:
toc_items = [
    'はじめに',
    '1 アクセシビリティの謎',
    '駅までの道',
    '一本の脚と、バラバラに上げられた腕',
    '「障害者の村」が明らかにすること',
    '障害のある人にとっての「障害」とは何か',
    '障害のある人が主体となるアクセシビリティへ',
    '2 音声描写との格闘の記録',
    'つくることと見ることをつなぐ音声描写',
    '『音で観るダンスのワークインプログレス』',
    '音で観るダンスとは何だったのか',
    '3 テクノロジーは鑑賞をアクセシブルにするか',
    'AIとの鑑賞ワークショップ',
    '鑑賞ワークショップを振り返る　忖度しないテクノロジー',
    '4 障害のある人の文化から捉え直す',
    '疑似体験と生きられた経験',
    'アメリカで学んだ、コミュニティとともにあること',
    '生きられた経験1　ろう者がつくるもうひとつの文化　牧原依里さん',
    '生きられた経験2　〝ふつう〟を反転させる物語　横道誠さん',
    '5 ともに楽しむために実装していく',
    '尊厳とデザインの危うい関係',
    '生きられた経験3　続けられるウェブアクセシビリティを　伊敷政英さん',
    'ゲームはアクセシビリティの実験場',
    '生きられた経験4　言い訳をつくらずに闘うために　Jeniさん',
    '生きられた経験5　どんな手がかりも見落とさない　野澤幸男くん',
    '6 座談会　あいだのアクセシビリティ',
    '7 アクセシビリティの生態系',
    'ノイズになって気づいたこと',
    '生きられた経験6　ケアすることから生まれる　中谷優希さんと杉浦一基さん',
    'アクセシビリティから遠くにいる人たち',
    'あとがき',
    '参考文献'
]

# Re-insert the Chapter 1 heading if it was lost in this file
has_chap1 = False
for h in soup.find_all(['h1', 'h2', 'h3', 'h4']):
    if '1' in h.get_text() and 'アクセシビリティの謎' in h.get_text() and '目次' not in h.get_text():
        has_chap1 = True
        break

if not has_chap1:
    for h in soup.find_all(['h2', 'h3', 'h4']):
        if '駅までの道' in h.get_text() or '駅での道' in h.get_text():
            new_h = soup.new_tag('h2')
            new_h.string = "1 アクセシビリティの謎"
            h.insert_before(new_h)
            break

# Normalize headings
for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
    t = unicodedata.normalize('NFKC', h.get_text()).strip()
    if any(k in t for k in ["目次", "序章", "終章", "謝辞", "著者紹介", "奥付", "著作権", "はじめに", "おわりに", "あとがき", "参考文献"]) or re.match(r'^(第[0-9０-９一二三四五六七八九十]+章|[0-9０-９]+[\s\.\　])', t):
        h.name = 'h2'
    elif re.match(r'^図表|^凡例|^\([0-9]+\)|^（[0-9]+）', t):
        h.name = 'h4'
    elif h.name in ['h1', 'h2']:
        h.name = 'h3'

# Find TOC heading
toc_h = None
for h in soup.find_all(['h1', 'h2', 'h3', 'h4']):
    if '目次' in h.get_text():
        toc_h = h
        break

# Index all headings
all_headings = []
for i, h in enumerate(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])):
    if h == toc_h: continue
    uid = f"section-{i+1}"
    h['id'] = uid
    all_headings.append({
        'id': uid,
        'elem': h,
        'text': h.get_text(strip=True),
        'clean': clean_key(h.get_text(strip=True))
    })

nav_tag = soup.new_tag('nav', **{'aria-label': '目次'})
ol_tag = soup.new_tag('ol')
nav_tag.append(ol_tag)

last_idx = 0
matched_count = 0
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
                
    if best_score < 0.40:
        for i, h in enumerate(all_headings):
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
    if best_h and best_score >= 0.35:
        if best_i >= last_idx:
            last_idx = best_i
        matched_count += 1
        a_tag = soup.new_tag('a', href=f"#{best_h['id']}")
        a_tag.string = it
        li_tag.append(a_tag)
        print(f"  LINK: {it} -> #{best_h['id']} ({best_h['text']})")
    else:
        li_tag.string = it
        print(f"  TEXT: {it}")
    ol_tag.append(li_tag)

if toc_h:
    toc_h.insert_after(nav_tag)

# Write to both Desktop and Downloads
desktop_file = Path(r"C:\Users\tonbo\Desktop\誰のためのアクセシビリティ_.html")
downloads_file = Path(r"C:\Users\tonbo\Downloads\誰のためのアクセシビリティ_.html")
desktop_file.write_text(str(soup), encoding='utf-8')
downloads_file.write_text(str(soup), encoding='utf-8')
print(f"\nCompleted! Written to Desktop and Downloads ({matched_count}/{len(toc_items)} matched).")
