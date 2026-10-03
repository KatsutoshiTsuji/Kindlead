import re

init_path = r"D:\Katsutoshi\AntiGravity\Kindlead\addon_src\globalPlugins\kindlead\__init__.py"
with open(init_path, 'r', encoding='utf-8') as f:
    content = f.read()

target_desc = """        descText = wx.StaticText(
            self,
            label="Kindle for PCで開いている書籍を、表紙から最後のページまで完全自動で取り込みます。\\n事前にKindleで読みたい書籍を開いておいてください（途中のページでも自動で表紙に移動します）。"
        )"""

new_desc = """        descText = wx.StaticText(
            self,
            label=(
                "【取り込み前の確認事項】\\n"
                "Kindle for PCで開いている書籍を、表紙から最終ページまで全自動で取り込みます。\\n\\n"
                "● 開始後は画面最前面でKindleが自動的にページをめくります。\\n"
                "  完了するまでの数分間は、PCのキーボードやマウスに触れずにお待ちください。\\n"
                "● 進捗はビープ音（ページ撮影時: 440Hz / AI解析完了時: 554Hz）でお知らせします。\\n"
                "● 完了すると上昇和音が鳴り、デスクトップに目次リンク付きHTMLが保存されて自動で開きます。\\n"
                "● 途中で止めたい場合は、いつでも NVDA+Shift+K を押せば安全に中断できます。"
            )
        )"""

content = content.replace(target_desc, new_desc)

with open(init_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated KindleadDialog text successfully!")
