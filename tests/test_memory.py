"""Memory-bounded-by-chunksize test.

Proves that setting PSC_PLOT_DASK_CHUNK_SIZE to a small value reduces peak
memory during a particle binning pipeline. Runs each pipeline in its own
subprocess so ru_maxrss readings are clean.
"""

from __future__ import annotations

import multiprocessing as mp
import pathlib
import resource

import pytest
from synthetic_particles import write_steps


def _run_pipeline(data_dir: str, chunksize: int, result_queue: mp.Queue) -> None:
    """Child-process entry point: configure env, run the pipeline, report ru_maxrss."""
    import os

    os.environ["PSC_PLOT_DATA_DIR"] = data_dir
    os.environ["PSC_PLOT_DASK_NUM_WORKERS"] = "1"
    os.environ["PSC_PLOT_DASK_CHUNK_SIZE"] = str(chunksize)

    import matplotlib

    matplotlib.use("Agg")

    from lib.parsing.args import Args
    from lib.parsing.parse import _get_parser

    parser = _get_parser()
    args = parser.parse_args(
        "prt --species i --bin y py=16 -v y py".split(),
        namespace=Args(),
    )
    plot = args.get_animation()
    plot._initialize()

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result_queue.put(peak)


def _measure(data_dir: pathlib.Path, chunksize: int) -> int:
    """Run _run_pipeline in a child and return the reported peak ru_maxrss."""
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    proc = ctx.Process(target=_run_pipeline, args=(str(data_dir), chunksize, queue))
    proc.start()
    proc.join(timeout=120)
    if proc.exitcode != 0:
        pytest.fail(f"child process exited with code {proc.exitcode}")
    return queue.get(timeout=5)


@pytest.fixture(scope="module")
def synthetic_data_dir(tmp_path_factory):
    """Write 4 timesteps × 1M particles (~220MB total) once per module."""
    data_dir = tmp_path_factory.mktemp("prt-mem")
    write_steps(
        data_dir,
        steps=[0, 1, 2, 3],
        times=[0.0, 1.0, 2.0, 3.0],
        n_particles_per_step=1_000_000,
    )
    return data_dir


def test_smaller_chunksize_reduces_peak_memory(synthetic_data_dir):
    """Running with a chunksize that forces many partitions should peak lower than running with chunksize large enough to swallow a whole step."""
    # 10M dwarfs 1M particles/step → 1 partition per step
    large_peak = _measure(synthetic_data_dir, chunksize=10_000_000)
    # 100K → ~10 partitions per step, 40 partitions total
    small_peak = _measure(synthetic_data_dir, chunksize=100_000)

    # Small-chunk run should use less than 75% of the large-chunk run's peak.
    # If dask is streaming properly, the ratio should be substantially lower than this;
    # 75% is a loose bound that still clearly distinguishes streaming from non-streaming.
    ratio = small_peak / large_peak
    assert ratio < 0.75, f"expected small chunksize to reduce peak memory, but ratio is {ratio:.2f} (small={small_peak}, large={large_peak})"
