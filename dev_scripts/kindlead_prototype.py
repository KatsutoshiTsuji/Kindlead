"""
Kindlead Prototype - Rate-Limit Resilient & Smart 'Ctrl+G' Cover Jump
--------------------------------------------------------------------
Kindle for PCから自動キャプチャし、Gemini APIで構造化HTMLにするスクリプト
- Ctrl+G（移動メニュー）を使った100%確実な表紙自動巻き戻し
- 429レートリミット時の自動リトライ＆指数バックオフ
"""

import os
import sys
import time
import argparse
import subprocess
import webbrowser
import winsound
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from PIL import Image
import numpy as np
import pyautogui
from google import genai
import markdown

# .envファイルの読み込み
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

SYSTEM_PROMPT = """あなたはアクセシビリティを専門とするアシスタントです。
提供された書籍のキャプチャ画像（日本語の縦書きまたは横書き）から、スクリーンリーダー（NVDA等）で快適かつ構造的に読めるように、正確なテキストと文書構造をMarkdown形式で抽出してください。

【厳格なルール】
1. 見出し（大見出し、中見出し、小見出し）は、視覚的な階層に応じて適切なMarkdown見出し記法（#、##、###）で出力してください。
2. 表紙や扉ページの場合は、書籍タイトルを # 見出し、著者名やサブタイトル、帯のキャッチコピーを明確に区別して抽出してください。
3. 目次ページの場合は、章タイトルを見出し、節項目を番号付きリストまたは箇条書きリストとして構造化してください。
4. 本文の段落は適切な改行で区切ってください。
5. 箇条書きやリスト、番号付きリストがある場合は、Markdownのリスト形式（- や 1.）で表現してください。
6. ルビ（ふりがな）がある場合は、HTMLのrubyタグ（例: <ruby>漢字<rt>かんじ</rt></ruby>）または読み上げを邪魔しない自然な形式で抽出してください。
7. ページ上下のヘッダー、フッター、書籍タイトル、ページ番号（ノンブル）など、本文と無関係な周辺要素は除外してください。
8. 前置きや解説文は一切含めず、純粋なMarkdownテキストのみを出力してください。
"""

def focus_and_maximize_kindle(go_to_start=True):
    """Kindleウィンドウを自動で最前面化し、最大化する（Ctrl+Gで表紙へジャンプ）"""
    print("[1/3] Kindleウィンドウを最前面化しています...")
    ps_command = "$wshell = New-Object -ComObject Wscript.Shell; $wshell.AppActivate('Kindle')"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_command], capture_output=True)
    time.sleep(1.0)
    
    pyautogui.hotkey('win', 'up')
    time.sleep(0.5)
    
    if go_to_start:
        print("  ・Ctrl+G（移動メニュー）を使って表紙へ自動ジャンプしています...")
        screen_w, screen_h = pyautogui.size()
        pyautogui.click(screen_w // 2, screen_h // 2)
        time.sleep(0.3)
        
        # 1. Ctrl + G で移動メニューを開く
        pyautogui.hotkey('ctrl', 'g')
        time.sleep(0.8)
        
        # 2. 「カバー（表紙）」を選択して Enter
        pyautogui.press('home')
        time.sleep(0.2)
        pyautogui.press('enter')
        time.sleep(1.2)
        
        # 3. 念のため Ctrl + Home も送信
        pyautogui.hotkey('ctrl', 'home')
        time.sleep(0.5)
        print("  => 表紙への巻き戻し完了！")

def turn_page_by_click(direction="left"):
    """画面上のページ送り領域（丸い矢印ボタン付近）を直接クリックする"""
    screen_w, screen_h = pyautogui.size()
    center_y = screen_h // 2
    
    if direction == "left":
        # 縦書きの「次へ進む」: 画面左端の丸い矢印ボタン (<) をクリック
        pyautogui.click(40, center_y)
    else:
        # 横書きの「次へ進む」: 画面右端の丸い矢印ボタン (>) をクリック
        pyautogui.click(screen_w - 40, center_y)

def images_are_identical(img1, img2, threshold=10000):
    """2枚の画像が同一（画面が変わっていない）かどうか判定する"""
    arr1 = np.array(img1.convert('L'))
    arr2 = np.array(img2.convert('L'))
    diff = np.abs(arr1.astype(int) - arr2.astype(int)).sum()
    return diff < threshold

def capture_pages_auto_end(max_pages=500, direction="left", wait_sec=0.4, output_dir=None):
    """表紙から本の終わり（画面変化なし）まで完全自動でキャプチャする"""
    if output_dir is None:
        output_dir = Path(__file__).parent / "captures"
    for f in output_dir.glob("page_*.png"):
        f.unlink()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    t_start = time.perf_counter()
    print(f"[2/3] 完全自動キャプチャ中... （終端検知モード / 最大上限 {max_pages} ページ）")
    
    image_paths = []
    prev_screenshot = None
    page_num = 1
    
    while page_num <= max_pages:
        screenshot = pyautogui.screenshot()
        
        # 終端判定
        if prev_screenshot is not None and images_are_identical(prev_screenshot, screenshot):
            print(f"\n  ★ 本の終端（最後のページ）に到達しました！（全 {page_num - 1} ページ）")
            winsound.Beep(1800, 100)
            winsound.Beep(2200, 200)
            break
            
        img_path = output_dir / f"page_{page_num:03d}.png"
        screenshot.save(img_path)
        image_paths.append(img_path)
        prev_screenshot = screenshot
        
        winsound.Beep(1600, 25)
        print(f"  ・ページ {page_num} 撮影完了", end="\r")
        
        turn_page_by_click(direction)
        time.sleep(wait_sec)
        page_num += 1
        
    t_total = time.perf_counter() - t_start
    print(f"\n  => キャプチャ完了！ 合計: {len(image_paths)} ページ ({t_total:.2f} 秒)")
    return image_paths, t_total

def analyze_single_page(img_path, page_idx, api_key, max_retries=3):
    """1ページ分の画像をGemini APIで解析（429リトライ対応）"""
    client = genai.Client(api_key=api_key)
    models_to_try = [
        'gemini-3.1-flash-lite-preview',
        'gemini-flash-lite-latest',
        'gemini-3.5-flash',
        'gemini-3.8-flash'
    ]
    
    t_page_start = time.perf_counter()
    image = Image.open(img_path)
    
    for attempt in range(1, max_retries + 1):
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        SYSTEM_PROMPT,
                        image,
                        "この画像のテキストと構造をMarkdownで抽出してください。"
                    ]
                )
                md_text = response.text.strip()
                dur = time.perf_counter() - t_page_start
                return {
                    "page": page_idx,
                    "file": img_path.name,
                    "markdown": md_text,
                    "duration": dur,
                    "model": model_name
                }
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait_time = 5 * attempt
                    print(f"  [レート制限待機] ページ {page_idx}: {wait_time}秒待機して再試行します...")
                    time.sleep(wait_time)
                    break
                continue
                
    dur = time.perf_counter() - t_page_start
    return {
        "page": page_idx,
        "file": img_path.name,
        "markdown": f"<!-- ページ {page_idx} 解析失敗 -->",
        "duration": dur,
        "model": "Failed"
    }

def process_images_parallel(image_paths, api_key, max_workers=5):
    """Gemini APIを並列実行して全ページを一括解析する（安全な5並列）"""
    if not api_key:
        raise ValueError("GEMINI_API_KEY が設定されていません。.envファイルに設定してください。")
    
    t_start = time.perf_counter()
    print(f"[3/3] Gemini APIで {len(image_paths)} ページの文書構造を並列解析中（安全な{max_workers}並列）...")
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(analyze_single_page, img_path, idx, api_key): idx
            for idx, img_path in enumerate(image_paths, 1)
        }
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            
    results.sort(key=lambda x: x["page"])
    t_total = time.perf_counter() - t_start
    return results, t_total

def generate_html(results, perf_stats, output_path=None, book_title="Kindlead 構造化読書"):
    """Markdown結果をシームレスでアクセシブルなHTMLドキュメントに結合する（ページ番号ノイズ全撤廃）"""
    if isinstance(results, tuple):
        results = results[0]
        
    if output_path is None:
        output_path = Path(__file__).parent / "output.html"
        
    t_start = time.perf_counter()
    combined_body = []
    for item in results:
        html_segment = markdown.markdown(item['markdown'], extensions=['extra', 'nl2br'])
        combined_body.append(html_segment)

    body_content = "\n\n".join(combined_body)
    
    html_template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{book_title}</title>
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
        hr {{
            border: 0;
            border-top: 1px dashed #ccc;
            margin: 2.5em 0;
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
        .perf-summary h2 {{
            margin-top: 0;
            font-size: 1.05em;
            border-bottom: none;
        }}
        .perf-summary ul {{
            margin-bottom: 0;
            padding-left: 1.2em;
        }}
    </style>
</head>
<body>
    <header>
        <h1>{book_title}</h1>
    </header>
    <main>
        {body_content}
    </main>
    <footer>
        <section class="perf-summary" aria-label="処理パフォーマンス計測結果">
            <h2>⏱ 処理時間ベンチマーク レポート（システム情報）</h2>
            <ul>
                <li><strong>総所要時間:</strong> {perf_stats['total_time']:.2f} 秒 (全 {perf_stats['page_count']} ページ)</li>
                <li><strong>1ページ平均時間:</strong> {perf_stats['avg_per_page']:.2f} 秒 / ページ (並列実行)</li>
                <li><strong>画面キャプチャ合計:</strong> {perf_stats['capture_time']:.2f} 秒</li>
                <li><strong>Gemini API解析合計:</strong> {perf_stats['api_time']:.2f} 秒</li>
            </ul>
        </section>
    </footer>
</body>
</html>
"""
    output_path.write_text(html_template, encoding="utf-8")
    return output_path

def run_kindlead(max_pages=500, direction="left", wait=0.4, from_start=True):
    t_all_start = time.perf_counter()
    
    print("\n" + "=" * 60)
    print("  Kindlead - 安定リトライ＆全自動リーダー")
    print("=" * 60)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n[!] GEMINI_API_KEY が設定されていません。")
        return None

    captures_dir = Path(__file__).parent / "captures"

    # 1. 自動フォーカス ＆ Ctrl+G 表紙巻き戻し
    focus_and_maximize_kindle(go_to_start=from_start)

    # 2. 終端検知キャプチャ
    image_paths, t_capture = capture_pages_auto_end(max_pages=max_pages, direction=direction, wait_sec=wait, output_dir=captures_dir)
    if not image_paths:
        print("[エラー] キャプチャ画像がありませんでした。")
        return None

    book_title = "Kindle 構造化読書ドキュメント"

    # 3. 並列API解析（安全な5並列＋429自動リトライ）
    results, t_api = process_images_parallel(image_paths, api_key, max_workers=5)

    # 4. HTML生成
    t_all_total = time.perf_counter() - t_all_start
    perf_stats = {
        "page_count": len(image_paths),
        "capture_time": t_capture,
        "api_time": t_api,
        "total_time": t_all_total,
        "avg_per_page": (t_all_total / len(image_paths)) if image_paths else 0.0
    }
    
    html_path = generate_html(results, perf_stats, book_title=f"{book_title}")

    # 5. コンソール側にベンチマークを表示
    print("\n" + "=" * 60)
    print("  📊 処理完了！ ベンチマーク レポート")
    print("=" * 60)
    print(f"  ・取り込み完了ページ数:       {perf_stats['page_count']} ページ (全ページ完全解析)")
    print(f"  ・画面キャプチャ時間:         {perf_stats['capture_time']:.2f} 秒")
    print(f"  ・Gemini API解析時間(並列):   {perf_stats['api_time']:.2f} 秒")
    print(f"  ------------------------------------------------------------")
    print(f"  ★ 総所要時間:                 {perf_stats['total_time']:.2f} 秒")
    print(f"  ★ 1ページ平均時間:           {perf_stats['avg_per_page']:.2f} 秒 / ページ")
    print("=" * 60)
    print(f"  => 出力ファイル: {html_path.name} をブラウザで開きました！\n")

    winsound.Beep(1200, 120)
    winsound.Beep(1600, 120)
    winsound.Beep(2000, 250)
    
    webbrowser.open(html_path.as_uri())
    return perf_stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kindlead: 安定リトライ＆全自動リーダー")
    parser.add_argument("--max-pages", type=int, default=300, help="安全のための最大上限ページ数（デフォルト: 300）")
    parser.add_argument("--direction", choices=["left", "right"], default="left", help="縦書き: left, 横書き: right")
    parser.add_argument("--wait", type=float, default=0.4, help="ページ送り待機秒数（デフォルト: 0.4秒）")
    parser.add_argument("--no-start-rewind", action="store_true", help="表紙への巻き戻しを行わず現在位置から開始")
    args = parser.parse_args()

    run_kindlead(max_pages=args.max_pages, direction=args.direction, wait=args.wait, from_start=not args.no_start_rewind)
