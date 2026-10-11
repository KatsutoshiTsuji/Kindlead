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

try:
    import addonHandler
    addonHandler.initTranslation()
except Exception:
    import gettext
    gettext.install("kindlead")

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
            _("Gemini API Key (&K):"),
            wx.TextCtrl,
            value=cur_key
        )

        # APIキー支援ボタン
        apiBtnSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.getApiKeyBtn = wx.Button(self, label=_("Open Gemini API Key page in browser (&G)"))
        self.pasteApiKeyBtn = wx.Button(self, label=_("Paste from clipboard (&V)"))
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
            _("Output folder (&O):"),
            wx.TextCtrl,
            value=cur_output_dir
        )
        self.browseOutputDirBtn = wx.Button(self, label=_("Browse output folder (&B)..."))
        self.browseOutputDirBtn.Bind(wx.EVT_BUTTON, self.onBrowseOutputDir)
        sHelper.addItem(self.browseOutputDirBtn)

        # 3. ページめくり待機時間
        self.pageWaitEdit = sHelper.addLabeledControl(
            _("Page turn wait (seconds) (&W):"),
            wx.TextCtrl,
            value=str(config.conf["kindlead"]["pageWait"])
        )
        
        # 4. 最大ページ数
        self.maxPagesEdit = sHelper.addLabeledControl(
            _("Maximum pages to capture (&M):"),
            wx.TextCtrl,
            value=str(config.conf["kindlead"]["maxPages"])
        )
        
        # 5. Pythonパス指定
        self.pythonPathEdit = sHelper.addLabeledControl(
            _("Python executable path (auto-detected if blank) (&P):"),
            wx.TextCtrl,
            value=config.conf["kindlead"]["pythonPath"]
        )

    def onGetApiKey(self, event):
        url = "https://aistudio.google.com/app/apikey"
        webbrowser.open(url)
        ui.message(_("Opened Google AI Studio API key page in browser. Copy your key, then click Paste."))

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
            ui.message(_("Pasted API key from clipboard."))
        else:
            ui.message(_("No text found in clipboard."))

    def onBrowseOutputDir(self, event):
        cur_dir = self.outputDirEdit.GetValue().strip() or get_default_output_dir()
        with wx.DirDialog(self, _("Select output folder"), defaultPath=cur_dir, style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.outputDirEdit.SetValue(dlg.GetPath())
                ui.message(_("Output folder set to {path}").format(path=dlg.GetPath()))

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
        super().__init__(parent, title=_("Kindlead - Kindle Book Structured Capture"), style=wx.DEFAULT_DIALOG_STYLE)
        self.on_start_callback = on_start_callback

        mainSizer = wx.BoxSizer(wx.VERTICAL)

        guidance_text = _(
            "[Important Checklist Before Starting]\n"
            "Open the target book in Kindle for PC and display the beginning (cover / page 1).\n\n"
            "● Once started, Kindle will automatically turn pages in full screen.\n"
            "  Please do not touch the keyboard or mouse for a few minutes until completion.\n"
            "● Progress is signaled with beeps (Page capture: 440Hz / AI analysis: 554Hz).\n"
            "● Upon completion, a chime plays, and the structured HTML with TOC links opens in your browser.\n"
            "● To cancel midway, run Kindlead from the NVDA menu again to safely stop."
        )

        descText = wx.StaticText(self, label=guidance_text)
        mainSizer.Add(descText, 0, wx.ALL, 12)

        # 送り方向（デフォルトは自動判別）
        self.directionRadio = wx.RadioBox(
            self,
            label=_("Reading direction (&D)"),
            choices=[
                _("Auto detect (recommended)"),
                _("Vertical (right-to-left)"),
                _("Horizontal (left-to-right)")
            ],
            majorDimension=1
        )
        self.directionRadio.SetSelection(0)
        mainSizer.Add(self.directionRadio, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        # ボタン
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.startBtn = wx.Button(self, wx.ID_OK, label=_("Start Capture (&S)"))
        self.cancelBtn = wx.Button(self, wx.ID_CANCEL, label=_("Cancel (&C)"))
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
            _("Kindlead - Structured capture from Kindle book (&K)..."),
            _("Automatically convert Kindle for PC book into accessible HTML")
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
                _("Capture is currently in progress. Do you want to abort?"),
                _("Kindlead - Running"),
                wx.YES_NO | wx.ICON_QUESTION
            )
            if res == wx.YES:
                self.stopExtraction()
            return

        api_key = config.conf["kindlead"]["geminiApiKey"] or load_fallback_api_key()
        if not api_key:
            gui.messageBox(
                _("Gemini API key is not configured.\nPlease go to NVDA Menu -> Preferences -> Settings -> Kindlead to enter your API key."),
                _("Kindlead - API Key Required"),
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
        notify_ui(_("Kindlead: Capture aborted."))

    def startExtraction(self, direction):
        if self._is_running:
            return
        self._is_running = True
        ui.message(_("Kindlead: Starting capture. Bringing Kindle to front..."))
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
                notify_ui(_("Kindlead: engine.py not found."))
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
                    title = res_json.get("title", "Book")
                    pages = res_json.get("pages", 0)
                    total_time = res_json.get("total_time", 0)
                    msg = _("Kindlead: Successfully captured '{title}' ({pages} pages) in {total_time}s!").format(
                        title=title, pages=pages, total_time=total_time
                    )
                    notify_ui(msg)
                else:
                    notify_ui(_("Kindlead: Capture completed. Opening HTML on Desktop."))
            else:
                err_msg = (stderr_out or "Unknown error").strip()
                log.error(f"[Kindlead] エンジンエラー: {err_msg}")
                notify_ui(_("Kindlead: An error occurred during capture.\n{err_msg}").format(err_msg=err_msg[:120]))

        except Exception as e:
            self._is_running = False
            self._current_process = None
            log.error(f"[Kindlead] 予期せぬ例外: {e}")
            notify_ui(_("Kindlead: Unexpected error: {e}").format(e=e))
