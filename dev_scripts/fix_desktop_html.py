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

def clean_and_link_book(file_path):
    html = file_path.read_text(encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')

    # 1. Remove existing nav tags and AI meta comments
    for nav in soup.find_all('nav'):
        nav.decompose()

    for p in soup.find_all('p'):
        t = p.get_text(strip=True)
        if any(k in t for k in ['テキスト情報が含まれていないため', '代替テキスト（Alt Text）を作成しました', '画像の説明：', 'Alt Text']):
            p.decompose()

    # 2. Find TOC header
    toc_h = None
    for h in soup.find_all(['h1', 'h2', 'h3', 'h4']):
        if '目次' in h.get_text():
            toc_h = h
            break

    if not toc_h:
        return

    # 3. Collect TOC raw lines
    curr = toc_h.next_sibling
    toc_nodes = []
    while curr:
        tag = getattr(curr, 'name', None)
        if tag == 'p' and len(curr.get_text(strip=True)) > 80:
            break
        if tag in ['p', 'ul', 'ol', 'div', 'h2', 'h3', 'h4']:
            toc_nodes.append(curr)
        curr = curr.next_sibling

    raw_toc_items = []
    for node in toc_nodes:
        if node.name in ['ul', 'ol']:
            for li in node.find_all('li'):
                t = li.get_text(strip=True)
                if len(clean_key(t)) >= 1 and '代替テキスト' not in t:
                    raw_toc_items.append(t)
        elif node.name == 'p':
            for line in node.get_text().split('\n'):
                line = line.strip().lstrip('-').lstrip('・').lstrip('*').strip()
                if len(clean_key(line)) >= 1 and '代替テキスト' not in line:
                    raw_toc_items.append(line)
        elif node.name in ['h2', 'h3', 'h4']:
            t = node.get_text(strip=True)
            if len(clean_key(t)) >= 1 and '代替テキスト' not in t:
                raw_toc_items.append(t)

    # 4. Assign clean sequential IDs to all body headings (after TOC)
    body_headings = []
    curr = toc_h.next_sibling
    target_id = 1
    while curr:
        if getattr(curr, 'name', None) in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] and curr not in toc_nodes:
            uid = f"section-{target_id}"
            target_id += 1
            curr['id'] = uid
            body_headings.append({
                'id': uid,
                'elem': curr,
                'text': curr.get_text(strip=True),
                'clean': clean_key(curr.get_text(strip=True))
            })
        curr = curr.next_sibling

    # 5. Monotonic ordered matching
    nav_tag = soup.new_tag('nav', **{'aria-label': '目次'})
    ol_tag = soup.new_tag('ol')
    nav_tag.append(ol_tag)

    last_idx = 0
    matched_count = 0
    for raw_t in raw_toc_items:
        c_t = clean_key(raw_t)
        best_h = None
        best_score = 0
        best_i = -1
        
        # Search forward from last_idx to ensure monotonic order
        for i in range(last_idx, len(body_headings)):
            bh = body_headings[i]
            sim = similarity(c_t, bh['clean'])
            if c_t in bh['clean'] or bh['clean'] in c_t:
                sim = max(sim, 0.90)
            if sim > best_score:
                best_score = sim
                best_h = bh
                best_i = i
                if sim >= 0.90:
                    break
                    
        li_tag = soup.new_tag('li')
        if best_h and best_score >= 0.40:
            last_idx = best_i
            matched_count += 1
            a_tag = soup.new_tag('a', href=f"#{best_h['id']}")
            a_tag.string = raw_t
            li_tag.append(a_tag)
            print(f"  LINKED: {raw_t} -> #{best_h['id']} ({best_h['text'][:25]})")
        else:
            li_tag.string = raw_t
            print(f"  UNLINKED: {raw_t}")
        ol_tag.append(li_tag)

    # 6. Replace old TOC nodes
    for node in toc_nodes:
        node.decompose()
    toc_h.insert_after(nav_tag)

    file_path.write_text(str(soup), encoding='utf-8')
    print(f"[{file_path.name}] Total: {len(raw_toc_items)}, Linked: {matched_count}")

# Fix Desktop files
for f in Path(r"C:\Users\tonbo\Desktop").glob("*.html"):
    print(f"\nProcessing {f.name}...")
    clean_and_link_book(f)
