# Kindlead (Kindle Accessible Reader)

[English](#english) | [日本語](#japanese)

---

<a id="english"></a>
## English

**Kindlead** is an NVDA (NonVisual Desktop Access) screen reader add-on designed for blind and visually impaired users to read inaccessible books on Kindle for PC (especially fixed-layout books, technical books, and image-only publications).

By combining automated full-screen page navigation with Google's multimodal AI (Gemini), Kindlead scans the entire book, recognizes heading hierarchies (`h1`–`h4`), extracts clean text, and compiles it into a **fully accessible HTML document with an interactive Table of Contents (TOC)** that opens instantly in your default web browser.

### 🌟 Key Features

1. **Automated Page Capture**
   - Automatically navigates and captures pages from the cover to the end of the book in full-screen mode.
2. **Gemini Vision AI Structuring**
   - Accurately identifies chapters, sections, subheadings (`h1`–`h4`), ruby/furigana readings, and body text.
3. **Interactive Table of Contents (TOC)**
   - Generates a semantic `<nav>` table of contents at the beginning with anchor links jumping directly to corresponding sections in the text.
4. **Screen Reader-Friendly Audio Cues**
   - Provides pleasant, real-time auditory feedback (440Hz for capture, 554Hz for AI analysis completion, ascending chime on finish) without interrupting speech.
5. **Instant Browser Reading**
   - Once capture completes, the formatted HTML file opens in your browser, ready for immediate, comfortable reading using NVDA quick navigation keys (`H` for headings, `1`–`6` for levels).
6. **Integrated NVDA Settings Panel**
   - Configure and securely store your Gemini API key directly within NVDA's Preferences &rarr; Settings dialog.
7. **Bilingual Support (English & Japanese)**
   - The UI, dialogs, messages, and documentation automatically adapt to your NVDA language (English or Japanese).

### 🚀 Installation

1. Download the latest `Kindlead-x.x.x.nvda-addon` from [Releases](https://github.com/KatsutoshiTsuji/Kindlead/releases).
2. Press `Enter` on the downloaded file or install it through NVDA's Add-on Store / Manager.
3. Restart NVDA when prompted.

### 📖 How to Use

#### 1. Setup API Key (First Time Only)
1. Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/).
2. Press `NVDA + N` &rarr; **Preferences** &rarr; **Settings...** (`NVDA + Ctrl + K`).
3. Select the **Kindlead** category from the list.
4. Paste your API key into the "Gemini API Key" field and press **OK**.

#### 2. Capture and Read a Book
1. Launch **Kindle for PC** and open the book you want to read.
2. Ensure the book is displayed at the **cover (page 1)**.
3. Press `NVDA + N` &rarr; **Tools** &rarr; **Kindlead - Structured capture from Kindle book...**
4. Review the guidance dialog and click **Start Capture** (`Alt + S`).
5. Kindlead will bring Kindle to the front and begin automated page turning. Please do not touch the keyboard or mouse during this time.
6. Upon completion, a success chime will sound, and the structured HTML book will open automatically in your browser!

### 🤝 Contribution Policy

* **Pull Requests**: To prevent unsolicited automated AI pull requests (AI Slop PRs) and maintain code quality, **external pull requests are not accepted** (restricted via repository settings and automation).
* **Issues**: Bug reports, book compatibility feedback, and feature requests are very welcome on **[GitHub Issues](https://github.com/KatsutoshiTsuji/Kindlead/issues)**.

### 👤 Authors

* **Katsutoshi Tsuji (Debugon)** - Concept, Architecture & Development
* **Antigravity** - Pair Programming & Implementation

### 📄 License

GNU General Public License v2 (GPL-2.0)

---

<a id="japanese"></a>
## 日本語 (Japanese)

**Kindlead** は、Kindle for PC で開いている電子書籍（特にアクセシビリティ機能が効かない固定レイアウト本や画像化された書籍）を、マルチモーダルAI（Google Gemini）を活用して**見出しツリー・目次リンク付きの完全アクセシブルなHTML電子書籍**へと自動変換する NVDA スクリーンリーダー用アドオンです。

### 🌟 主な特徴

1. **完全自動のページ巡回と画面キャプチャ**
   - 書籍の先頭から末尾まで、Kindle for PC の全画面を自動でページ送りしながら高精度にキャプチャします。
2. **Gemini Vision AI による高精度 OCR & 構造化**
   - 単なるテキスト認識にとどまらず、章題・節見出し（`h1`〜`h4`）や本文・注釈の階層構造を正確に識別します。
3. **クリック可能な目次（TOC）とページ内リンクの自動生成**
   - 冒頭に目次リストを生成し、各章・節の本文位置へワンクリック（または Enter キー）でジャンプできるようにアンカーリンクを自動マッピングします。
4. **スクリーンリーダーに親和性の高い進行通知**
   - 画面のキャプチャ時やAI解析の進捗を、作業の邪魔にならない軽快なビープ音（440Hz / 554Hz）でリアルタイムにフィードバックします。
5. **ブラウザでの即時読書**
   - 取り込みが完了すると、自動的に既定のブラウザで生成された HTML が開き、NVDA の見出しジャンプキー（`H` キーや `数字` キー）を使って快適に読書を開始できます。
6. **NVDA 設定画面での安全な API キー管理**
   - NVDA の標準設定ダイアログ内に「Kindlead」設定パネルを統合。Gemini API キーを安全に保存・管理できます。
7. **英語・日本語の多言語対応**
   - NVDAの言語設定に応じて、UI・ダイアログ・ヘルプドキュメントが英語／日本語に自動で切り替わります。

### 🚀 インストール方法

1. [Releases](https://github.com/KatsutoshiTsuji/Kindlead/releases) から最新の `Kindlead-x.x.x.nvda-addon` をダウンロードします。
2. ダウンロードしたファイルを Enter キーで開くか、NVDA のアドオンマネージャーからインストールします。
3. NVDA の再起動を促されたら、指示に従って NVDA を再起動します。

### 📖 使い方

#### 1. API キーの登録（初回のみ）
1. [Google AI Studio](https://aistudio.google.com/) で Gemini API キー（無料枠あり）を取得します。
2. `NVDA + N` を押して NVDA メニューを開き、**「設定」→「設定...」**（`NVDA + Ctrl + K`）を選択します。
3. カテゴリ一覧から **「Kindlead」** を選択します。
4. 「Gemini API キー」欄に取得したキーを貼り付け、「OK」ボタンを押します。

#### 2. 書籍の取り込みと読書
1. **Kindle for PC** を起動し、読みたい書籍を開きます。
2. 書籍の**表紙（または1ページ目）**を表示させておきます。
3. `NVDA + N` → **「ツール」** → **「Kindlead - Kindle書籍の構造化取り込み...」** を実行します。
4. ガイドダイアログが表示されるので、内容を確認して **「取り込み開始」** を選択します。
5. 自動取り込みが始まります。処理中はキーボードやマウスに触れずにお待ちください。
6. 完了すると完了ビープが鳴り、ブラウザで構造化された電子書籍が開きます！

### 🤝 コントリビューション・不具合報告方針

* **プルリクエスト（PR）について**:
  * 無秩序なAI自動生成プルリクエストの防止およびプロジェクトの品質維持のため、**外部からのプルリクエストの受付は行っておりません**（リポジトリ設定および自動処理にて制限されています）。
* **Issue（不具合報告・機能改善提案）について**:
  * 不具合報告や機能要望は **[GitHub Issues](https://github.com/KatsutoshiTsuji/Kindlead/issues)** にて歓迎しております。お気づきの点がありましたらお気軽に Issue を作成してください。

### 👤 開発者

* **辻 勝利 (Debugon)** - 企画・開発
* **Antigravity** - ペアプログラミング & アーキテクチャ実装

### 📄 ライセンス

GNU General Public License v2 (GPL-2.0)
