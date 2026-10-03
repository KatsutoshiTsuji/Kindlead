import sys
from pathlib import Path
from bs4 import BeautifulSoup

soup = BeautifulSoup(Path(r"C:\Users\tonbo\Desktop\主要登場人物.html").read_text(encoding='utf-8'), 'html.parser')
sys.stdout.reconfigure(encoding='utf-8')

# Look at all headings with their following text
headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
for i, h in enumerate(headings):
    next_p = h.find_next_sibling('p')
    p_preview = next_p.get_text(strip=True)[:60] if next_p else "(no immediate p)"
    print(f"[{i:02d}] <{h.name} id='{h.get('id')}'> {h.get_text(strip=True)}")
    print(f"     Next: {p_preview}")
