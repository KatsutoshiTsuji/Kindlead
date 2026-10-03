from bs4 import BeautifulSoup
import re, unicodedata
from difflib import SequenceMatcher

def clean_key(s):
    if not s: return ''
    s = unicodedata.normalize('NFKC', str(s))
    s = re.sub(r'[0-9０-９\.\s\-\—\―\:\：\(\)\（\）\「\」\『\』\【\】\・\…\、\。]', '', s)
    return s.lower()

def similarity(a, b):
    return SequenceMatcher(None, clean_key(a), clean_key(b)).ratio()

html = open(r'C:\Users\tonbo\Downloads\誰のためのアクセシビリティ_.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')

toc_h = None
for h in soup.find_all(['h1', 'h2', 'h3']):
    if '目次' in h.get_text():
        toc_h = h
        break

# Extract TOC items
curr = toc_h.next_sibling
toc_nodes = []
seen_body = False
while curr:
    if getattr(curr, 'name', None) in ['h1', 'h2', 'h3', 'h4']:
        seen_body = True
    if not seen_body:
        if getattr(curr, 'name', None) in ['p', 'ul', 'ol', 'div']:
            toc_nodes.append(curr)
    curr = curr.next_sibling

raw_toc_items = []
for node in toc_nodes:
    if node.name in ['ul', 'ol']:
        for li in node.find_all('li'):
            t = li.get_text(strip=True)
            if len(clean_key(t)) >= 1:
                raw_toc_items.append(t)
    elif node.name == 'p':
        for line in node.get_text().split('\n'):
            line = line.strip().lstrip('-').lstrip('・').strip()
            if len(clean_key(line)) >= 1:
                raw_toc_items.append(line)

# Gather all headings AFTER TOC
body_headings = []
curr = toc_h.next_sibling
target_id = 1
while curr:
    if getattr(curr, 'name', None) in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        uid = f'heading-{target_id}'
        target_id += 1
        curr['id'] = uid
        body_headings.append({'elem': curr, 'id': uid, 'text': curr.get_text(strip=True), 'clean': clean_key(curr.get_text(strip=True))})
    curr = curr.next_sibling

print(f'Total TOC items: {len(raw_toc_items)}')
print(f'Total Body Headings: {len(body_headings)}')

matched = 0
for raw_t in raw_toc_items:
    c_t = clean_key(raw_t)
    best_h = None
    best_score = 0
    for bh in body_headings:
        sim = similarity(c_t, bh['clean'])
        if c_t in bh['clean'] or bh['clean'] in c_t:
            sim = max(sim, 0.85)
        if sim > best_score:
            best_score = sim
            best_h = bh
    if best_h and best_score >= 0.4:
        matched += 1
        matched_text = best_h["text"]
        print(f"MATCH ({best_score:.2f}): {raw_t} ---> {matched_text}")
    else:
        print(f"NO MATCH: {raw_t}")

print(f"Result: {matched} / {len(raw_toc_items)} matched!")
