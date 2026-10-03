import os, sys
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from PIL import Image

load_dotenv(r"D:\Katsutoshi\AntiGravity\Kindlead\.env")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

snapshots_dir = Path(r"D:\Katsutoshi\AntiGravity\Kindlead\video_snapshots")

# Check key frames
key_frames = [
    "frame_0000s.png", "frame_0004s.png", "frame_0008s.png", "frame_0012s.png",
    "frame_0016s.png", "frame_0020s.png", "frame_0030s.png", "frame_0060s.png",
    "frame_0386s.png", "frame_0682s.png", "frame_0711s.png", "frame_0720s.png",
    "frame_0732s.png", "frame_0741s.png", "frame_0744s.png"
]

for fname in key_frames:
    fpath = snapshots_dir / fname
    if not fpath.exists(): continue
    img = Image.open(fpath)
    resp = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[
            img,
            "この画面の内容を簡潔に教えてください。"
            "1. 何のアプリ・画面（Kindle, NVDAメニュー/ダイアログ, ブラウザ, デスクトップ, 録画ソフト等）が表示されているか？"
            "2. 操作の開始・実行中・完了のどの段階か？"
            "3. 個人情報（名前、メール、プライベートな通知・ファイル等）はあるか？"
        ]
    )
    print(f"=== {fname} ===")
    print(resp.text.strip())
    print("-" * 50)
