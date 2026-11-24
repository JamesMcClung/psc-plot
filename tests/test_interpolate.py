"""Tests for `--interpolate`, which adds a list column by lerping a field at each row's position."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pytest
import xarray as xr
from conftest import CONFIG_2D

from lib.data.adaptors import interpolate
from lib.data.data_with_attrs import Field, List
from lib.data.data_world import DataWorld
from lib.parsing.parse import parse_args
from lib.run.compile import compile_plot_pipeline


def _pull_active(argv: str):
    return compile_plot_pipeline(parse_args(argv.split()), CONFIG_2D).run_world().require_active_data()


def _field(key: str) -> xr.DataArray:
    data = _pull_active(f"pfd_moments {key} -v y z")
    assert isinstance(data, Field)
    return data.require_active_subdata().compute()


def test_matches_xarray_interp_at_clamped_positions():
    rho = _field("rho_i").isel(t=3)
    df = _pull_active("prt.i --idx t=3 --interpolate pfd_moments::rho_i -v y z").data.compute()

    y, z = (np.clip(df[dim].to_numpy(), rho[dim].min().item(), rho[dim].max().item()) for dim in ("y", "z"))
    expected = rho.interp(y=xr.DataArray(y), z=xr.DataArray(z)).to_numpy()
    np.testing.assert_allclose(df["rho_i"].to_numpy(), expected)


def test_lazy_matches_computed():
    lazy = _pull_active("prt.i --interpolate pfd_moments::rho_i -v y z").data.compute()
    computed = _pull_active("prt.i -c --interpolate pfd_moments::rho_i -v y z").data
    np.testing.assert_allclose(lazy["rho_i"].to_numpy(), computed["rho_i"].to_numpy())


def test_idx_commutes():
    before = _pull_active("prt.i --idx t=3 --interpolate pfd_moments::rho_i -v y z").data.compute()
    after = _pull_active("prt.i --interpolate pfd_moments::rho_i --idx t=3 -v y z").data.compute()
    np.testing.assert_allclose(before["rho_i"].to_numpy(), after["rho_i"].to_numpy())


@pytest.fixture
def bulk_reads(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Every adios2 bulk read, as (file name, var name)."""
    from adios2py.file import File

    reads: list[tuple[str, str]] = []
    original_read = File._read

    def recording_read(self: File, var_name: str, index):
        reads.append((Path(str(self._filename)).name, var_name))
        return original_read(self, var_name, index)

    monkeypatch.setattr(File, "_read", recording_read)
    return reads


def test_projection_reaches_the_particle_loader(bulk_reads):
    df = _pull_active("prt.i --interpolate bulk=pfd_moments::rho_i -v y z").data
    bulk_reads.clear()
    df[["py", "bulk"]].compute()
    # Every list step is on a field step, so `t` is never needed, and the field has length 1 in `x`.
    assert {var for file, var in bulk_reads if file.startswith("prt.i.")} == {"py", "y", "z"}


def test_selecting_a_step_reads_only_its_files(bulk_reads):
    df = _pull_active("prt.i --interpolate bulk=pfd_moments::rho_i --idx t=5 -v y z").data
    graph = df.optimize().__dask_graph__()
    assert sum("field-windows" in str(key) for key in graph) == 1

    bulk_reads.clear()
    df.compute()
    assert {file for file, var in bulk_reads if var == "rho_i"} == {"pfd_moments.000000005.bp"}
    assert {file for file, _ in bulk_reads if file.startswith("prt.i.")} == {"prt.i.000000005.bp"}


def test_lerps_steps_between_field_steps():
    """Shift the list half a step off the field's steps, so every window spans two field steps."""
    data = _pull_active("prt.i -v y z")
    t = data.coordss()["t"]
    half_step = (t[1] - t[0]) / 2
    shifted = data.assign(data.data.assign(t=data.data["t"] + half_step), coordss=data.coordss() | {"t": t + half_step})

    def interpolated(data):
        world = DataWorld({"prt.i": data}, "prt.i", config=CONFIG_2D)
        return interpolate.Interpolate("rho_i", "pfd_moments", "rho_i").apply_world(world).require_active_data().data

    lazy = interpolated(shifted).compute()
    eager = interpolated(shifted.compute())
    np.testing.assert_allclose(lazy["rho_i"].to_numpy(), eager["rho_i"].to_numpy())
    assert not np.allclose(lazy["rho_i"].to_numpy(), interpolated(data).compute()["rho_i"].to_numpy())


def test_bins_lazily_like_computed():
    lazy = _pull_active("prt.i --interpolate bulk=pfd_moments::rho_i --bin y=4 bulk=4 -v y bulk")
    computed = _pull_active("prt.i -c --interpolate bulk=pfd_moments::rho_i --bin y=4 bulk=4 -v y bulk")
    np.testing.assert_allclose(lazy.require_active_subdata().to_numpy(), computed.require_active_subdata().to_numpy())


def test_new_column_is_named_and_active():
    data = _pull_active("prt.i --interpolate bulk=pfd_moments::rho_i -v y z")
    assert isinstance(data, List)
    assert data.active_key == "bulk"
    assert "bulk" in data.data.columns and "rho_i" not in data.data.columns


def test_rejects_field_active_data():
    with pytest.raises(ValueError, match="list data"):
        _pull_active("pfd_moments rho_i --interpolate pfd_moments::rho_e -v y z")


@pytest.mark.parametrize("arg", ["rho_i", "bulk=rho_i", "::rho_i", "a=b=pfd_moments::rho_i"])
def test_parse_rejects(arg):
    with pytest.raises(argparse.ArgumentTypeError):
        interpolate.parse_interpolate(arg)


@pytest.mark.parametrize(
    "pos, expected",
    [
        (1.0, [1]),
        (1.0 + 1e-12, [1]),
        (1.5, [1, 2]),
        (0.0, [0]),
        (-1.0, [0]),
        (3.0, [3]),
        (4.0, [3]),
    ],
)
def test_bracket(pos, expected):
    assert interpolate._bracket(np.array([0.0, 1.0, 2.0, 3.0]), pos) == expected
