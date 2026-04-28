"""Performance test: BP particle pipeline should be at least 2x faster than
the H5 equivalent on two-species data for a typical binning pipeline.

Uses subprocess-per-run so each pipeline is measured in a fresh interpreter
(no warm caches, no dask-cluster contamination). Synthetic data (2 species,
1M particles/step/species, 4 steps) via the tests/synthetic_particles.py
helpers."""

from __future__ import annotations

import multiprocessing as mp
import pathlib
import time

import pytest
from synthetic_particles import write_steps, write_steps_bp


def _run_h5_pipeline(data_dir: str, result_queue: mp.Queue) -> None:
    import os

    os.environ["PSC_PLOT_DATA_DIR"] = data_dir
    os.environ["PSC_PLOT_DASK_NUM_WORKERS"] = "1"
    import matplotlib

    matplotlib.use("Agg")
    from lib.parsing.args import Args
    from lib.parsing.parse import _get_parser

    parser = _get_parser()
    args = parser.parse_args("prt --species i --bin y py -v y py".split(), namespace=Args())
    plot = args.get_animation()
    t0 = time.perf_counter()
    plot._initialize()
    elapsed = time.perf_counter() - t0
    result_queue.put(elapsed)


def _run_bp_pipeline(data_dir: str, result_queue: mp.Queue) -> None:
    import os

    os.environ["PSC_PLOT_DATA_DIR"] = data_dir
    os.environ["PSC_PLOT_DASK_NUM_WORKERS"] = "1"
    import matplotlib

    matplotlib.use("Agg")
    from lib.parsing.args import Args
    from lib.parsing.parse import _get_parser

    parser = _get_parser()
    args = parser.parse_args("prt.i --bin y py -v y py".split(), namespace=Args())
    plot = args.get_animation()
    t0 = time.perf_counter()
    plot._initialize()
    elapsed = time.perf_counter() - t0
    result_queue.put(elapsed)


def _measure(target, data_dir: pathlib.Path) -> float:
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    proc = ctx.Process(target=target, args=(str(data_dir), queue))
    proc.start()
    proc.join(timeout=300)
    if proc.exitcode != 0:
        pytest.fail(f"child process exited with code {proc.exitcode}")
    return queue.get(timeout=5)


@pytest.fixture(scope="module")
def synthetic_two_species_dir(tmp_path_factory):
    """Write 4 steps of 2-species synthetic data in BOTH H5 and BP formats
    into the same dir so both pipelines can run without re-writing."""
    data_dir = tmp_path_factory.mktemp("prt-perf")
    steps = [0, 1, 2, 3]
    times = [0.0, 1.0, 2.0, 3.0]
    write_steps(data_dir, steps=steps, times=times, n_particles_per_step=2_000_000)
    write_steps_bp(
        data_dir,
        steps=steps,
        times=times,
        species=[("i", 1.0, 100.0, 1_000_000), ("e", -1.0, 1.0, 1_000_000)],
    )
    return data_dir


def test_bp_pipeline_faster_than_h5(synthetic_two_species_dir):
    """BP should be at least 2x faster than H5 on a binning pipeline for
    two-species data (BP reads half the particles; lighter serialization)."""
    h5_time = _measure(_run_h5_pipeline, synthetic_two_species_dir)
    bp_time = _measure(_run_bp_pipeline, synthetic_two_species_dir)
    ratio = bp_time / h5_time
    assert ratio < 0.5, f"expected BP to be >2x faster than H5, but ratio is {ratio:.2f} (bp={bp_time:.2f}s, h5={h5_time:.2f}s)"
