import sys
import types

from lib.suggest.candidates import candidate_schedulers, guess_scheduler


def test_without_distributed(monkeypatch):
    monkeypatch.setitem(sys.modules, "dask.distributed", None)
    assert candidate_schedulers() == ["threads", "processes"]
    assert guess_scheduler(8) == "threads"


def test_with_distributed(monkeypatch):
    monkeypatch.setitem(sys.modules, "dask.distributed", types.ModuleType("dask.distributed"))
    assert candidate_schedulers() == ["threads", "processes", "distributed"]
    assert guess_scheduler(8) == "distributed"
    assert guess_scheduler(1) == "threads"
