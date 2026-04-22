import importlib
from pathlib import Path

this_path = Path(__file__)

for path in this_path.parent.glob("*.py"):
    if path != this_path:
        importlib.import_module(f"{__name__}.{path.stem}")
