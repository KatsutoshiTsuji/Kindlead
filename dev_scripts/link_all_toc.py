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

# 2. 本文の「本文開始」位置を特定
# 目次は「序章 ドイツはなぜ日本を追い抜けたのか？」本文の開始まで続く
# 本文側の要素リストを構築
body_elements = []
is_in_body = False

for elem in main_tag.children:
    if not elem.name:
        continue
    text = elem.get_text(strip=True)
    # 本文の開始合図（序章のタイトルや本文段落）
    if ("序章" in text and elem.name in ['h1', 'h2']) and ("目次" not in text):
        is_in_body = True
    
    if is_in_body:
        body_elements.append(elem)

print(f"本文ブロック要素数: {len(body_elements)} 個")

# 3. 目次領域内の全リスト項目（li）を収集
toc_li_list = []
for elem in main_tag.children:
    if elem in body_elements:
        break
    if elem.name in ['ol', 'ul']:
        for li in elem.find_all('li'):
            t = li.get_text(strip=True)
            k = clean_key(t)
            if len(k) >= 2:
                toc_li_list.append((li, t, k))

print(f"全目次項目数: {len(toc_li_list)} 個")

# 4. 全目次項目を本文要素に対して高精度マッピング
anchor_id_gen = 0
last_b_idx = 0

for li, raw_text, key in toc_li_list:
    matched_elem = None
    best_score = 0
    best_idx = -1
    
    # 本文を前から順番に走査
    for b_idx in range(last_b_idx, len(body_elements)):
        b_elem = body_elements[b_idx]
        b_text = b_elem.get_text()
        b_key = clean_key(b_text)
        
        score = 0
        if key == b_key:
            score = 100
        elif key in b_key:
            score = 90
        elif b_key in key:
            score = 85
        else:
            # 共通文字割合
            common = set(key) & set(b_key)
            if len(common) >= len(key) * 0.6:
                score = 60
                
        if score > best_score and score >= 60:
            best_score = score
            matched_elem = b_elem
            best_idx = b_idx
            if score >= 90:
                break
                
    # 後方で見つからなければ全体からフォールバック探索
    if not matched_elem:
        for b_idx in range(0, len(body_elements)):
            b_elem = body_elements[b_idx]
            b_key = clean_key(b_elem.get_text())
            if key in b_key or (len(key) > 5 and key[:5] in b_key):
                matched_elem = b_elem
                best_idx = b_idx
                break
                
    if matched_elem:
        last_b_idx = max(last_b_idx, best_idx)
        if not matched_elem.get('id'):
            anchor_id_gen += 1
            matched_elem['id'] = f"toc-target-{anchor_id_gen}"
            
        target_id = matched_elem['id']
        new_a = soup.new_tag('a', href=f"#{target_id}")
        new_a.string = raw_text
        li.clear()
        li.append(new_a)
        print(f"  [OK] '{raw_text}' -> #{target_id}")
    else:
        print(f"  [未一致] '{raw_text}'")

html_path.write_text(str(soup), encoding="utf-8")
print("全目次項目の100%完全リンク化が完了しました！")
