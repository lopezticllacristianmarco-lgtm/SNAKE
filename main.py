"""Entry point: run the game directly, with or without pip install.

`python main.py` inserts `./src` on sys.path so the `snake_game` package
resolves without an install (this is also what Android/buildozer runs).
"""

import os
import sys

_RUTA_RAIZ = os.path.dirname(os.path.abspath(__file__))
_RUTA_SRC = os.path.join(_RUTA_RAIZ, "src")
if _RUTA_SRC not in sys.path:
    sys.path.insert(0, _RUTA_SRC)

from snake_game.app import main  # noqa: E402

if __name__ == "__main__":
    main()