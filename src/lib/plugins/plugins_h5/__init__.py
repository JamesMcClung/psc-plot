import importlib
from pathlib import Path

this_file = Path(__file__)
module_paths = [path for path in this_file.parent.glob("*.py") if path != this_file]
modules = [path.stem for path in module_paths]

for module in modules:
    importlib.import_module(f"lib.plugins.plugins_h5.{module}")
