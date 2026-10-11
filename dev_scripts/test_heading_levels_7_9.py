"""
Test script for Kindlead heading level 7-9 compilation
"""
import sys
from pathlib import Path
from bs4 import BeautifulSoup

# アドオンのengineモジュールをインポート
sys.path.insert(0, str(Path("addon_src/globalPlugins/kindlead").resolve()))
from engine import compile_accessible_html

# テスト用の疑似解析結果
sample_results = [
    {
        "page": 1,
        "markdown": "# 素晴らしいアクセシビリティの世界\n\n著者: 辻勝利\n\n## 第1章 NVDAと読書革新\n\nスクリーンリーダーでの読書体験は年々進化しています※1。\n特に見出しジャンプ機能は極めて重要です[2]。\n\n<aside role=\"region\" aria-label=\"コラム\" class=\"kindlead-column\">\n  <div role=\"heading\" aria-level=\"7\" class=\"column-title\">コラム：見出しジャンプの歴史</div>\n  NVDAでは古くからHキーによる見出しジャンプがサポートされていましたが、近年は1〜9の数字キーによるレベル別単打ジャンプが利用可能になりました。\n</aside>\n\n本文の続きです。ここにも図表の解説が入ります。\n\n<figure class=\"kindlead-figure\">\n  <figcaption role=\"heading\" aria-level=\"9\" class=\"figure-caption\">図1-1 読書効率の向上グラフ</figcaption>\n  従来の全文読み上げと比較して、見出しナビゲーションを用いた場合の読書速度が3倍に向上したことを示すグラフ。\n</figure>\n\n※1 NVDA日本語版の普及により、日本国内の視覚障害者の情報アクセス環境は劇的に改善された。\n[2] スクリーンリーダーの単打ナビゲーションキー（Quick Navigation）のこと。"
    }
]

out_file, title = compile_accessible_html(
    sample_results,
    image_count=1,
    t_cap=0.5,
    t_api=1.2,
    output_dir=Path("dev_scripts/test_output")
)

print(f"Generated HTML: {out_file}")
print(f"Detected Title: {title}")

# HTMLの検証
content = out_file.read_text(encoding="utf-8")
soup = BeautifulSoup(content, "html.parser")

# 1. コラム (level 7)
h7 = soup.find_all(lambda el: el.get('role') == 'heading' and el.get('aria-level') == '7')
print(f"Heading Level 7 count: {len(h7)}")
for el in h7:
    print(f"  Level 7: {el.get_text(strip=True)}")

# 2. 注釈 (level 8)
h8 = soup.find_all(lambda el: el.get('role') == 'heading' and el.get('aria-level') == '8')
print(f"Heading Level 8 count: {len(h8)}")
for el in h8:
    print(f"  Level 8: {el.get_text(strip=True)}")

# 双方向リンクの確認
fn_refs = soup.find_all(class_='footnote-ref')
print(f"Footnote references in text: {len(fn_refs)}")
for r in fn_refs:
    print(f"  Ref: {r.get_text()} -> {r.get('href')}")

backrefs = soup.find_all(class_='footnote-backref')
print(f"Footnote backrefs: {len(backrefs)}")
for b in backrefs:
    print(f"  Backref -> {b.get('href')}")

# 3. 図表 (level 9)
h9 = soup.find_all(lambda el: el.get('role') == 'heading' and el.get('aria-level') == '9')
print(f"Heading Level 9 count: {len(h9)}")
for el in h9:
    print(f"  Level 9: {el.get_text(strip=True)}")

assert len(h7) >= 1, "Level 7 heading not found!"
assert len(h8) >= 2, "Level 8 headings not found!"
assert len(h9) >= 1, "Level 9 heading not found!"
assert len(fn_refs) >= 1, "Footnote refs not found!"
assert len(backrefs) >= 2, "Backrefs not found!"
print("\nALL ASSERTIONS PASSED! Level 7, 8, 9 structures and bidirectional links verified.")
