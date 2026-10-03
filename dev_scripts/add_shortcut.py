import re

init_path = r"D:\Katsutoshi\AntiGravity\Kindlead\addon_src\globalPlugins\kindlead\__init__.py"
with open(init_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add scriptHandler import if not present
if "import scriptHandler" not in content:
    content = content.replace("import globalPluginHandler", "import globalPluginHandler\nimport scriptHandler")

# Update GlobalPlugin class
old_gp_start = "class GlobalPlugin(globalPluginHandler.GlobalPlugin):\n    scriptCategory = \"Kindlead\""

new_gp = """class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = "Kindlead"

    __gestures__ = {
        "kb:NVDA+shift+k": "startExtraction"
    }

    def __init__(self):
        super().__init__()
        self._is_running = False
        self._current_process = None
        NVDASettingsDialog.categoryClasses.append(KindleadSettingsPanel)
        
        self.menuItem = gui.mainFrame.sysTrayIcon.toolsMenu.Append(
            wx.ID_ANY,
            "Kindlead - Kindle書籍の構造化取り込み(&K)...\\tNVDA+Shift+K",
            "Kindle for PCの書籍を完全アクセシブルなHTMLに自動変換します"
        )
        gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onKindleadMenu, self.menuItem)

    def terminate(self):
        if self._is_running:
            self.stopExtraction()
        try:
            NVDASettingsDialog.categoryClasses.remove(KindleadSettingsPanel)
        except Exception:
            pass
        try:
            gui.mainFrame.sysTrayIcon.toolsMenu.Remove(self.menuItem)
        except Exception:
            pass
        super().terminate()

    @scriptHandler.script(
        description="Kindlead: Kindle書籍の取り込みを開始または中止します",
        gesture="kb:NVDA+shift+k"
    )
    def script_startExtraction(self, gesture):
        if self._is_running:
            self.stopExtraction()
            return
            
        api_key = config.conf["kindlead"]["geminiApiKey"] or load_fallback_api_key()
        if not api_key:
            gui.messageBox(
                "Gemini APIキーが設定されていません。\\nNVDAメニュー → 設定 → 設定 → Kindlead からAPIキーを設定してください。",
                "Kindlead - APIキー未設定",
                wx.OK | wx.ICON_WARNING
            )
            return

        dlg = KindleadDialog(gui.mainFrame, self.startExtraction)
        dlg.ShowModal()

    def onKindleadMenu(self, event):
        self.script_startExtraction(None)

    def stopExtraction(self):
        if self._current_process and self._current_process.poll() is None:
            try:
                self._current_process.terminate()
            except Exception:
                pass
        self._is_running = False
        self._current_process = None
        set_speech_muted(False)
        tones.beep(440, 100)
        tones.beep(330, 150)
        notify_ui("Kindlead: 取り込みを中止しました。")

    def startExtraction(self, direction):
        if self._is_running:
            return
        self._is_running = True
        ui.message("Kindlead: 取り込みを開始します。Kindleを最前面化しています...")
        worker = threading.Thread(target=self._run_extraction_thread, args=(direction,), daemon=True)
        worker.start()

    def _run_extraction_thread(self, direction):
        try:
            # 開始アナウンス完了を待ってから完全ミュート
            time.sleep(1.2)
            set_speech_muted(True)
            
            api_key = config.conf["kindlead"]["geminiApiKey"] or load_fallback_api_key()
            page_wait = config.conf["kindlead"]["pageWait"]
            max_pages = config.conf["kindlead"]["maxPages"]
            output_dir = config.conf["kindlead"]["outputDir"] or get_default_output_dir()
            python_exe = get_python_executable()

            plugin_dir = Path(__file__).parent
            engine_path = plugin_dir / "engine.py"
            if not engine_path.exists():
                engine_path = Path(r"D:\\Katsutoshi\\AntiGravity\\Kindlead\\kindlead_engine.py")

            if not engine_path.exists():
                self._is_running = False
                set_speech_muted(False)
                notify_ui("Kindlead: engine.py が見つかりませんでした。")
                return

            cmd = [
                python_exe,
                str(engine_path),
                "--api-key", api_key,
                "--direction", direction,
                "--output-dir", output_dir,
                "--wait", str(page_wait),
                "--max-pages", str(max_pages),
                "--output-json"
            ]

            log.info(f"[Kindlead] エンジン起動: {' '.join(cmd[:3])} ...")
            
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"

            self._current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            res_json = None
            for raw_line in iter(self._current_process.stdout.readline, ''):
                if not self._is_running:
                    break
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("{") and line.endswith("}"):
                    try:
                        data = json.loads(line)
                        event = data.get("event")
                        if event == "page":
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
            set_speech_muted(False)

            if not was_running:
                # 中止された場合
                return

            if ret_code == 0:
                tones.beep(440, 100)
                tones.beep(659, 100)
                tones.beep(880, 220)
                if res_json and res_json.get("success"):
                    title = res_json.get("title", "電子書籍")
                    pages = res_json.get("pages", 0)
                    total_time = res_json.get("total_time", 0)
                    notify_ui(f"Kindlead: 『{title}』 全 {pages} ページの構造化取り込みが完了しました！（所要時間: {total_time}秒）")
                else:
                    notify_ui("Kindlead: 取り込みが完了しました。デスクトップのHTMLを開きます。")
            else:
                err_msg = (stderr_out or "不明なエラー").strip()
                log.error(f"[Kindlead] エンジンエラー: {err_msg}")
                notify_ui(f"Kindlead: 取り込み中にエラーが発生しました。\\n{err_msg[:120]}")

        except Exception as e:
            self._is_running = False
            self._current_process = None
            set_speech_muted(False)
            log.error(f"[Kindlead] 予期せぬ例外: {e}")
            notify_ui(f"Kindlead: エラーが発生しました: {e}")
"""

# Replace from class GlobalPlugin to the end
idx = content.find("class GlobalPlugin(globalPluginHandler.GlobalPlugin):")
if idx != -1:
    content = content[:idx] + new_gp

with open(init_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Added script_startExtraction and NVDA+Shift+K binding successfully!")
