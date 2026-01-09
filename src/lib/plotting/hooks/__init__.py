# Import each other file in this directory, which may not be imported otherwise.
# Each file is then responsible for registering its content with argparse.
# This file is itself explicitly imported in lib/__init__.py.

import importlib
from pathlib import Path

this_path = Path(__file__)

for path in this_path.parent.glob("*.py"):
    if path != this_path:
        importlib.import_module(f"{__name__}.{path.stem}")
