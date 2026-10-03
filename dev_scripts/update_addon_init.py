import re

init_path = r"D:\Katsutoshi\AntiGravity\Kindlead\addon_src\globalPlugins\kindlead\__init__.py"
with open(init_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_imports = """import config
import speech
import ui
import core
import tones
import api
import appModuleHandler
from logHandler import log"""

new_mute = """_saved_speech_mode = None
_managed_app_modules = set()

def set_speech_muted(muted):
    \"\"\"メインスレッドで安全に音声出力をミュート/解除し、Kindleアプリをスリープモードにする\"\"\"
    def _do():
        global _saved_speech_mode, _managed_app_modules
        try:
            speech.cancelSpeech()
            
            # 1. KindleのAppModuleおよび現在フォーカス中のAppModuleをスリープモードにする
            try:
                if hasattr(appModuleHandler, 'runningTable'):
                    for pid, mod in appModuleHandler.runningTable.items():
                        if mod and hasattr(mod, 'appName') and 'kindle' in str(mod.appName).lower():
                            mod.sleepMode = muted
                            _managed_app_modules.add(mod)
                            log.info(f"[Kindlead] Kindle appModule sleepMode: {muted}")
                
                focus = api.getFocusObject()
                if focus and focus.appModule:
                    focus.appModule.sleepMode = muted
                    _managed_app_modules.add(focus.appModule)
                    log.info(f"[Kindlead] Focus appModule ({focus.appModule.appName}) sleepMode: {muted}")

                if not muted:
                    for mod in list(_managed_app_modules):
                        try:
                            mod.sleepMode = False
                        except Exception:
                            pass
                    _managed_app_modules.clear()
            except Exception as e:
                log.error(f"[Kindlead] sleepMode設定エラー: {e}")

            # 2. 全体の音声出力を停止/復帰
            try:
                from speech.speechMode import SpeechMode
                if muted:
                    if _saved_speech_mode is None:
                        _saved_speech_mode = speech.getState().speechMode
                    speech.setSpeechMode(SpeechMode.off)
                else:
                    target_mode = _saved_speech_mode if _saved_speech_mode is not None else SpeechMode.talk
                    speech.setSpeechMode(target_mode)
                    _saved_speech_mode = None
            except Exception:
                try:
                    if hasattr(speech, 'speechMode_off'):
                        speech.speechMode = speech.speechMode_off if muted else speech.speechMode_talk
                except Exception:
                    pass

            log.info(f"[Kindlead] 音声ミュート状態: {muted}")
        except Exception as e:
            log.error(f"[Kindlead] set_speech_muted({muted}) エラー: {e}")
    core.callLater(0, _do)"""

old_imports = """import config
import speech
import ui
import core
import tones
from logHandler import log"""

pattern = r'def set_speech_muted\(muted\):[\s\S]*?(?=def get_python_executable)'

content = content.replace(old_imports, new_imports)
content = re.sub(pattern, new_mute + '\n\n', content)

with open(init_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated __init__.py with sleepMode successfully!")
