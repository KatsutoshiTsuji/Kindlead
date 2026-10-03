import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from PIL import Image

load_dotenv(r"D:\Katsutoshi\AntiGravity\Kindlead\.env")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

snapshots_dir = Path(r"D:\Katsutoshi\AntiGravity\Kindlead\video_snapshots")
frames = sorted(snapshots_dir.glob("*.png"))

print(f"Analyzing {len(frames)} snapshot frames for video trimming & privacy check...")

for f in frames:
    img = Image.open(f)
    resp = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[
            img,
            "この画面に何が映っているかを2〜3行で簡潔に要約してください。"
            "特に以下の点を確認してください："
            "1. Kindleアプリ、NVDAダイアログ、ブラウザ、デスクトップ、OBS/録画ツールのどれが表示されているか。"
            "2. 個人情報（氏名、メールアドレス、プライベートなファイル名・通知・チャット等）が映り込んでいないか。"
        ]
    )
    print(f"=== {f.name} ===")
    print(resp.text.strip())
    print()
