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

def process_toc_links_universal(soup):
    toc_h = None
    for h in soup.find_all(['h1', 'h2', 'h3', 'h4']):
        if '目次' in h.get_text():
            toc_h = h
            break
            
    if not toc_h:
        return 0, 0

    # 1. Collect TOC container nodes between toc_h and the first long paragraph (>70 chars)
    curr = toc_h.next_sibling
    toc_nodes = []
    while curr:
        tag = getattr(curr, 'name', None)
        if tag == 'p' and len(curr.get_text(strip=True)) > 70:
            break
        if tag in ['p', 'ul', 'ol', 'div', 'h2', 'h3', 'h4']:
            toc_nodes.append(curr)
        curr = curr.next_sibling

    # 2. Extract all raw TOC items
    raw_toc_items = []
    for node in toc_nodes:
        if node.name in ['ul', 'ol']:
            for li in node.find_all('li'):
                t = li.get_text(strip=True)
                if len(clean_key(t)) >= 1:
                    raw_toc_items.append(t)
        elif node.name == 'p':
            for line in node.get_text().split('\n'):
                line = line.strip().lstrip('-').lstrip('・').lstrip('*').strip()
                if len(clean_key(line)) >= 1:
                    raw_toc_items.append(line)
        elif node.name in ['h2', 'h3', 'h4']:
            t = node.get_text(strip=True)
            if len(clean_key(t)) >= 1:
                raw_toc_items.append(t)

    if not raw_toc_items:
        return 0, 0

    # 3. Assign IDs to all headings and body paragraphs NOT in toc_nodes
    all_headings = []
    all_paras = []
    elem_counter = 1
    
    for el in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        if el == toc_h or el in toc_nodes:
            continue
        uid = f"heading-{elem_counter}"
        elem_counter += 1
        el['id'] = uid
        all_headings.append({'id': uid, 'text': el.get_text(strip=True), 'clean': clean_key(el.get_text(strip=True))})

    for el in soup.find_all('p'):
        if el in toc_nodes:
            continue
        t = el.get_text(strip=True)
        if len(t) > 5:
            uid = f"para-{elem_counter}"
            elem_counter += 1
            el['id'] = uid
            all_paras.append({'id': uid, 'text': t, 'clean': clean_key(t)})

    # 4. Construct semantic <nav aria-label="目次"><ol>...</ol></nav>
    nav_tag = soup.new_tag('nav', **{'aria-label': '目次'})
    ol_tag = soup.new_tag('ol')
    nav_tag.append(ol_tag)

    matched_count = 0
    for raw_t in raw_toc_items:
        c_t = clean_key(raw_t)
        if not c_t:
            continue
            
        best_target = None
        best_score = 0

        # Match against headings first
        for h in all_headings:
            sim = similarity(c_t, h['clean'])
            if c_t in h['clean'] or h['clean'] in c_t:
                sim = max(sim, 0.90)
            if sim > best_score:
                best_score = sim
                best_target = h
                if sim >= 0.90:
                    break

        # If still no heading match, match against paragraphs
        if best_score < 0.45:
            for p in all_paras:
                sim = similarity(c_t, p['clean'][:len(c_t) + 15])
                if c_t in p['clean'][:len(c_t) + 15]:
                    sim = max(sim, 0.85)
                if sim > best_score:
                    best_score = sim
                    best_target = p
                    if sim >= 0.85:
                        break

        li_tag = soup.new_tag('li')
        if best_target and best_score >= 0.40:
            matched_count += 1
            a_tag = soup.new_tag('a', href=f"#{best_target['id']}")
            a_tag.string = raw_t
            li_tag.append(a_tag)
        else:
            li_tag.string = raw_t
        ol_tag.append(li_tag)

    # Replace old toc nodes with new nav_tag
    for node in toc_nodes:
        node.decompose()
    toc_h.insert_after(nav_tag)
    
    return len(raw_toc_items), matched_count

# Run test on all html files in Downloads
downloads = Path(r"C:\Users\tonbo\Downloads")
for f in sorted(list(downloads.glob("*.html")), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
    html_text = f.read_text(encoding='utf-8')
    if "目次" in html_text:
        s = BeautifulSoup(html_text, 'html.parser')
        total, matched = process_toc_links_universal(s)
        print(f"File: {f.name} -> Total TOC: {total}, Matched & Linked: {matched}")
        if total > 0:
            f.write_text(str(s), encoding='utf-8')
