import re

init_path = r"D:\Katsutoshi\AntiGravity\Kindlead\addon_src\globalPlugins\kindlead\__init__.py"
with open(init_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace notify_ui and add play_beep / play_chord
top_helpers = """def notify_ui(msg):
    \"\"\"メインスレッドで安全にUIメッセージを読み上げる\"\"\"
    core.callLater(0, ui.message, msg)

def play_beep(freq, dur):
    \"\"\"メインスレッドで安全にビープ音を再生する\"\"\"
    core.callLater(0, tones.beep, freq, dur)

def play_chord(*notes):
    \"\"\"メインスレッドで安全に和音/メロディを再生する\"\"\"
    def _do():
        for freq, dur in notes:
            try:
                tones.beep(freq, dur)
            except Exception:
                pass
    core.callLater(0, _do)"""

pattern_helpers = r'def notify_ui\(msg\):[\s\S]*?(?=def get_python_executable)'
content = re.sub(pattern_helpers, top_helpers + '\n\n', content)

# Remove set_speech_muted calls in class GlobalPlugin
content = content.replace("set_speech_muted(True)", "# no mute")
content = content.replace("set_speech_muted(False)", "# no mute")

# Replace tones.beep in worker thread with play_beep / play_chord
old_thread_body = """                        if event == "page":
                            tones.beep(440, 60)
                        elif event == "analyzed":
                            tones.beep(554, 50)
                        elif event == "end_of_book":
                            tones.beep(440, 70)
                            tones.beep(554, 70)
                            tones.beep(659, 100)
                        elif data.get("success") is not None:
                            res_json = data
                    except Exception:
                        pass

            stderr_out = self._current_process.stderr.read() if self._current_process else ""
            if self._current_process:
                self._current_process.wait()
                ret_code = self._current_process.returncode
            else:
                ret_code = -1

            was_running = self._is_running
            self._is_running = False
            self._current_process = None

            # 処理完了時にミュート解除
            # no mute

            if not was_running:
                # 中止された場合
                return

            if ret_code == 0:
                tones.beep(440, 100)
                tones.beep(659, 100)
                tones.beep(880, 220)"""

new_thread_body = """                        if event == "page":
                            play_beep(440, 60)
                        elif event == "analyzed":
                            play_beep(554, 50)
                        elif event == "end_of_book":
                            play_chord((440, 70), (554, 70), (659, 100))
                        elif data.get("success") is not None:
                            res_json = data
                    except Exception:
                        pass

            stderr_out = self._current_process.stderr.read() if self._current_process else ""
            if self._current_process:
                self._current_process.wait()
                ret_code = self._current_process.returncode
            else:
                ret_code = -1

            was_running = self._is_running
            self._is_running = False
            self._current_process = None

            if not was_running:
                # 中止された場合
                return

            if ret_code == 0:
                play_chord((440, 100), (659, 100), (880, 220))"""

content = content.replace(old_thread_body, new_thread_body)

# Replace stopExtraction tones
content = content.replace("tones.beep(440, 100)\n        tones.beep(330, 150)", "play_chord((440, 100), (330, 150))")

with open(init_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated __init__.py with thread-safe audio dispatchers!")
