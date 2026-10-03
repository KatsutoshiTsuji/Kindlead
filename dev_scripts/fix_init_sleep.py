import re

init_path = r"D:\Katsutoshi\AntiGravity\Kindlead\addon_src\globalPlugins\kindlead\__init__.py"
with open(init_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    def __init__(self):
        super().__init__()
        self._is_running = False
        self._current_process = None
        NVDASettingsDialog.categoryClasses.append(KindleadSettingsPanel)"""

replacement = """    def __init__(self):
        super().__init__()
        self._is_running = False
        self._current_process = None
        
        # 過去の実行で残ったsleepModeやミュートを確実にリセット
        try:
            if hasattr(appModuleHandler, 'runningTable'):
                for pid, mod in appModuleHandler.runningTable.items():
                    if mod:
                        mod.sleepMode = False
        except Exception:
            pass
        try:
            from speech.speechMode import SpeechMode
            speech.setSpeechMode(SpeechMode.talk)
        except Exception:
            try:
                speech.speechMode = speech.speechMode_talk
            except Exception:
                pass

        NVDASettingsDialog.categoryClasses.append(KindleadSettingsPanel)"""

content = content.replace(target, replacement)

with open(init_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Added explicit sleepMode reset on __init__!")
