"""Memory tests for the particle binning pipeline.

Two properties, each measured by running the pipeline in its own subprocess so
ru_maxrss readings are clean:

- a smaller PSC_PLOT_DASK_CHUNK_SIZE reduces peak memory;
- peak memory does not grow with the number of timesteps beyond the binned grid
  itself. This is the cluster _ArrayMemoryError in miniature: the failure was
  driven by bins x partitions in flight and was independent of particle count,
  so a few hundred KiB of data over many steps reproduces it.
"""

from __future__ import annotations

import multiprocessing as mp
import pathlib
import resource
import sys

import pytest
from synthetic_particles import write_steps

from lib.config import PscPlotConfig

_DEFAULT_ARGV = "prt --species i --bin y py=16 -v y py"


def _run_pipeline(data_dir: pathlib.Path, chunksize: int, argv: str, result_queue: mp.Queue) -> None:
    """Child-process entry point: configure env, run the pipeline, report ru_maxrss."""
    import matplotlib

    matplotlib.use("Agg")

    from lib.data.compile import compile_plot_node
    from lib.parsing.parse import parse_args

    args = parse_args(argv.split())
    plot = compile_plot_node(args, PscPlotConfig(data_root=data_dir, dask_chunk_size=chunksize)).pull()
    plot._initialize()

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result_queue.put(peak)


def _measure(data_dir: pathlib.Path, chunksize: int, argv: str = _DEFAULT_ARGV) -> int:
    """Run _run_pipeline in a child and return the reported peak ru_maxrss."""
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    proc = ctx.Process(target=_run_pipeline, args=(data_dir, chunksize, argv, queue))
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


# ru_maxrss is bytes on darwin and KiB elsewhere; the ratio test above doesn't care, the budget test below does.
_RU_MAXRSS_UNIT = 1 if sys.platform == "darwin" else 1024


_N_Y_BINS = 512
_N_PY_BINS = 256
_FEW_STEPS = 4
_MANY_STEPS = 64
# One t slice of the binned grid, i.e. what each added step legitimately adds to
# the resident result. float64 is the widest dtype the histogram can produce.
_GRID_SLICE_BYTES = _N_Y_BINS * _N_PY_BINS * 8


@pytest.fixture(scope="module")
def many_step_data_dirs(tmp_path_factory):
    """Two datasets differing only in timestep count, each with a negligible
    number of particles so that peak memory reflects bins, not data."""
    dirs = {}
    for n_steps in (_FEW_STEPS, _MANY_STEPS):
        data_dir = tmp_path_factory.mktemp(f"prt-steps-{n_steps}")
        write_steps(
            data_dir,
            steps=list(range(n_steps)),
            times=[float(step) for step in range(n_steps)],
            n_particles_per_step=200,
        )
        dirs[n_steps] = data_dir
    return dirs


def test_peak_memory_does_not_grow_with_timestep_count(many_step_data_dirs):
    """Binning must not allocate a dense (y, py, t) histogram per partition.

    When it did, peak memory grew by ~10 slices of the binned grid per timestep
    (measured: 336 MiB at 4 steps to 1433 MiB at 120, on 3 MB of data), which is
    what made real runs die with numpy's _ArrayMemoryError. The floor is the
    result itself, which grows by one slice per step.
    """
    argv = f"prt --species i --bin y={_N_Y_BINS} py={_N_PY_BINS} -v y py"
    few_peak = _measure(many_step_data_dirs[_FEW_STEPS], chunksize=1_000_000, argv=argv)
    many_peak = _measure(many_step_data_dirs[_MANY_STEPS], chunksize=1_000_000, argv=argv)

    growth_per_step = (many_peak - few_peak) * _RU_MAXRSS_UNIT / (_MANY_STEPS - _FEW_STEPS)
    budget = 5 * _GRID_SLICE_BYTES
    assert growth_per_step < budget, f"peak memory grew {growth_per_step / 2**20:.1f} MiB per timestep; budget is {budget / 2**20:.1f} MiB (one grid slice is {_GRID_SLICE_BYTES / 2**20:.1f} MiB). few={few_peak}, many={many_peak}"
