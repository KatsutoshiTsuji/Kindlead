from pathlib import Path
import re
from bs4 import BeautifulSoup
import unicodedata
from difflib import SequenceMatcher

def clean_text(s):
    if not s:
        return ""
    s = unicodedata.normalize('NFKC', s)
    # 記号、数字、空白を除去
    s = re.sub(r'[0-9０-９\.\s\-\—\―\:\：\(\)\（\）\「\」\『\』\【\】\・\…\、\。]', '', s)
    return s.lower()

def similarity(a, b):
    return SequenceMatcher(None, clean_text(a), clean_text(b)).ratio()

html_path = Path("D:/Katsutoshi/AntiGravity/Kindlead/output.html")
soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
main_tag = soup.find('main')

# 1. 既存のaタグを全解除
for a in main_tag.find_all('a'):
    a.replace_with(a.get_text())

# 2. 本文開始位置を特定
# 目次見出しより前と後
all_h = main_tag.find_all(['h1', 'h2', 'h3', 'h4'])
toc_h = None
for h in all_h:
    if "目次" in h.get_text():
        toc_h = h
        break

# 3. 本文側のすべての見出し・段落にユニークIDを付与
body_targets = []
in_body = False

for elem in main_tag.find_all(['h2', 'h3', 'h4', 'p']):
    t = elem.get_text(strip=True)
    if "序章" in t and elem.name in ['h2', 'h3'] and "目次" not in t:
        in_body = True
        
    if in_body and len(t) > 2:
        uid = f"target-{len(body_targets) + 1}"
        elem['id'] = uid
        body_targets.append({
            'id': uid,
            'elem': elem,
            'text': t,
            'clean': clean_text(t)
        })

print(f"本文ターゲット数: {len(body_targets)} 件")

# 4. 目次リスト内の全項目を取得
toc_items = []
if toc_h:
    curr = toc_h.next_sibling
    while curr:
        if getattr(curr, 'name', None) in ['ol', 'ul']:
            for li in curr.find_all('li'):
                raw = li.get_text(strip=True)
                if len(raw) > 1:
                    toc_items.append((li, raw))
        elif getattr(curr, 'name', None) in ['h2', 'h3'] and "序章" in curr.get_text():
            # 本文開始直前の目次内の大項目
            pass
        curr = curr.next_sibling

print(f"目次項目数: {len(toc_items)} 件")

# 5. 各目次項目に対して、最も類似度が高い本文ターゲットを順番に割り当て
last_idx = 0
for li, raw_title in toc_items:
    c_title = clean_text(raw_title)
    if not c_title:
        continue
        
    best_target = None
    best_score = 0
    best_target_idx = -1
    
    # 探索（前回のマッチ位置以降を優先）
    for i in range(last_idx, len(body_targets)):
        bt = body_targets[i]
        sim = similarity(c_title, bt['clean'][:len(c_title) + 10])
        if c_title in bt['clean']:
            sim = max(sim, 0.95)
            
        if sim > best_score:
            best_score = sim
            best_target = bt
            best_target_idx = i
            if sim >= 0.95:
                break
                
    # 後方で見つからなければ全体探索
    if best_score < 0.6:
        for i in range(0, len(body_targets)):
            bt = body_targets[i]
            sim = similarity(c_title, bt['clean'][:len(c_title) + 10])
            if c_title in bt['clean']:
                sim = max(sim, 0.95)
            if sim > best_score:
                best_score = sim
                best_target = bt
                best_target_idx = i
                
    if best_target and best_score >= 0.5:
        last_idx = best_target_idx
        # リンク化
        new_a = soup.new_tag('a', href=f"#{best_target['id']}")
        new_a.string = raw_title
        li.clear()
        li.append(new_a)
        
html_path.write_text(str(soup), encoding="utf-8")
print("完全な1対1の目次リンクマッピングが完了しました！")
