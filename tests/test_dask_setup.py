import sys

import dask
import pytest
from conftest import CONFIG_2D

from lib.config import PscPlotConfig
from lib.run.dask_setup import configure_dask
from lib.run.usage_error import UsageError


def test_distributed_scheduler_without_distributed_is_a_usage_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "dask.distributed", None)
    config = PscPlotConfig.create_minimal(data_root=CONFIG_2D.data_root, dask_scheduler="distributed")
    # restores the num_workers that configure_dask sets before failing
    with dask.config.set(num_workers=None), pytest.raises(UsageError, match=r"\.\[hpc\]"):
        configure_dask(config)
