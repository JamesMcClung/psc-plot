from pathlib import Path

import pytest

from lib.config import PscPlotConfig

# --- create_minimal ---


def test_create_minimal():
    config = PscPlotConfig.create_minimal()
    assert config.data_root == Path.cwd()
    assert config.ffmpeg_bin is None
    assert (config.dask_scheduler, config.dask_num_workers, config.dask_chunk_size) == ("synchronous", 1, 1_000_000)
    assert (config.registries_use_defaults, config.registry_patterns) == (True, [])


def test_create_minimal_overrides():
    config = PscPlotConfig.create_minimal(data_root=Path("/data"), dask_num_workers=4)
    assert (config.data_root, config.dask_num_workers, config.dask_scheduler) == (Path("/data"), 4, "synchronous")


def test_fields_have_no_defaults():
    with pytest.raises(TypeError):
        PscPlotConfig(data_root=Path("."))
