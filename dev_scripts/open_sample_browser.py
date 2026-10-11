import sys
import webbrowser
from pathlib import Path

# アドオンモジュールのロード
sys.path.insert(0, str(Path("addon_src/globalPlugins/kindlead").resolve()))
from engine import compile_accessible_html

# サンプルデータ
sample_results = [
    {
        "page": 1,
        "markdown": """# 素晴らしいアクセシビリティの世界

著者: 辻 勝利

## 第1章 NVDAと読書革新

スクリーンリーダーでの読書体験は年々進化しています※1。
特に見出しジャンプ機能は極めて重要です[2]。

<aside role="region" aria-label="コラム" class="kindlead-column">
  <div role="heading" aria-level="7" class="column-title">コラム：見出しジャンプの歴史</div>
  NVDAでは古くからHキーによる見出しジャンプがサポートされていましたが、近年は1〜9の数字キーによるレベル別単打ジャンプが利用可能になりました。
</aside>

本文の続きです。ここにも図表の解説が入ります。

<figure class="kindlead-figure">
  <figcaption role="heading" aria-level="9" class="figure-caption">図1-1 読書効率の向上グラフ</figcaption>
  従来の全文読み上げと比較して、見出しナビゲーションを用いた場合の読書速度が3倍に向上したことを示すグラフ。
</figure>

※1 NVDA日本語版の普及により、日本国内の視覚障害者の情報アクセス環境は劇的に改善された。
[2] スクリーンリーダーの単打ナビゲーションキー（Quick Navigation）のこと。"""
    }
]

out_dir = Path("dev_scripts/sample_preview")
out_file, title = compile_accessible_html(
    sample_results,
    image_count=1,
    t_cap=0.4,
    t_api=1.1,
    output_dir=out_dir
)

print(f"Sample HTML generated at: {out_file.resolve()}")
webbrowser.open(out_file.resolve().as_uri())
print("Browser opened successfully!")
