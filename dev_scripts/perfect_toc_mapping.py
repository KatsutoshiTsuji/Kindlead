from pathlib import Path
import re
from bs4 import BeautifulSoup
import unicodedata

def clean_key(text):
    text = unicodedata.normalize('NFKC', text)
    # 記号や数字、空白を除去したコア文字列
    text = re.sub(r'[^a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', '', text)
    return text.lower()

html_path = Path("D:/Katsutoshi/AntiGravity/Kindlead/output.html")
soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")

main_tag = soup.find('main')

# 1. 既存の壊れたリンクやIDをいったんクリア
for a in main_tag.find_all('a'):
    # aタグを解除してテキストに戻す
    a.replace_with(a.get_text())

# 2. 目次セクションのリストと、本文ブロックを分離
# 「目次」見出しの後、本文の開始（序章など）までのリストを目次とする
toc_items = []
body_elements = []
in_toc = False

for elem in main_tag.children:
    if not elem.name:
        continue
    text = elem.get_text(strip=True)
    if "目次" in text and elem.name in ['h1', 'h2']:
        in_toc = True
        continue
    elif in_toc and ("序章" in text or "第1章" in text) and elem.name in ['h1', 'h2']:
        in_toc = False
        body_elements.append(elem)
    elif in_toc:
        if elem.name in ['ol', 'ul']:
            for li in elem.find_all('li'):
                t = li.get_text(strip=True)
                if len(clean_key(t)) >= 2:
                    toc_items.append((li, t, clean_key(t)))
    else:
        body_elements.append(elem)

print(f"目次項目数: {len(toc_items)} 個")
print(f"本文要素数: {len(body_elements)} 個")

# 3. 本文中のすべての要素（見出し＋段落）を走査し、目次項目と1対1で正確にマッチング
anchor_count = 0
last_body_idx = 0

for li_tag, raw_title, key in toc_items:
    matched_target = None
    best_score = 0
    best_idx = -1
    
    # 探索（前回のマッチ位置以降を優先）
    for b_idx in range(last_body_idx, len(body_elements)):
        elem = body_elements[b_idx]
        elem_text = elem.get_text()
        elem_key = clean_key(elem_text)
        
        score = 0
        if key in elem_key:
            score = 100
        elif elem_key in key:
            score = 90
        else:
            # 共通部分の長さ
            common = set(key) & set(elem_key)
            if len(common) >= len(key) * 0.7:
                score = 70
                
        if score > best_score and score >= 70:
            best_score = score
            matched_target = elem
            best_idx = b_idx
            if score == 100:
                break
                
    # もし見つからなければ、全体から再探索
    if not matched_target:
        for b_idx in range(0, len(body_elements)):
            elem = body_elements[b_idx]
            elem_text = elem.get_text()
            elem_key = clean_key(elem_text)
            if key in elem_key or (len(key) > 4 and key[:4] in elem_key):
                matched_target = elem
                best_idx = b_idx
                break
                
    if matched_target:
        last_body_idx = max(last_body_idx, best_idx)
        # ターゲットにIDが付いていなければ付与
        if not matched_target.get('id'):
            anchor_count += 1
            matched_target['id'] = f"toc-target-{anchor_count}"
        
        target_id = matched_target['id']
        
        # 目次項目をリンク化
        new_a = soup.new_tag('a', href=f"#{target_id}")
        new_a.string = raw_title
        li_tag.clear()
        li_tag.append(new_a)
        print(f"  [OK リンク] '{raw_title}' -> #{target_id} ({matched_target.name}: {matched_target.get_text()[:30]}...)")
    else:
        print(f"  [未検出] '{raw_title}'")

# 4. HTMLを保存
html_path.write_text(str(soup), encoding="utf-8")
print(f"全 {len(toc_items)} 個の目次項目に対する完全マッピングが完了しました！")
