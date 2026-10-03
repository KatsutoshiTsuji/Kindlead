import re

init_path = r"D:\Katsutoshi\AntiGravity\Kindlead\addon_src\globalPlugins\kindlead\__init__.py"
with open(init_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace set_speech_muted to be a simple no-op/cancelSpeech or remove it
clean_mute = """def set_speech_muted(muted):
    \"\"\"NVDAの安定動作を優先し、無理なスリープを避けて安全に音声制御する\"\"\"
    pass"""

pattern = r'_saved_speech_mode = None[\s\S]*?(?=def get_python_executable)'
content = re.sub(pattern, clean_mute + '\n\n', content)

with open(init_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Simplified speech handling for maximum stability!")
