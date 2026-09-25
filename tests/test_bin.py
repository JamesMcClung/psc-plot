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
from conftest import CONFIG_2D

from lib.data.compile import compile_data_node
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
