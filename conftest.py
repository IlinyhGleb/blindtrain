import sys
from pathlib import Path

_here = Path(__file__).parent

for candidate in (_here, _here / "blindtrain"):
    if (candidate / "app.py").is_file() and (candidate / "lessons.py").is_file():
        sys.path.insert(0, str(candidate))
        break
