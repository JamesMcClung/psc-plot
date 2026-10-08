import datetime
from pathlib import Path

import yaml

from lib.config import CONFIG_KEYS, CONFIG_PATH_KEY, PscPlotConfig
from lib.profiling.profiler import StageRecord
from lib.profiling.worker_count import WorkerCount
from lib.suggest.suggestion import ConfigSuggestion, Measurement, fastest
from lib.suggest.trial import TrialFailure, TrialRun

_CONFIG = PscPlotConfig.create_minimal(data_root=Path("/data"), ffmpeg_bin=Path("/usr/bin/ffmpeg"), dask_chunk_size=500)
_WORKERS = WorkerCount(28, "NCPUS", "min of NCPUS=28, affinity=56, physical=28")
_DATE = datetime.date(2026, 10, 7)
_TRIALS = {
    "threads": TrialRun(StageRecord("total", 41.2, 44.0, 3 * 2**30), 201, 6, 5.0),
    "processes": TrialFailure("exited with code -9"),
    "distributed": TrialRun(StageRecord("total", 13.1, 118.9, 10 * 2**30), 201, 6, 2.5),
}


def test_fastest_ignores_failures():
    assert fastest(_TRIALS) == "distributed"
    assert fastest({"threads": TrialFailure("boom")}) is None


def test_fastest_ranks_by_projected_wall():
    # slower over the 6 rendered frames, faster over all 100
    slow_start = TrialRun(StageRecord("total", 16.0, 16.0, 0), 100, 6, 5.0)
    fast_start = TrialRun(StageRecord("total", 13.0, 13.0, 0), 100, 6, 10.0)
    assert fastest({"threads": fast_start, "processes": slow_start}) == "processes"


def test_format_yaml_without_measurement():
    suggestion = ConfigSuggestion("node1", _DATE, _WORKERS, "distributed", _CONFIG, None)
    assert suggestion.format_yaml() == (
        "# psc-plot --suggest-config on node1, 2026-10-07\n"
        "# an environment-based guess; to measure, rerun with a representative pipeline: psc-plot <prepath> [var] [adaptors...] --suggest-config\n"
        "PSC_PLOT_DATA_DIR: .  # set per job: export PSC_PLOT_DATA_DIR=...\n"
        "PSC_PLOT_FFMPEG_BIN: /usr/bin/ffmpeg\n"
        "PSC_PLOT_DASK_SCHEDULER: distributed  # environment-based guess\n"
        "PSC_PLOT_DASK_NUM_WORKERS: $NCPUS  # = 28 here; min of NCPUS=28, affinity=56, physical=28\n"
        "PSC_PLOT_DASK_CHUNK_SIZE: 500\n"
        "PSC_PLOT_REGISTRIES_USE_DEFAULTS: true\n"
        "PSC_PLOT_REGISTRIES: []\n"
    )


def test_format_yaml_with_measurement():
    measurement = Measurement("pfd_moments jy_e --bin x", 6, 201, _TRIALS)
    suggestion = ConfigSuggestion("node1", _DATE, WorkerCount(32, None, "min of NSLOTS=64, physical=32"), "distributed", _CONFIG, measurement)
    assert suggestion.format_yaml() == (
        "# psc-plot --suggest-config on node1, 2026-10-07\n"
        "# measured: pfd_moments jy_e --bin x  (6 of 201 frames, after a warm-up run)\n"
        "# projected: all 201 frames, each unrendered one at the mean wall of frames 2-6\n"
        "#   scheduler        wall  projected      cpu  cores  peak rss\n"
        "#   threads         41.2s     236.2s    44.0s    1.1    3.0 GB\n"
        "#   processes   failed: exited with code -9\n"
        "# * distributed     13.1s     110.6s   118.9s    9.1   10.0 GB\n"
        "PSC_PLOT_DATA_DIR: .  # set per job: export PSC_PLOT_DATA_DIR=...\n"
        "PSC_PLOT_FFMPEG_BIN: /usr/bin/ffmpeg\n"
        "PSC_PLOT_DASK_SCHEDULER: distributed  # least projected wall of 3 trials\n"
        "PSC_PLOT_DASK_NUM_WORKERS: 32  # min of NSLOTS=64, physical=32\n"
        "PSC_PLOT_DASK_CHUNK_SIZE: 500\n"
        "PSC_PLOT_REGISTRIES_USE_DEFAULTS: true\n"
        "PSC_PLOT_REGISTRIES: []\n"
    )


def test_format_yaml_loads_as_a_config_file(tmp_path, monkeypatch):
    suggestion = ConfigSuggestion("node1", _DATE, _WORKERS, "processes", _CONFIG, Measurement("pfd hx_fc", 6, 11, _TRIALS))
    path = tmp_path / "config.yml"
    path.write_text(suggestion.format_yaml())
    for key in CONFIG_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(CONFIG_PATH_KEY, str(path))
    monkeypatch.setenv("NCPUS", "28")
    loaded = PscPlotConfig.from_env()
    assert loaded.data_root == Path(".")
    assert loaded.dask_scheduler == "processes"
    assert loaded.dask_num_workers == 28
    assert loaded.dask_chunk_size == 500


def test_multi_line_failure_reason_stays_in_the_comments():
    trials = {"threads": TrialFailure("ValueError: bad\nkey: oops\n  more"), "processes": _TRIALS["distributed"]}
    suggestion = ConfigSuggestion("node1", _DATE, _WORKERS, "processes", _CONFIG, Measurement("pfd hx_fc", 6, 11, trials))
    assert "#   threads     failed: ValueError: bad key: oops more\n" in suggestion.format_yaml()
    assert set(yaml.safe_load(suggestion.format_yaml())) == set(CONFIG_KEYS)
