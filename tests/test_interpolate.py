"""Tests for `--interpolate`, which adds a list column by lerping a field at each row's position."""

from __future__ import annotations

import argparse

import numpy as np
import pytest
import xarray as xr
from conftest import CONFIG_2D

from lib.data.adaptors import interpolate
from lib.data.data_with_attrs import Field, List
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


def test_selecting_a_step_interpolates_only_its_partitions(monkeypatch):
    calls = []
    with_column = interpolate._with_column

    def spy(df, *args):
        calls.append(len(df))
        return with_column(df, *args)

    monkeypatch.setattr(interpolate, "_with_column", spy)
    data = _pull_active("prt.i --interpolate pfd_moments::rho_i --idx t=5 -v y z")
    data.data.compute()
    assert len(calls) == 1


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
