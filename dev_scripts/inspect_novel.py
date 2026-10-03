import sys
from pathlib import Path
from bs4 import BeautifulSoup

soup = BeautifulSoup(Path(r"C:\Users\tonbo\Desktop\主要登場人物.html").read_text(encoding='utf-8'), 'html.parser')
sys.stdout.reconfigure(encoding='utf-8')

print("=== Headings ===")
for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
    print(f"<{h.name} id='{h.get('id')}'>{h.get_text(strip=True)}</{h.name}>")

print("\n=== TOC ===")
nav = soup.find('nav')
if nav:
    for li in nav.find_all('li'):
        links = [a.get('href') for a in li.find_all('a')]
        print(f"  {li.get_text(strip=True)} -> {links}")
else:
    print("No nav tag!")

print("\n=== Summary Stats ===")
print("Total paragraphs:", len(soup.find_all('p')))
print("Total headings:", len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])))
print("Total words/chars:", len(soup.get_text()))
