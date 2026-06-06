"""CortexFlow 套件入口 — python -m cortexflow。"""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from main import main  # noqa: E402

main()
