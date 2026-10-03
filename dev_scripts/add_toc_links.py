from pathlib import Path
import re
from bs4 import BeautifulSoup
import urllib.parse

html_path = Path("D:/Katsutoshi/AntiGravity/Kindlead/output.html")
soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")

# 1. 本文中のすべての見出し (h1, h2, h3, h4) を収集し、IDを付与
headings = []
heading_counter = 0

for h in soup.find_all(['h1', 'h2', 'h3', 'h4']):
    text = h.get_text(strip=True)
    if not text:
        continue
    # 目次自体の見出しはスキップ
    if "目次" in text:
        continue
        
    heading_counter += 1
    anchor_id = f"heading-{heading_counter}"
    h['id'] = anchor_id
    headings.append({
        'id': anchor_id,
        'text': text,
        'tag': h.name
    })

print(f"本文見出し数: {len(headings)} 個にIDを付与しました。")

# 2. 目次領域を探してリンク化
# 「目次」という見出しの後ろにあるリスト（ol, ul）の各項目を本文の見出しと照合
in_toc = False
for elem in soup.find_all(['h1', 'h2', 'h3', 'ol', 'ul']):
    if elem.name in ['h1', 'h2', 'h3']:
        if "目次" in elem.get_text():
            in_toc = True
            continue
        elif in_toc and ("序章" in elem.get_text() or "第1章" in elem.get_text() or "第１章" in elem.get_text()):
            # 本文の開始見出しが来たら目次終了
            # ただし目次内の「第1章」見出しの場合はリストがある
            pass
            
    if in_toc and elem.name in ['ol', 'ul']:
        for li in elem.find_all('li', recursive=False):
            li_text = li.get_text(strip=True)
            # 最適な本文見出しを探す（完全一致または部分一致）
            matched_id = None
            for hd in headings:
                # 目次項目と見出しの類似・一致判定
                clean_li = re.sub(r'^[0-9０-９\.\s\-\—]+', '', li_text).strip()
                clean_hd = re.sub(r'^[0-9０-９\.\s\-\—]+', '', hd['text']).strip()
                if clean_li and clean_hd and (clean_li in clean_hd or clean_hd in clean_li):
                    matched_id = hd['id']
                    break
            
            if matched_id:
                # リンクタグでラップ
                link_tag = soup.new_tag('a', href=f"#{matched_id}")
                link_tag.string = li.get_text()
                li.clear()
                li.append(link_tag)

# 3. 更新したHTMLを保存
html_path.write_text(str(soup), encoding="utf-8")
print("目次リンクの自動付与が完了しました！")
