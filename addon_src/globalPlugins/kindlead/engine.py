"""
Kindlead Engine - Standalone Worker
------------------------------------
NVDAアドオンやCLIから呼び出されるKindleadの実行エンジン
"""

import os
import sys

# Windows環境での標準入出力UTF-8化
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import time
import json
import re
import argparse
import subprocess
import webbrowser
import winsound
import unicodedata
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from dotenv import load_dotenv
from PIL import Image
import numpy as np
import pyautogui
from google import genai
from bs4 import BeautifulSoup
import markdown

SYSTEM_PROMPT = """あなたはアクセシビリティを専門とするアシスタントです。
提供された書籍のキャプチャ画像（日本語の縦書きまたは横書き）から、スクリーンリーダー（NVDA等）で快適かつ構造的に読めるように、正確なテキストと高度な文書構造（見出しレベル1〜9）をMarkdown/HTMLで抽出してください。

【厳格なルール】
1. 見出し（大見出し、中見出し、小見出し）は、視覚的な階層に応じて適切なMarkdown見出し記法（#、##、###）で出力してください。書籍の部・章・節は # 〜 ###、小見出しは #### 〜 ##### を使用してください。
2. 表紙や扉ページの場合は、書籍タイトルを # 見出し、著者名やサブタイトル、帯のキャッチコピーを明確に区別して抽出してください。
3. 登場人物紹介ページ（「主要登場人物」等）は書籍タイトルではありません。見出しは ## 登場人物 などとし、本文の紹介文を正確に抽出してください。
4. 扉絵や章の開始ページにある装飾的な幾何学図形や背景イラストに関する視覚要素の解説（「画面構成」「三角形の図形」「イラストの説明」など）は不要です。章タイトル（# 序章、## 風の話 など）や本文のテキストのみを抽出してください。
5. 目次ページの場合は、章タイトルを見出し、節項目を番号付きリストまたは箇条書きリストとして構造化してください。
6. 本文の段落は適切な改行で区切ってください。小説などの会話文や地の文はそれぞれ独立した段落として自然に読めるようにしてください。
7. 【見出しレベル7：コラム・囲み記事・トピックス】
   本文とは独立した囲み記事、コラム、Tips等がある場合は、以下のようにマークアップしてください。
   <aside role="region" aria-label="コラム" class="kindlead-column">
     <div role="heading" aria-level="7" class="column-title">コラムの見出し</div>
     コラムの本文...
   </aside>
8. 【見出しレベル8：注釈・脚注・割注】
   ページ下部や章末の注釈・脚注（※1、注1、[1] など）は、本文と混ざらないよう以下のようにマークアップしてください。
   <div class="kindlead-footnote" id="fn-1">
     <div role="heading" aria-level="8" class="footnote-heading">注1.</div>
     注釈の本文...
   </div>
   本文中の対応する参照箇所には <a href="#fn-1" id="fnref-1" class="footnote-ref">※1</a> のようにリンクを記載してください。
9. 【見出しレベル9：図表キャプション・グラフ解説】
   図、表、グラフ、挿絵の解説やキャプションがある場合は、以下のようにマークアップしてください。
   <figure class="kindlead-figure">
     <figcaption role="heading" aria-level="9" class="figure-caption">図1-1 〇〇の概要</figcaption>
     図表の解説テキスト...
   </figure>
10. 箇条書きやリスト、番号付きリストがある場合は、Markdownのリスト形式（- や 1.）で表現してください。
11. ルビ（ふりがな）がある場合は、HTMLのrubyタグ（例: <ruby>漢字<rt>かんじ</rt></ruby>）または読み上げを邪魔しない自然な形式で抽出してください。
12. ページ上下のヘッダー、フッター、書籍タイトル、ページ番号（ノンブル）など、本文と無関係な周辺要素は除外してください。
13. 前置きや解説文（「テキスト情報が含まれていないため」等のメタ説明）は一切含めず、純粋な抽出結果のみを出力してください。
"""

def clean_key(s):
    if not s:
        return ""
    s = unicodedata.normalize('NFKC', str(s))
    s = re.sub(r'[0-9０-９\.\s\-\—\―\:\：\(\)\（\）\「\」\『\』\【\】\・\…\、\。]', '', s)
    return s.lower()

def normalize_text(text):
    if not text:
        return ""
    return unicodedata.normalize('NFKC', str(text)).strip()

def similarity(a, b):
    return SequenceMatcher(None, clean_key(a), clean_key(b)).ratio()

def focus_and_maximize_kindle():
    """Kindleウィンドウを最前面化して最大化する"""
    ps_cmd = "$wshell = New-Object -ComObject Wscript.Shell; $wshell.AppActivate('Kindle')"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    time.sleep(1.0)
    pyautogui.hotkey('win', 'up')
    time.sleep(0.5)

def go_to_first_page():
    """Kindleのショートカット（Ctrl+G）を使用して書籍の先頭（表紙/位置No.1）に自動移動する"""
    import pyperclip
    pyautogui.press('escape')
    time.sleep(0.3)
    pyautogui.hotkey('ctrl', 'g')
    time.sleep(0.5)
    
    # 日本語IMEの未確定状態を回避するため、クリップボード経由で貼り付け
    pyperclip.copy("1")
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.3)
    pyautogui.press('enter')
    time.sleep(0.3)
    pyautogui.press('enter')
    time.sleep(1.2)
    pyautogui.press('escape')
    time.sleep(0.3)

def capture_pages_auto(max_pages=300, direction="auto", wait_sec=0.4, output_dir=None):
    if output_dir is None:
        output_dir = Path(os.getenv("TEMP")) / "kindlead_captures"
    output_dir.mkdir(parents=True, exist_ok=True)
    for f in output_dir.glob("page_*.png"):
        try:
            f.unlink()
        except Exception:
            pass
        
    t_start = time.perf_counter()
    image_paths = []
    screen_w, screen_h = pyautogui.size()
    center_y = screen_h // 2
    left_x = 40
    right_x = screen_w - 40

    # 1. 最初のページ（表紙/1ページ目）をキャプチャ
    first_screenshot = pyautogui.screenshot()
    img1_path = output_dir / "page_001.png"
    first_screenshot.save(img1_path)
    image_paths.append(img1_path)
    prev_screenshot = first_screenshot
    print(json.dumps({"event": "page", "page": 1}), flush=True)

    chosen_direction = direction
    if direction == "auto":
        # 縦書き（左クリック）をまず試す
        try: winsound.Beep(440, 60)
        except Exception: pass
        pyautogui.click(left_x, center_y)
        time.sleep(wait_sec)
        test_screenshot = pyautogui.screenshot()
        
        arr1 = np.array(first_screenshot.convert('L'))
        arr2 = np.array(test_screenshot.convert('L'))
        diff_left = np.abs(arr1.astype(int) - arr2.astype(int)).sum()
        
        if diff_left >= 10000:
            chosen_direction = "left"
            img2_path = output_dir / "page_002.png"
            test_screenshot.save(img2_path)
            image_paths.append(img2_path)
            prev_screenshot = test_screenshot
            print(json.dumps({"event": "page", "page": 2}), flush=True)
        else:
            try: winsound.Beep(440, 60)
            except Exception: pass
            pyautogui.click(right_x, center_y)
            time.sleep(wait_sec)
            test_screenshot2 = pyautogui.screenshot()
            arr3 = np.array(test_screenshot2.convert('L'))
            diff_right = np.abs(arr1.astype(int) - arr3.astype(int)).sum()
            
            if diff_right >= 10000:
                chosen_direction = "right"
                img2_path = output_dir / "page_002.png"
                test_screenshot2.save(img2_path)
                image_paths.append(img2_path)
                prev_screenshot = test_screenshot2
                print(json.dumps({"event": "page", "page": 2}), flush=True)
            else:
                chosen_direction = "left"

    click_x = left_x if chosen_direction == "left" else right_x
    start_page = len(image_paths) + 1

    for page_num in range(start_page, max_pages + 1):
        try: winsound.Beep(440, 60)
        except Exception: pass
        pyautogui.click(click_x, center_y)
        time.sleep(wait_sec)
        
        screenshot = pyautogui.screenshot()
        if prev_screenshot is not None:
            arr1 = np.array(prev_screenshot.convert('L'))
            arr2 = np.array(screenshot.convert('L'))
            diff = np.abs(arr1.astype(int) - arr2.astype(int)).sum()
            if diff < 10000:
                print(json.dumps({"event": "end_of_book"}), flush=True)
                try:
                    winsound.Beep(440, 70)
                    winsound.Beep(554, 70)
                    winsound.Beep(659, 100)
                except Exception: pass
                break
                
        img_path = output_dir / f"page_{page_num:03d}.png"
        screenshot.save(img_path)
        image_paths.append(img_path)
        prev_screenshot = screenshot
        print(json.dumps({"event": "page", "page": page_num}), flush=True)

    t_total = time.perf_counter() - t_start
    return image_paths, t_total, chosen_direction

def process_images_parallel(image_paths, api_key, max_workers=5):
    client = genai.Client(api_key=api_key)
    models_to_try = [
        'gemini-2.5-flash-lite',
        'gemini-3.1-flash-lite-preview',
        'gemini-flash-lite-latest',
        'gemini-3.8-flash',
        'gemini-2.5-flash'
    ]
    
    def _analyze_page(img_p, p_idx):
        img = Image.open(img_p)
        for attempt in range(1, 4):
            for m_name in models_to_try:
                try:
                    resp = client.models.generate_content(
                        model=m_name,
                        contents=[SYSTEM_PROMPT, img, "テキストと構造をMarkdownで抽出してください。"]
                    )
                    return {"page": p_idx, "markdown": resp.text.strip()}
                except Exception as err:
                    if "429" in str(err) or "RESOURCE_EXHAUSTED" in str(err):
                        continue
                    continue
            time.sleep(2 * attempt)
        return {"page": p_idx, "markdown": ""}

    t_start = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_analyze_page, p, i): i for i, p in enumerate(image_paths, 1)}
        for f in as_completed(futures):
            res = f.result()
            if res["markdown"]:
                results.append(res)
            print(json.dumps({"event": "analyzed", "page": res["page"]}), flush=True)
            try: winsound.Beep(440, 50)
            except Exception: pass
                
    results.sort(key=lambda x: x["page"])
    t_total = time.perf_counter() - t_start
    return results, t_total

def compile_accessible_html(results, image_count, t_cap, t_api, output_dir=None):
    combined_md = [markdown.markdown(r['markdown'], extensions=['extra', 'nl2br']) for r in results]
    raw_body = "\n\n".join(combined_md)
    soup = BeautifulSoup(raw_body, "html.parser")
    
    # 0. AIメタコメントの除外
    for el in soup.find_all(['p', 'div', 'blockquote', 'li']):
        t = el.get_text(strip=True)
        if any(k in t for k in [
            'テキスト情報が含まれていないため', '代替テキスト（Alt Text）を作成しました',
            '画像の説明：', 'Alt Text', '画面構成', '視覚要素', '配置された大きな三角形'
        ]):
            el.decompose()

    # 1. 書籍タイトルの特定
    generic_titles = [
        "電子書籍", "構造化ドキュメント", "目次", "主要登場人物", "登場人物", "人物紹介",
        "キャラクター", "はじめに", "おわりに", "まえがき", "あとがき", "序章", "プロローグ",
        "注意事項", "凡例", "カバー", "表紙", "奥付", "著者紹介", "参考文献", "タイトル"
    ]
    detected_title = "電子書籍 構造化ドキュメント"
    for h1 in soup.find_all('h1'):
        candidate = normalize_text(h1.get_text())
        if candidate and not any(g in candidate for g in generic_titles) and len(candidate) > 1:
            detected_title = candidate
            break

    if detected_title == "電子書籍 構造化ドキュメント":
        for h in soup.find_all(['h2', 'h3'])[:15]:
            candidate = normalize_text(h.get_text())
            if candidate and not any(g in candidate for g in generic_titles) and len(candidate) > 1:
                if not re.match(r'^(第[0-9０-９一二三四五六七八九十]+章|[0-9０-９]+[\s\.\　])', candidate):
                    detected_title = candidate
                    break

    # 主要登場人物などのH1は見出し階層としてH2に降格
    for h1 in soup.find_all('h1'):
        t = normalize_text(h1.get_text())
        if any(g in t for g in ["主要登場人物", "登場人物", "人物紹介", "キャラクター", "はじめに", "序章"]):
            h1.name = 'h2'

    # 重複タイトルの整理
    norm_title = clean_key(detected_title)
    for h in soup.find_all('h1'):
        h_norm = clean_key(h.get_text())
        if "目次" not in h.get_text() and (norm_title in h_norm or h_norm in norm_title):
            h.decompose()

    # 2. 見出し階層の正規化 (H2: 章/目次/謝辞/あとがき, H3: 節/項目)
    for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        t = normalize_text(h.get_text())
        if any(k in t for k in ["目次", "序章", "終章", "謝辞", "著者紹介", "奥付", "著作権", "はじめに", "おわりに", "あとがき", "参考文献"]) or re.match(r'^第[0-9０-９一二三四五六七八九十]+章', t):
            h.name = 'h2'
        elif re.match(r'^[0-9０-９一二三四五六七八九十]+[\s\.\　]', t):
            h.name = 'h3'
        elif re.match(r'^図表|^凡例|^\([0-9]+\)|^（[0-9]+）', t):
            h.name = 'h4'
        elif h.name in ['h1', 'h2']:
            h.name = 'h3'

    # 3. 目次の検出と全文書ターゲットへの1対1アンカーリンク生成
    toc_h = None
    for h in soup.find_all(['h1', 'h2', 'h3', 'h4']):
        if "目次" in h.get_text():
            toc_h = h
            break

    if toc_h:
        # 目次ノード群の収集
        curr = toc_h.next_sibling
        toc_nodes = []
        while curr:
            tag = getattr(curr, 'name', None)
            if tag == 'p' and len(curr.get_text(strip=True)) > 80:
                break
            if tag in ['p', 'ul', 'ol', 'div', 'h2', 'h3', 'h4']:
                toc_nodes.append(curr)
            curr = curr.next_sibling

        # 目次項目の抽出
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

        if raw_toc_items:
            # 本文要素（目次領域以外）への一意なID付与とインデックス化
            all_headings = []
            target_id = 1

            for el in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                if el == toc_h or el in toc_nodes:
                    continue
                uid = f"section-{target_id}"
                target_id += 1
                el['id'] = uid
                all_headings.append({
                    'id': uid,
                    'elem': el,
                    'text': el.get_text(strip=True),
                    'clean': clean_key(el.get_text(strip=True))
                })

            # セマンティックな目次構造 <nav aria-label="目次"><ol>...</ol></nav> の構築
            nav_tag = soup.new_tag('nav', **{'aria-label': '目次'})
            ol_tag = soup.new_tag('ol')
            nav_tag.append(ol_tag)

            last_idx = 0
            for raw_t in raw_toc_items:
                c_t = clean_key(raw_t)
                if not c_t:
                    continue

                best_h = None
                best_score = 0
                best_i = -1

                # 順方向マッチング（単調増加）
                for i in range(last_idx, len(all_headings)):
                    h = all_headings[i]
                    sim = similarity(c_t, h['clean'])
                    if c_t in h['clean'] or h['clean'] in c_t:
                        sim = max(sim, 0.90)
                    if sim > best_score:
                        best_score = sim
                        best_h = h
                        best_i = i
                        if sim >= 0.90:
                            break

                # 見つからない場合は全体から再探索
                if best_score < 0.40:
                    for i, h in enumerate(all_headings):
                        sim = similarity(c_t, h['clean'])
                        if c_t in h['clean'] or h['clean'] in c_t:
                            sim = max(sim, 0.90)
                        if sim > best_score:
                            best_score = sim
                            best_h = h
                            best_i = i
                            if sim >= 0.90:
                                break

                li_tag = soup.new_tag('li')
                if best_h and best_score >= 0.35:
                    if best_i >= last_idx:
                        last_idx = best_i
                    a_tag = soup.new_tag('a', href=f"#{best_h['id']}")
                    a_tag.string = raw_t
                    li_tag.append(a_tag)
                else:
                    li_tag.string = raw_t
                ol_tag.append(li_tag)

            # 古い目次ノードを削除し、構造化されたnav_tagを配置
            for node in toc_nodes:
                node.decompose()
            toc_h.insert_after(nav_tag)

    # 4. 見出しレベル7〜9のセマンティック構造化 ＆ 注釈双方向リンク自動結線
    # 4-1. コラム・囲み記事（見出しレベル7）の正規化
    for aside in soup.find_all(['aside', 'div']):
        if aside.get('class') and 'kindlead-column' in aside.get('class') or aside.get('aria-label') == 'コラム':
            aside['role'] = 'region'
            aside['aria-label'] = 'コラム'
            if 'kindlead-column' not in aside.get('class', []):
                aside['class'] = aside.get('class', []) + ['kindlead-column']
            title_el = aside.find(lambda el: el.get('role') == 'heading' or 'column-title' in el.get('class', []))
            if title_el:
                title_el['role'] = 'heading'
                title_el['aria-level'] = '7'
                if 'column-title' not in title_el.get('class', []):
                    title_el['class'] = title_el.get('class', []) + ['column-title']

    # 4-2. 図表キャプション（見出しレベル9）の正規化
    for fig in soup.find_all(['figure', 'div']):
        if (fig.name == 'figure') or (fig.get('class') and 'kindlead-figure' in fig.get('class')):
            cap = fig.find(['figcaption', 'div', 'p'])
            if cap:
                cap['role'] = 'heading'
                cap['aria-level'] = '9'
                if 'figure-caption' not in cap.get('class', []):
                    cap['class'] = cap.get('class', []) + ['figure-caption']

    # 4-3. 注釈・脚注（見出しレベル8）の検出と双方向アンカーリンク結線
    # 本文中の既存またはAI生成脚注を検索
    footnote_counter = 1
    existing_footnotes = soup.find_all(class_='kindlead-footnote')
    
    # AIがMarkdownテキストのまま出力した段落から注釈行を自動抽出して構造化
    fn_pattern = re.compile(r'^(※|注|\[)(\d+|[０-９]+)(\]|\.|\:|\s|\)|）)\s*(.*)$')
    for p in list(soup.find_all('p')):
        if p.find_parent(class_='kindlead-footnote'):
            continue
        lines = [line.strip() for line in p.get_text().split('\n') if line.strip()]
        matching_lines = [line for line in lines if fn_pattern.match(line)]
        if matching_lines:
            new_elements = []
            for line in lines:
                m = fn_pattern.match(line)
                if m:
                    fn_num = unicodedata.normalize('NFKC', m.group(2))
                    fn_prefix = m.group(1) + m.group(2) + m.group(3)
                    fn_body = m.group(4).strip()
                    
                    fn_id = f"fn-{fn_num}"
                    ref_id = f"fnref-{fn_num}"
                    
                    fn_div = soup.new_tag('div', **{'class': 'kindlead-footnote', 'id': fn_id})
                    fn_heading = soup.new_tag('div', **{'role': 'heading', 'aria-level': '8', 'class': 'footnote-heading'})
                    fn_heading.string = fn_prefix
                    
                    fn_p = soup.new_tag('p')
                    fn_p.string = fn_body + " "
                    
                    back_link = soup.new_tag('a', href=f"#{ref_id}", **{
                        'class': 'footnote-backref',
                        'aria-label': f'本文（注釈{fn_num}）'
                    })
                    back_link.string = "↩"
                    fn_p.append(back_link)
                    
                    fn_div.append(fn_heading)
                    fn_div.append(fn_p)
                    new_elements.append(fn_div)
                else:
                    normal_p = soup.new_tag('p')
                    normal_p.string = line
                    new_elements.append(normal_p)
            
            curr_el = p
            for el in new_elements:
                curr_el.insert_after(el)
                curr_el = el
            p.decompose()

    # 本文中の参照マークを探してリンク化
    for fn in soup.find_all(class_='kindlead-footnote'):
        fn_id = fn.get('id', '')
        if not fn_id.startswith('fn-'):
            continue
        fn_num = fn_id[3:]
        ref_id = f"fnref-{fn_num}"
        ref_candidates = [f"※{fn_num}", f"[{fn_num}]", f"注{fn_num}"]
        for text_node in list(soup.find_all(text=True)):
            if text_node.parent and text_node.parent.name in ['a', 'rt', 'rp', 'script', 'style']:
                continue
            if text_node.find_parent(class_='kindlead-footnote'):
                continue
            node_str = str(text_node)
            replaced = False
            for cand in ref_candidates:
                if cand in node_str and not text_node.find_parent('a'):
                    parts = node_str.split(cand, 1)
                    if len(parts) == 2:
                        new_frag = BeautifulSoup(
                            f'{parts[0]}<sup class="kindlead-footnote-ref"><a href="#{fn_id}" id="{ref_id}" class="footnote-ref" aria-label="注釈{fn_num}">{cand}</a></sup>{parts[1]}',
                            'html.parser'
                        )
                        text_node.replace_with(new_frag)
                        replaced = True
                        break
            if replaced:
                break

    # すでにAIが出力した既存の footnote にも role="heading" aria-level="8" と backref を補完
    for fn in soup.find_all(class_='kindlead-footnote'):
        h_el = fn.find(lambda el: el.get('role') == 'heading' or 'footnote-heading' in el.get('class', []))
        if h_el:
            h_el['role'] = 'heading'
            h_el['aria-level'] = '8'
        fn_id = fn.get('id', '')
        if fn_id.startswith('fn-'):
            num = fn_id[3:]
            ref_id = f"fnref-{num}"
            if not fn.find(class_='footnote-backref'):
                back_link = soup.new_tag('a', href=f"#{ref_id}", **{
                    'class': 'footnote-backref',
                    'aria-label': f'本文（注釈{num}）'
                })
                back_link.string = "↩"
                last_p = fn.find_all('p')
                if last_p:
                    last_p[-1].append(" ")
                    last_p[-1].append(back_link)
                else:
                    fn.append(back_link)

    # 5. 完全なHTMLドキュメントの構築
    final_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{detected_title}</title>
    <style>
        :root {{
            --bg-color: #ffffff;
            --text-color: #1a1a1a;
            --heading-color: #0b3c5d;
            --border-color: #e0e0e0;
            --accent-bg: #f4f6f8;
            --link-color: #0056b3;
            --column-border: #2e86de;
            --footnote-border: #8395a7;
            --figure-color: #c0392b;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Hiragino Kaku Gothic ProN", "Yu Gothic", Meiryo, sans-serif;
            line-height: 1.85;
            max-width: 840px;
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
        p {{ margin-bottom: 1.2em; text-indent: 1em; }}
        ul, ol {{ margin-bottom: 1.2em; padding-left: 1.8em; }}
        li {{ margin-bottom: 0.4em; }}
        a {{ color: var(--link-color); text-decoration: underline; }}
        a:focus, a:hover {{ background-color: #e8f0fe; outline: 3px solid var(--link-color); outline-offset: 2px; }}
        nav[aria-label="目次"], nav[aria-label="Table of Contents"] {{
            background: var(--accent-bg);
            border-left: 4px solid var(--heading-color);
            padding: 16px 20px;
            margin: 24px 0;
            border-radius: 0 8px 8px 0;
        }}
        ruby {{ font-size: 1.0em; }}
        rt {{ font-size: 0.65em; color: #555; }}

        /* 見出しレベル7: コラム・囲み記事・トピックス */
        .kindlead-column, aside[aria-label="コラム"] {{
            background: #f8fbfe;
            border: 1px solid #d0e2f2;
            border-left: 5px solid var(--column-border);
            padding: 16px 20px;
            margin: 24px 0;
            border-radius: 0 8px 8px 0;
        }}
        [role="heading"][aria-level="7"], .column-title {{
            color: #0c5460;
            font-size: 1.15em;
            font-weight: bold;
            margin-top: 0;
            margin-bottom: 0.6em;
            border-bottom: 1px dashed #bee5eb;
            padding-bottom: 0.3em;
        }}

        /* 見出しレベル8: 注釈・脚注・割注 */
        .kindlead-footnote {{
            background: #fafafa;
            border-left: 4px solid var(--footnote-border);
            padding: 12px 16px;
            margin: 14px 0;
            font-size: 0.95em;
            border-radius: 0 6px 6px 0;
        }}
        .kindlead-footnote p {{
            text-indent: 0;
            margin-bottom: 0.4em;
        }}
        [role="heading"][aria-level="8"], .footnote-heading {{
            color: #495057;
            font-size: 1.0em;
            font-weight: bold;
            display: inline-block;
            margin-right: 0.6em;
            margin-bottom: 0.2em;
        }}
        .kindlead-footnote-ref {{
            font-size: 0.8em;
            vertical-align: super;
            margin: 0 2px;
            line-height: 1;
        }}
        .footnote-ref {{
            font-weight: bold;
            text-decoration: none;
            padding: 0 2px;
        }}
        .footnote-backref {{
            margin-left: 8px;
            text-decoration: none;
            color: var(--link-color);
            font-weight: bold;
            font-size: 1.1em;
        }}
        .footnote-backref:focus, .footnote-backref:hover {{
            background-color: #d1ecf1;
            outline: 2px solid var(--link-color);
        }}

        /* 見出しレベル9: 図表キャプション・グラフ解説 */
        .kindlead-figure, figure {{
            margin: 24px 0;
            padding: 18px 20px;
            background: #fdfaf6;
            border: 1px solid #f4e8dc;
            border-left: 5px solid var(--figure-color);
            border-radius: 0 8px 8px 0;
        }}
        [role="heading"][aria-level="9"], .figure-caption, figcaption {{
            color: var(--figure-color);
            font-size: 1.1em;
            font-weight: bold;
            margin-bottom: 0.6em;
        }}

        footer {{ margin-top: 50px; padding-top: 20px; border-top: 2px solid #ccc; }}
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
        <h1>{detected_title}</h1>
    </header>
    <main>
        {str(soup)}
    </main>
    <footer>
        <section class="perf-summary" aria-label="処理パフォーマンス計測結果">
            <h2>⏱ 処理時間ベンチマーク レポート（システム情報）</h2>
            <p>全 {image_count} ページ完走 / キャプチャ: {t_cap:.1f}秒 / AI解析: {t_api:.1f}秒 / 総所要時間: {(t_cap + t_api):.1f}秒</p>
        </section>
    </footer>
</body>
</html>"""

    if output_dir is None:
        user_profile = os.environ.get("USERPROFILE", "")
        desktop = Path(user_profile) / "Desktop"
        if desktop.exists():
            output_dir = desktop
        else:
            output_dir = Path(user_profile)
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    clean_fname = re.sub(r'[^a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', '_', detected_title)
    if not clean_fname.strip('_'):
        clean_fname = "Kindlead_Document"
    output_file = output_dir / f"{clean_fname}.html"
    output_file.write_text(final_html, encoding="utf-8")
    return output_file, detected_title

def main():
    parser = argparse.ArgumentParser(description="Kindlead Core Engine")
    parser.add_argument("--api-key", type=str, required=True, help="Gemini API Key")
    parser.add_argument("--direction", choices=["auto", "left", "right"], default="auto", help="Page turn direction")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory for generated HTML")
    parser.add_argument("--wait", type=float, default=0.4, help="Wait seconds between page turns")
    parser.add_argument("--max-pages", type=int, default=300, help="Max pages limit")
    parser.add_argument("--workers", type=int, default=5, help="Parallel workers count")
    parser.add_argument("--output-json", action="store_true", help="Output JSON result for caller")
    args = parser.parse_args()

    # 1. Kindle最前面化 ＆ 最大化
    focus_and_maximize_kindle()

    # 2. 自動的に書籍の先頭（表紙/位置No.1）に移動
    go_to_first_page()

    # 3. キャプチャ ＆ 組み方向の自動判別 ＆ 終端検知
    captures_dir = Path(os.getenv("TEMP")) / "kindlead_captures"
    image_paths, t_cap, actual_dir = capture_pages_auto(
        max_pages=args.max_pages,
        direction=args.direction,
        wait_sec=args.wait,
        output_dir=captures_dir
    )
    if not image_paths:
        if args.output_json:
            print(json.dumps({"success": False, "error": "キャプチャに失敗しました"}, ensure_ascii=False))
        sys.exit(1)

    # 4. Gemini並列解析
    results, t_api = process_images_parallel(image_paths, args.api_key, max_workers=args.workers)

    # 5. HTML生成
    html_file, title = compile_accessible_html(results, len(image_paths), t_cap, t_api, output_dir=args.output_dir)

    # 6. 完了音 ＆ ブラウザ起動
    try:
        winsound.Beep(440, 100)
        winsound.Beep(659, 100)
        winsound.Beep(880, 220)
    except Exception: pass
    webbrowser.open(html_file.as_uri())

    if args.output_json:
        print(json.dumps({
            "success": True,
            "title": title,
            "pages": len(image_paths),
            "detected_direction": actual_dir,
            "file": str(html_file),
            "total_time": round(t_cap + t_api, 1)
        }, ensure_ascii=False))

if __name__ == "__main__":
    main()
