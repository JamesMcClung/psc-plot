import runpy
from pathlib import Path

from lib import cli

_MAIN = Path(__file__).parent.parent / "src" / "main.py"


def test_spawned_children_do_not_rerun_main(monkeypatch):
    # multiprocessing's spawn re-imports the main script as __mp_main__; running main() there would recurse into --suggest-config's trials
    def fail():
        raise AssertionError("main() ran on import")

    monkeypatch.setattr(cli, "main", fail)
    runpy.run_path(str(_MAIN), run_name="__mp_main__")
