# Kindlead 開発ロードマップ & ネクストアクション

## Issue #1: NVDA 見出しレベル 7〜9 を活用した高度なセマンティック構造化 (v1.2.0 実装完了 ✅)
* **GitHub Issue**: https://github.com/KatsutoshiTsuji/Kindlead/issues/1
* **ステータス**: 実装完了 (v1.2.0)
* **概要**: 近年の NVDA でサポートされた「見出しレベル 1〜9 の単打ジャンプ（キー 1〜9）」をフル活用し、書籍内の注釈・コラム・図表キャプションを通常の本文と明確に分離・構造化。
* **割り当て設計**:
  * 見出しレベル 1〜3 (`h1`〜`h3`): 書籍の骨格（部・章・節）
  * 見出しレベル 4〜5 (`h4`〜`h5`): 小見出し・小節・段落見出し
  * 見出しレベル 7 (`role="heading" aria-level="7"`): コラム・囲み記事・トピックス（NVDAキー `7` でジャンプ）
  * 見出しレベル 8 (`role="heading" aria-level="8"`): 注釈・脚注・割注（NVDAキー `8` でジャンプ）＋ 本文と脚注の双方向アンカーリンク自動結線
  * 見出しレベル 9 (`role="heading" aria-level="9"`): 図表キャプション・グラフ解説（NVDAキー `9` でジャンプ）
* **対応内容**:
  * Gemini解析プロンプトの拡充（コラム・注釈・図表のセマンティック抽出指示）
  * `compile_accessible_html` による見出しレベル7〜9の正規化および注釈双方向アンカーリンク自動結線
  * NVDAフォーカス可視化および各セマンティックブロックのCSSスタイリング拡充

---

## Issue #2: CJK多言語対応（中国語簡体字 zh_CN、繁体字 zh_TW、韓国語 ko）の追加 (v1.2.0 実装完了 ✅)
* **GitHub Issue**: https://github.com/KatsutoshiTsuji/Kindlead/issues/2
* **ステータス**: 実装完了 (v1.2.0)
* **概要**: CJK（日中韓・台湾）文化圏のスクリーンリーダーユーザーに向けて、Kindleadの多言語対応を拡充。
* **背景**:
  * Kindleの固定レイアウト本や画像化された書籍のアクセシビリティ課題はアジア圏全域で共通。
  * 特に台湾（繁体字）は日本と同様に縦書き・右開きの書籍文化を持ち、NVDAコミュニティ（淡江大学等）の活動も非常に活発。
  * NVDAのgettext多言語化アーキテクチャを活用し、UI・メニュー・メッセージを完全ローカライズ。
* **対象言語**:
  * `zh_TW` (Chinese Traditional / 繁體中文)
  * `zh_CN` (Chinese Simplified / 简体中文)
  * `ko` (Korean / 한국어)
* **対応内容**:
  1. 各言語の翻訳カタログ（`addon_src/locale/{zh_TW,zh_CN,ko}/LC_MESSAGES/nvda.po`）の作成（全38エントリ）
  2. `build_addon.py` による自動 `.mo` バイナリコンパイル
  3. 各言語用ヘルプドキュメント（`doc/{zh_TW,zh_CN,ko}/readme.html`）の作成
  4. リポジトリ `README.md` の多言語リンク・概要セクション更新

---
最終更新日: 2026-10-11 (辻 勝利 & Antigravity)
