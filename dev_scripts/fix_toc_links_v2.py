from pathlib import Path
import re
from bs4 import BeautifulSoup
import unicodedata

def normalize_text(text):
    """テキストを正規化して比較しやすくする"""
    text = unicodedata.normalize('NFKC', text)
    # 記号や空白、章番号のプレフィックスを除去
    text = re.sub(r'[0-9０-９\.\s\-\—\―\:\：\(\)\（\）\「\」\『\』]', '', text)
    return text.lower()

html_path = Path("D:/Katsutoshi/AntiGravity/Kindlead/output.html")
soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")

book_title = "高く売れるものだけ作るドイツ人、いいものを安く売ってしまう日本人"
norm_book_title = normalize_text(book_title)

# 1. 本文中に重複して現れる書籍タイトル (h1) をクリーンアップ（ドキュメント冒頭のheader以外は削除）
for h1 in soup.find_all('h1'):
    if h1.parent and h1.parent.name == 'header':
        continue
    # 目次見出し以外の書籍タイトルh1は削除
    h1_norm = normalize_text(h1.get_text())
    if "目次" not in h1.get_text() and (norm_book_title in h1_norm or h1_norm in norm_book_title):
        h1.decompose() # ノイズとなる重複タイトルを完全削除！

# 2. 本文の見出し (h1, h2, h3, h4) に正確な一意IDを付与
headings = []
for idx, h in enumerate(soup.find_all(['h1', 'h2', 'h3', 'h4']), 1):
    text = h.get_text(strip=True)
    if not text:
        continue
    if "目次" in text:
        continue
    anchor_id = f"section-{idx}"
    h['id'] = anchor_id
    headings.append({
        'id': anchor_id,
        'text': text,
        'norm': normalize_text(text),
        'element': h
    })

print(f"ユニークな本文見出し: {len(headings)} 個にIDを割り当てました。")

# 3. 目次領域のリンクを正確に1対1でマッピング
# 目次項目の順番に沿って、本文の見出しを前から順番に高精度マッチング
last_matched_idx = -1

for elem in soup.find_all(['ol', 'ul']):
    # 目次っぽいリストのみ対象
    for li in elem.find_all('li'):
        # 既存のaタグがあればテキストを取り出す
        li_text = li.get_text(strip=True)
        norm_li = normalize_text(li_text)
        if len(norm_li) < 2:
            continue
            
        best_match = None
        best_score = 0
        best_idx = -1
        
        # 本文見出しを探索（前回のマッチ位置以降を優先）
        for h_idx, hd in enumerate(headings):
            norm_hd = hd['norm']
            if not norm_hd:
                continue
                
            # スコアリング
            score = 0
            if norm_li == norm_hd:
                score = 100
            elif norm_li in norm_hd or norm_hd in norm_li:
                # 共通の長さの割合
                common_len = min(len(norm_li), len(norm_hd))
                score = (common_len / max(len(norm_li), len(norm_hd))) * 80
                
            # 順序の整合性ボーナス
            if h_idx >= last_matched_idx:
                score += 10
                
            if score > best_score and score > 45:
                best_score = score
                best_match = hd
                best_idx = h_idx
                
        if best_match:
            last_matched_idx = best_idx
            # リンクタグを設定
            link_tag = soup.new_tag('a', href=f"#{best_match['id']}")
            link_tag.string = li_text
            li.clear()
            li.append(link_tag)

# 4. 保存
html_path.write_text(str(soup), encoding="utf-8")
print("高精度な目次リンクとシームレス化の修正が完了しました！")
