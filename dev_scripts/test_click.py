import pyautogui
import time
import subprocess
from PIL import Image
import numpy as np

# Kindle最前面化
subprocess.run(["powershell", "-NoProfile", "-Command", "$wshell = New-Object -ComObject Wscript.Shell; $wshell.AppActivate('Kindle')"])
time.sleep(1.0)

screen_w, screen_h = pyautogui.size()
print(f"画面サイズ: {screen_w}x{screen_h}")

# 1. 撮影前のスクショ
img_before = pyautogui.screenshot()

# 2. 画面の左端中央（X=80, Y=screen_h//2）をクリック（縦書きの進むボタン領域）
click_x = 80
click_y = screen_h // 2
print(f"画面左端 ({click_x}, {click_y}) をクリックします...")
pyautogui.click(click_x, click_y)
time.sleep(1.2)

# 3. 撮影後のスクショ
img_after = pyautogui.screenshot()
img_after.save("D:/Katsutoshi/AntiGravity/Kindlead/captures/test_after_click.png")

# 差分確認
diff = np.abs(np.array(img_before) - np.array(img_after)).sum()
print(f"クリック前後のピクセル差分: {diff}")
if diff > 500000:
    print("=> 成功！ページがめくられました！")
else:
    print("=> まだページが変わっていません。別の位置を試します。")
