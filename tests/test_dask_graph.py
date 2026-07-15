"""Regression tests for the structure of the dask graph produced by the particle
pipeline. The pipeline's downstream selects a small subset of columns; the
column-projection optimization in dask-expr should propagate that selection all
the way down to the per-file reads, so unused columns are never read from disk.

These tests inspect the *optimized* expression tree and assert that read tasks
for unwanted columns are absent. They guard against regressions where an opaque
operation (e.g. an inline `map_partitions(lambda)`) blocks projection pushdown,
silently causing dead loads of every column in every file.
"""

from conftest import _DATA_DIR

from lib.config import CONFIG
from lib.data.compile import compile_plot_node
from lib.parsing.parse import parse_args


def _read_keys_for_columns(args_list: list[str], data_dir: str = "test-2d") -> list[str]:
    """Optimize each dask collection produced by `args_list` and return
    the set of per-column file-read task key strings in the optimized graph."""
    original = CONFIG.data_dir
    CONFIG.data_dir = _DATA_DIR / data_dir
    try:
        args = parse_args(args_list)
        node = compile_plot_node(args)
        data = node.input_node.pull().active_data
        collections = data.dask_collections()
        assert collections, "expected particle pipeline to be dask-backed"
        read_keys: list[str] = []
        for c in collections:
            opt = c.optimize() if hasattr(c, "optimize") else c
            for k in opt.__dask_graph__():
                key = k[0] if isinstance(k, tuple) else k
                if isinstance(key, str) and "open_dataset" in key:
                    read_keys.append(key)
        return read_keys
    finally:
        CONFIG.data_dir = original


def test_particle_load_projects_columns_to_reads():
    """`prt.i -v y py` only needs y and py; the optimized graph must not
    contain read tasks for px, pz, w, x, or z."""
    read_keys = _read_keys_for_columns(["prt.i", "-v", "y", "py", "-q"])
    unwanted = ["px", "pz", "w", "x", "z"]
    leaked = sorted({c for c in unwanted if any(f"-{c}-" in k for k in read_keys)})
    assert not leaked, f"unprojected columns still being read from disk: {leaked}"


def test_particle_load_projects_columns_in_binned_pipeline():
    """`--bin y py=16 -v y py` only needs y, py, and the weight column. The
    optimized graph must not contain read tasks for px, pz, x, or z."""
    read_keys = _read_keys_for_columns(["prt.i", "--bin", "y", "py=16", "-v", "y", "py", "-q"])
    unwanted = ["px", "pz", "x", "z"]
    leaked = sorted({c for c in unwanted if any(f"-{c}-" in k for k in read_keys)})
    assert not leaked, f"unprojected columns still being read from disk: {leaked}"
