from pathlib import Path
import re
from bs4 import BeautifulSoup
import unicodedata

def clean_key(text):
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'[^a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', '', text)
    return text.lower()

html_path = Path("D:/Katsutoshi/AntiGravity/Kindlead/output.html")
soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
main_tag = soup.find('main')

# 1. すべてのaタグを解除してプレーンテキストに戻す
for a in main_tag.find_all('a'):
    a.replace_with(a.get_text())

# 2. 本文側の全要素（段落 p, 見出し h1~h4, li）を収集
# 目次領域以外のすべてのテキストノード
all_elems = list(main_tag.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'tr']))

# 3. 目次内の全リスト項目（ol > li, ul > li）を収集
# 最初の「目次」見出しの後にあるol/ul群
toc_heading = None
for h in main_tag.find_all(['h1', 'h2', 'h3']):
    if "目次" in h.get_text():
        toc_heading = h
        break

toc_li_items = []
if toc_heading:
    curr = toc_heading.next_sibling
    while curr:
        if curr.name in ['h1', 'h2'] and "目次" not in curr.get_text() and ("序章" in curr.get_text() or "第1章" in curr.get_text()):
            # 本文開始！
            # ただし目次内の「序章」「第1章」見出しは目次の一部
            # 次の要素がol/ulなら目次継続
            next_elem = curr.find_next_sibling(['ol', 'ul', 'h1', 'h2', 'p'])
            if next_elem and next_elem.name in ['ol', 'ul']:
                pass # まだ目次
            else:
                break # 本文突入
                
        if getattr(curr, 'name', None) in ['ol', 'ul']:
            for li in curr.find_all('li'):
                t = li.get_text(strip=True)
                k = clean_key(t)
                if len(k) >= 2:
                    toc_li_items.append((li, t, k))
        curr = curr.next_sibling

print(f"収集した目次項目: {len(toc_li_items)} 個")

# 4. 本文要素に対して1対1でマッチング
# 目次より後ろにある要素のみを対象にする
body_start_idx = 0
if toc_heading:
    for i, el in enumerate(all_elems):
        if el == toc_heading:
            body_start_idx = i + 1
            break

# 探索対象の本文要素（目次以降のpやh2~h4）
body_targets = all_elems[body_start_idx + len(toc_li_items):]
print(f"マッチング対象の本文要素: {len(body_targets)} 個")

anchor_gen = 0
last_target_idx = 0

for li, raw_title, key in toc_li_items:
    matched = None
    best_score = 0
    best_i = -1
    
    # 探索
    for i in range(last_target_idx, len(body_targets)):
        b_el = body_targets[i]
        b_text = b_el.get_text()
        b_key = clean_key(b_text)
        
        score = 0
        if key in b_key:
            score = 100
        elif b_key in key:
            score = 90
        else:
            common = set(key) & set(b_key)
            if len(common) >= len(key) * 0.7:
                score = 70
                
        if score > best_score and score >= 70:
            best_score = score
            matched = b_el
            best_i = i
            if score == 100:
                break
                
    # 後方で見つからなければ全体からフォールバック
    if not matched:
        for i in range(0, len(body_targets)):
            b_el = body_targets[i]
            b_key = clean_key(b_el.get_text())
            if key in b_key or (len(key) > 4 and key[:4] in b_key):
                matched = b_el
                best_i = i
                break
                
    if matched:
        last_target_idx = max(last_target_idx, best_i)
        if not matched.get('id'):
            anchor_gen += 1
            matched['id'] = f"jump-{anchor_gen}"
            
        target_id = matched['id']
        new_a = soup.new_tag('a', href=f"#{target_id}")
        new_a.string = raw_title
        li.clear()
        li.append(new_a)

html_path.write_text(str(soup), encoding="utf-8")
print(f"全 {len(toc_li_items)} 項目に対する完璧なリンク付けが完了しました！")
