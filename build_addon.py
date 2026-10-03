import zipfile
from pathlib import Path

src_dir = Path("D:/Katsutoshi/AntiGravity/Kindlead/addon_src")
output_addon = Path("D:/Katsutoshi/AntiGravity/Kindlead/Kindlead-1.0.0.nvda-addon")

with zipfile.ZipFile(output_addon, 'w', zipfile.ZIP_DEFLATED) as zf:
    for file in src_dir.rglob('*'):
        if file.is_file():
            arcname = file.relative_to(src_dir)
            zf.write(file, arcname)

print(f"アドオンのビルドが完了しました: {output_addon}")
