from pathlib import Path
import re

html_path = Path("D:/Katsutoshi/AntiGravity/Kindlead/output.html")
raw = html_path.read_text(encoding="utf-8")

sections = re.findall(r'<section class="book-page"[^>]*>(.*?)</section>', raw, re.DOTALL)
cleaned_segments = []
for s in sections:
    s_clean = re.sub(r'<hr[^>]*>', '', s)
    s_clean = re.sub(r'<!--.*?-->', '', s_clean)
    s_clean = s_clean.strip()
    if s_clean:
        cleaned_segments.append(s_clean)

body_content = "\n\n".join(cleaned_segments)

html_template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>高く売れるものだけ作るドイツ人、いいものを安く売ってしまう日本人</title>
    <style>
        :root {{
            --bg-color: #ffffff;
            --text-color: #1a1a1a;
            --heading-color: #0b3c5d;
            --border-color: #e0e0e0;
            --accent-bg: #f4f6f8;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Hiragino Kaku Gothic ProN", "Yu Gothic", Meiryo, sans-serif;
            line-height: 1.85;
            max-width: 820px;
            margin: 30px auto;
            padding: 0 24px;
            color: var(--text-color);
            background-color: var(--bg-color);
        }}
        h1, h2, h3, h4 {{
            color: var(--heading-color);
            margin-top: 1.8em;
            margin-bottom: 0.6em;
            line-height: 1.4;
        }}
        h1 {{ font-size: 1.8em; border-bottom: 2px solid var(--heading-color); padding-bottom: 0.3em; }}
        h2 {{ font-size: 1.4em; border-bottom: 1px solid var(--border-color); padding-bottom: 0.2em; }}
        h3 {{ font-size: 1.2em; }}
        p {{
            margin-bottom: 1.2em;
            text-indent: 1em;
        }}
        ul, ol {{
            margin-bottom: 1.2em;
            padding-left: 1.8em;
        }}
        li {{
            margin-bottom: 0.4em;
        }}
        ruby {{
            font-size: 1.0em;
        }}
        rt {{
            font-size: 0.65em;
            color: #555;
        }}
        footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #ccc;
        }}
        .perf-summary {{
            background: var(--accent-bg);
            border-left: 4px solid var(--heading-color);
            padding: 16px 20px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <header>
        <h1>高く売れるものだけ作るドイツ人、いいものを安く売ってしまう日本人</h1>
    </header>
    <main>
        {body_content}
    </main>
    <footer>
        <section class="perf-summary" aria-label="処理パフォーマンス計測結果">
            <h2>⏱ 処理時間ベンチマーク レポート（システム情報）</h2>
            <p>全 98 ページ完走 / 総所要時間: 333 秒</p>
        </section>
    </footer>
</body>
</html>"""

html_path.write_text(html_template, encoding="utf-8")
print("Seamless HTML updated successfully!")
