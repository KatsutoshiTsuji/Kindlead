import os, sys
from pathlib import Path

tmp = Path(os.getenv('TEMP')) / 'kindlead_captures'
print("Files:", [f.name for f in sorted(tmp.glob('page_*.png'))[:10]])
