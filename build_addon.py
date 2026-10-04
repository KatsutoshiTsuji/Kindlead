import zipfile
import struct
import re
from pathlib import Path

def parse_po(po_path):
    """Simple PO file parser supporting multiline strings"""
    entries = {}
    current_msgid = None
    current_msgstr = None
    state = None
    
    with open(po_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('msgid '):
                if current_msgid is not None and current_msgstr is not None:
                    entries[current_msgid] = current_msgstr
                current_msgid = eval(line[6:])
                current_msgstr = None
                state = 'msgid'
            elif line.startswith('msgstr '):
                current_msgstr = eval(line[7:])
                state = 'msgstr'
            elif line.startswith('"') and line.endswith('"'):
                s = eval(line)
                if state == 'msgid':
                    current_msgid += s
                elif state == 'msgstr':
                    current_msgstr += s
                    
    if current_msgid is not None and current_msgstr is not None:
        entries[current_msgid] = current_msgstr
        
    return entries

def compile_po_to_mo(po_entries):
    """Compile dictionary of msgid->msgstr into binary GNU gettext .mo format"""
    items = sorted(po_entries.items())
    keys = [k.encode('utf-8') for k, v in items]
    vals = [v.encode('utf-8') for k, v in items]
    
    N = len(items)
    orig_table_offset = 28
    trans_table_offset = orig_table_offset + N * 8
    str_offset = trans_table_offset + N * 8
    
    orig_entries = []
    trans_entries = []
    
    data_orig = bytearray()
    for k in keys:
        orig_entries.append((len(k), str_offset + len(data_orig)))
        data_orig.extend(k + b'\x00')
        
    data_trans = bytearray()
    for v in vals:
        trans_entries.append((len(v), str_offset + len(data_orig) + len(data_trans)))
        data_trans.extend(v + b'\x00')
        
    header = struct.pack(
        '<Iiiiiii',
        0x950412de, # Magic
        0,          # Version
        N,          # Number of strings
        orig_table_offset,
        trans_table_offset,
        0,          # Hash table size
        0           # Hash table offset
    )
    
    table_orig = bytearray()
    for length, offset in orig_entries:
        table_orig.extend(struct.pack('<ii', length, offset))
        
    table_trans = bytearray()
    for length, offset in trans_entries:
        table_trans.extend(struct.pack('<ii', length, offset))
        
    return header + table_orig + table_trans + data_orig + data_trans

def build():
    base_dir = Path(__file__).parent
    src_dir = base_dir / "addon_src"
    manifest_path = src_dir / "manifest.ini"

    # バージョン取得
    version = "1.0.0"
    if manifest_path.exists():
        content = manifest_path.read_text(encoding="utf-8")
        m = re.search(r"^version\s*=\s*(.+)$", content, re.MULTILINE)
        if m:
            version = m.group(1).strip().strip('"').strip("'")

    # 1. すべての .po ファイルを .mo に自動コンパイル
    for po_file in src_dir.rglob("*.po"):
        mo_file = po_file.with_suffix(".mo")
        entries = parse_po(po_file)
        mo_bytes = compile_po_to_mo(entries)
        mo_file.write_bytes(mo_bytes)
        print(f"[i18n] コンパイル完了: {po_file.name} -> {mo_file.name} ({len(entries)} 翻訳エントリ)")

    # 2. アドオン zip (.nvda-addon) パッケージの作成
    output_addon = base_dir / f"Kindlead-{version}.nvda-addon"
    with zipfile.ZipFile(output_addon, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in src_dir.rglob('*'):
            if file.is_file():
                # 不要なキャッシュは除外
                if "__pycache__" in file.parts or file.suffix == ".pyc":
                    continue
                arcname = file.relative_to(src_dir)
                zf.write(file, arcname)

    print(f"アドオンのビルドが完了しました: {output_addon.name} (サイズ: {output_addon.stat().st_size:,} bytes)")

if __name__ == "__main__":
    build()
