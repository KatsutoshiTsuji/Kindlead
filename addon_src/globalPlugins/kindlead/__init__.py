"""
Kindlead - Kindle Accessible Reader
NVDA Global Plugin
Author: Debugon & Antigravity
"""

import os
import sys
import time
import json
import shutil
import threading
import subprocess
import webbrowser
from pathlib import Path

import wx
import globalPluginHandler
import scriptHandler
import gui
try:
    from gui.settingsDialogs import SettingsPanel, NVDASettingsDialog
except ImportError:
    from gui import SettingsPanel, NVDASettingsDialog

import config
import speech
import ui
import core
import tones
import api
import appModuleHandler
from logHandler import log

def get_default_output_dir():
    """デフォルトの出力先フォルダ（デスクトップ）を取得"""
    user_profile = os.environ.get("USERPROFILE", "")
    desktop = Path(user_profile) / "Desktop"
    if desktop.exists():
        return str(desktop)
    return user_profile

# 設定の初期化
confspec = {
    "geminiApiKey": "string(default='')",
    "outputDir": f"string(default='{get_default_output_dir()}')",
    "pageWait": "float(default=0.4)",
    "maxPages": "integer(default=300)",
    "pythonPath": "string(default='')"
}
config.conf.spec["kindlead"] = confspec

def notify_ui(msg):
    """メインスレッドで安全にUIメッセージを読み上げる"""
    core.callLater(0, ui.message, msg)

def play_beep(freq, dur):
    """メインスレッドで安全にビープ音を再生する"""
    core.callLater(0, tones.beep, freq, dur)

def play_chord(*notes):
    """メインスレッドで安全に和音/メロディを再生する"""
    def _do():
        for freq, dur in notes:
            try:
                tones.beep(freq, dur)
            except Exception:
                pass
    core.callLater(0, _do)

def get_python_executable():
    """OSにインストールされているPython実行バイナリを探す"""
    custom_path = config.conf["kindlead"]["pythonPath"]
    if custom_path and os.path.isfile(custom_path):
        return custom_path
        
    for candidate in ["python", "python3", "py"]:
        p = shutil.which(candidate)
        if p and "nvda" not in p.lower():
            return p
            
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        py_dir = Path(local_appdata) / "Programs" / "Python"
        if py_dir.exists():
            for p in py_dir.glob("Python*/python.exe"):
                if p.is_file():
                    return str(p)
                    
    return "python"

def load_fallback_api_key():
    """設定が空の場合、ワークスペースの.env等からフォールバック探索"""
    saved_key = config.conf["kindlead"]["geminiApiKey"]
    if saved_key:
        return saved_key
    env_paths = [
        Path(r"D:\Katsutoshi\AntiGravity\Kindlead\.env"),
        Path(os.environ.get("USERPROFILE", "")) / ".gemini" / ".env"
    ]
    for ep in env_paths:
        if ep.exists():
            try:
                for line in ep.read_text(encoding="utf-8").splitlines():
                    if line.startswith("GEMINI_API_KEY="):
                        k = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if k:
                            return k
            except Exception:
                pass
    return ""

class KindleadSettingsPanel(SettingsPanel):
    title = "Kindlead"

    def makeSettings(self, settingsSizer):
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        
        # 1. APIキー入力
        cur_key = config.conf["kindlead"]["geminiApiKey"]
        if not cur_key:
            cur_key = load_fallback_api_key()
            
        self.apiKeyEdit = sHelper.addLabeledControl(
            "Gemini APIキー (&K):",
            wx.TextCtrl,
            value=cur_key
        )

        # APIキー支援ボタン
        apiBtnSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.getApiKeyBtn = wx.Button(self, label="Gemini APIキー取得ページを開く (ブラウザ) (&G)")
        self.pasteApiKeyBtn = wx.Button(self, label="クリップボードから貼り付け (&V)")
        apiBtnSizer.Add(self.getApiKeyBtn, 0, wx.RIGHT, 10)
        apiBtnSizer.Add(self.pasteApiKeyBtn, 0)
        sHelper.addItem(apiBtnSizer)

        self.getApiKeyBtn.Bind(wx.EVT_BUTTON, self.onGetApiKey)
        self.pasteApiKeyBtn.Bind(wx.EVT_BUTTON, self.onPasteApiKey)
        
        # 2. 保存先フォルダー（デフォルト: デスクトップ）
        cur_output_dir = config.conf["kindlead"]["outputDir"]
        if not cur_output_dir:
            cur_output_dir = get_default_output_dir()

        self.outputDirEdit = sHelper.addLabeledControl(
            "保存先フォルダー (&O):",
            wx.TextCtrl,
            value=cur_output_dir
        )
        self.browseOutputDirBtn = wx.Button(self, label="保存先フォルダーの参照 (&B)...")
        self.browseOutputDirBtn.Bind(wx.EVT_BUTTON, self.onBrowseOutputDir)
        sHelper.addItem(self.browseOutputDirBtn)

        # 3. ページめくり待機時間
        self.pageWaitEdit = sHelper.addLabeledControl(
            "ページ送り待機秒数 (&W):",
            wx.TextCtrl,
            value=str(config.conf["kindlead"]["pageWait"])
        )
        
        # 4. 最大ページ数
        self.maxPagesEdit = sHelper.addLabeledControl(
            "最大取り込み上限ページ数 (&M):",
            wx.TextCtrl,
            value=str(config.conf["kindlead"]["maxPages"])
        )
        
        # 5. Pythonパス指定
        self.pythonPathEdit = sHelper.addLabeledControl(
            "Python実行パス（通常は空欄で自動検出） (&P):",
            wx.TextCtrl,
            value=config.conf["kindlead"]["pythonPath"]
        )

    def onGetApiKey(self, event):
        url = "https://aistudio.google.com/app/apikey"
        webbrowser.open(url)
        ui.message("Google AI StudioのAPIキー取得ページをブラウザで開きました。キーを作成・コピー後、貼り付けボタンを押してください。")

    def onPasteApiKey(self, event):
        text = ""
        if wx.TheClipboard.Open():
            if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
                data = wx.TextDataObject()
                wx.TheClipboard.GetData(data)
                text = data.GetText().strip()
            wx.TheClipboard.Close()
            
        if text:
            self.apiKeyEdit.SetValue(text)
            ui.message("クリップボードからAPIキーを貼り付けました。")
        else:
            ui.message("クリップボードにテキストが見つかりませんでした。")

    def onBrowseOutputDir(self, event):
        cur_dir = self.outputDirEdit.GetValue().strip() or get_default_output_dir()
        with wx.DirDialog(self, "保存先フォルダーを選択してください", defaultPath=cur_dir, style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.outputDirEdit.SetValue(dlg.GetPath())
                ui.message(f"保存先を {dlg.GetPath()} に設定しました。")

    def onSave(self):
        config.conf["kindlead"]["geminiApiKey"] = self.apiKeyEdit.GetValue().strip()
        config.conf["kindlead"]["outputDir"] = self.outputDirEdit.GetValue().strip() or get_default_output_dir()
        try:
            config.conf["kindlead"]["pageWait"] = float(self.pageWaitEdit.GetValue())
        except ValueError:
            pass
        try:
            config.conf["kindlead"]["maxPages"] = int(self.maxPagesEdit.GetValue())
        except ValueError:
            pass
        config.conf["kindlead"]["pythonPath"] = self.pythonPathEdit.GetValue().strip()

class KindleadDialog(wx.Dialog):
    def __init__(self, parent, on_start_callback):
        super().__init__(parent, title="Kindlead - Kindle書籍の構造化取り込み", style=wx.DEFAULT_DIALOG_STYLE)
        self.on_start_callback = on_start_callback

        mainSizer = wx.BoxSizer(wx.VERTICAL)

        descText = wx.StaticText(
            self,
            label=(
                "【取り込み前の確認事項】\n"
                "Kindle for PCで読みたい書籍を開き、【先頭（表紙）】を表示させた状態で開始してください。\n\n"
                "● 開始後は画面最前面でKindleが自動的にページをめくります。\n"
                "  完了するまでの数分間は、PCのキーボードやマウスに触れずにお待ちください。\n"
                "● 進捗はビープ音（ページ撮影時: 440Hz / AI解析完了時: 554Hz）でお知らせします。\n"
                "● 完了すると上昇和音が鳴り、デスクトップに目次リンク付きHTMLが保存されて自動で開きます。\n"
                "● 途中で止めたい場合は、再度メニューからKindleadを実行すると安全に中断できます。"
            )
        )
        mainSizer.Add(descText, 0, wx.ALL, 12)

        # 送り方向（デフォルトは自動判別）
        self.directionRadio = wx.RadioBox(
            self,
            label="書籍の組み方向 (&D)",
            choices=["自動判別（おすすめ）", "縦書き（右開き）", "横書き（左開き）"],
            majorDimension=1
        )
        self.directionRadio.SetSelection(0)
        mainSizer.Add(self.directionRadio, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        # ボタン
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.startBtn = wx.Button(self, wx.ID_OK, label="取り込み開始 (&S)")
        self.cancelBtn = wx.Button(self, wx.ID_CANCEL, label="キャンセル (&C)")
        btnSizer.Add(self.startBtn, 0, wx.RIGHT, 10)
        btnSizer.Add(self.cancelBtn, 0)
        mainSizer.Add(btnSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 12)

        self.SetSizerAndFit(mainSizer)
        self.startBtn.SetDefault()
        self.startBtn.Bind(wx.EVT_BUTTON, self.onStart)

    def onStart(self, event):
        sel = self.directionRadio.GetSelection()
        direction = "auto" if sel == 0 else ("left" if sel == 1 else "right")
        self.EndModal(wx.ID_OK)
        self.on_start_callback(direction)

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = "Kindlead"

    def __init__(self):
        super().__init__()
        self._is_running = False
        self._current_process = None
        
        # 過去の実行状態をクリーンにリセット
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
            pass

        NVDASettingsDialog.categoryClasses.append(KindleadSettingsPanel)
        
        self.menuItem = gui.mainFrame.sysTrayIcon.toolsMenu.Append(
            wx.ID_ANY,
            "Kindlead - Kindle書籍の構造化取り込み(&K)...",
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

    def onKindleadMenu(self, event):
        if self._is_running:
            res = gui.messageBox(
                "現在取り込み処理が実行中です。処理を中止しますか？",
                "Kindlead - 実行中",
                wx.YES_NO | wx.ICON_QUESTION
            )
            if res == wx.YES:
                self.stopExtraction()
            return

        api_key = config.conf["kindlead"]["geminiApiKey"] or load_fallback_api_key()
        if not api_key:
            gui.messageBox(
                "Gemini APIキーが設定されていません。\nNVDAメニュー → 設定 → 設定 → Kindlead からAPIキーを設定してください。",
                "Kindlead - APIキー未設定",
                wx.OK | wx.ICON_WARNING
            )
            return

        dlg = KindleadDialog(gui.mainFrame, self.startExtraction)
        dlg.ShowModal()

    def stopExtraction(self):
        if self._current_process and self._current_process.poll() is None:
            try:
                self._current_process.terminate()
            except Exception:
                pass
        self._is_running = False
        self._current_process = None
        play_chord((440, 100), (330, 150))
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
            api_key = config.conf["kindlead"]["geminiApiKey"] or load_fallback_api_key()
            page_wait = config.conf["kindlead"]["pageWait"]
            max_pages = config.conf["kindlead"]["maxPages"]
            output_dir = config.conf["kindlead"]["outputDir"] or get_default_output_dir()
            python_exe = get_python_executable()

            plugin_dir = Path(__file__).parent
            engine_path = plugin_dir / "engine.py"
            if not engine_path.exists():
                engine_path = Path(r"D:\Katsutoshi\AntiGravity\Kindlead\kindlead_engine.py")

            if not engine_path.exists():
                self._is_running = False
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
                return

            if ret_code == 0:
                play_chord((440, 100), (659, 100), (880, 220))
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
                notify_ui(f"Kindlead: 取り込み中にエラーが発生しました。\n{err_msg[:120]}")

        except Exception as e:
            self._is_running = False
            self._current_process = None
            log.error(f"[Kindlead] 予期せぬ例外: {e}")
            notify_ui(f"Kindlead: エラーが発生しました: {e}")
