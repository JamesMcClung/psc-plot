"""Tests for the --bin adaptor on particle (List) data.

Two properties matter here beyond plain correctness:

1. `--bin` must cope with dims whose coord has been reduced to a scalar by an
   earlier `--idx t=<int>`; such a dim holds a single value and so is not a
   histogram dim at all.
2. `--bin` must not build a dense `prod(nbins)` histogram per dataframe
   partition. Partitions are t-aligned, so the t axis is added by stacking
   per-step histograms. `test_binned_values_match_numpy` pins the numerics of
   that construction against a plain numpy histogram of the same data.
"""

from __future__ import annotations

import numpy as np
import pytest
from conftest import CONFIG_2D

from lib.data.compile import compile_data_node, compile_plot_node
from lib.data.data_with_attrs import Field, List
from lib.parsing.parse import parse_args


def _pull_world(argv: str):
    return compile_data_node(parse_args(argv.split()), CONFIG_2D).pull()


def _pull_active(argv: str):
    return _pull_world(argv).require_active_data()


def test_bin_after_idx_int_on_time():
    """`-i t=-1` leaves t as a scalar coord; binning must treat it as a single
    value, not try to len() it."""
    data = _pull_active("prt.i -i t=-1 --bin y=8 py=16 -v y py")

    assert isinstance(data, Field)
    da = data.require_active_subdata()
    assert set(da.dims) == {"y", "py"}, f"expected only the binned dims, got {da.dims}"
    assert da.coords["t"].shape == (), "t should stay a scalar coord after --idx t=-1"


def test_idx_slice_keeps_partition_ranges_consistent():
    """After partition pruning, partition_ranges must index the pruned frame and
    stay aligned with the surviving coords."""
    data = _pull_active("prt.i -i t=0:3 -v y z")

    assert isinstance(data, List)
    md = data.metadata
    assert md.partition_dim == "t"
    assert md.partition_ranges is not None
    assert len(md.partition_ranges) == len(md.coordss["t"]) == 3
    assert md.partition_ranges[0][0] == 0, f"ranges must be rebased onto the pruned frame, got {md.partition_ranges}"
    assert md.partition_ranges[-1][1] == data.data.npartitions, f"ranges must cover the pruned frame's {data.data.npartitions} partitions, got {md.partition_ranges}"


def test_idx_int_on_partition_dim_clears_partition_metadata():
    """An int index collapses the partition dim to a single value, so it is no
    longer a dim partitions are laid out along."""
    data = _pull_active("prt.i -i t=-1 -v y z")

    assert isinstance(data, List)
    assert data.metadata.partition_dim is None
    assert data.metadata.partition_ranges is None


def test_binned_values_match_numpy():
    """The stacked per-step histogram must equal a single dense histogram of the
    same columns, weights included."""
    listdata = _pull_active("prt.i -v y py")
    assert isinstance(listdata, List)
    df = listdata.data.compute()
    times = listdata.metadata.coordss["t"]

    binned = _pull_active("prt.i --bin y=8 py=16 -v y py").require_active_subdata()

    y_edges = np.asarray(binned.coords["y"])
    py_edges = np.asarray(binned.coords["py"])
    # coords are left edges; rebuild the full edge arrays
    y_full = np.append(y_edges, 2 * y_edges[-1] - y_edges[-2])
    py_full = np.append(py_edges, 2 * py_edges[-1] - py_edges[-2])
    t_full = np.append(times, np.inf)

    expected, _ = np.histogramdd(
        [df["y"].to_numpy(), df["py"].to_numpy(), df["t"].to_numpy()],
        [y_full, py_full, t_full],
        weights=df["w"].to_numpy(),
    )

    actual = np.asarray(binned.transpose("y", "py", "t"))
    np.testing.assert_allclose(actual, expected, rtol=1e-6)


@pytest.fixture
def histogram_calls(monkeypatch: pytest.MonkeyPatch):
    """Records the per-partition bin shape of every histogram kernel call.

    `dask.array.histogramdd` allocates one dense `prod(nbins)` array per
    dataframe partition, so this is the allocation that used to blow up.
    """
    shapes: list[tuple[int, ...]] = []
    original = np.histogramdd

    def recording_histogramdd(sample, bins=None, **kwargs):
        shapes.append(tuple(len(np.asarray(edges)) - 1 for edges in bins))
        return original(sample, bins, **kwargs)

    monkeypatch.setattr(np, "histogramdd", recording_histogramdd)
    return shapes


def test_time_axis_is_not_part_of_the_per_partition_histogram(histogram_calls):
    """Each partition holds one timestep, so histogramming t per partition would
    allocate the whole y-by-py-by-t grid to write one t slice of it."""
    compile_plot_node(parse_args("prt.i --bin y=8 py=16 -v y py -q".split()), CONFIG_2D).pull()._initialize()

    assert histogram_calls, "expected the binning pipeline to run the histogram kernel"
    oversized = {shape for shape in histogram_calls if shape != (8, 16)}
    assert not oversized, f"per-partition histograms must cover only the non-time bins (8, 16); got {sorted(oversized)}"


def test_particle_files_are_histogrammed_once(histogram_calls):
    """The binned grid is materialized at --bin, so neither the color bounds nor
    the animation frames may re-run the histogram over the particle files."""
    node = compile_plot_node(parse_args("prt.i --bin y=8 py=16 -v y py -q".split()), CONFIG_2D)
    plot = node.pull()
    plot._initialize()
    after_initialize = len(histogram_calls)

    for frame in range(plot.n_frames):
        for renderer in plot.renderers:
            renderer.update_plot_info(frame)
            np.asarray(renderer.plot_info.data)

    n_partitions = len(_pull_active("prt.i -v y py").metadata.partition_ranges)
    assert after_initialize == n_partitions, f"expected one histogram call per partition ({n_partitions}), got {after_initialize}"
    assert len(histogram_calls) == after_initialize, f"drawing {plot.n_frames} frames re-ran the histogram {len(histogram_calls) - after_initialize} times"


@pytest.mark.parametrize("n_t_bins", [3, 11, 25])
def test_explicit_time_bins_match_numpy(n_t_bins):
    """An explicit --bin t=<n> makes t bins that don't correspond 1:1 to steps:
    coarser bins sum several steps together, finer ones leave bins empty."""
    listdata = _pull_active("prt.i -v y py")
    assert isinstance(listdata, List)
    df = listdata.data.compute()

    binned = _pull_active(f"prt.i --bin y=8 py=16 t={n_t_bins} -v y py").require_active_subdata()
    assert binned.sizes["t"] == n_t_bins

    edgess = []
    for dim in ("y", "py", "t"):
        left = np.asarray(binned.coords[dim])
        edgess.append(np.append(left, 2 * left[-1] - left[-2]))

    expected, _ = np.histogramdd(
        [df["y"].to_numpy(), df["py"].to_numpy(), df["t"].to_numpy()],
        edgess,
        weights=df["w"].to_numpy(),
    )

    np.testing.assert_allclose(np.asarray(binned.transpose("y", "py", "t")), expected, rtol=1e-6)
