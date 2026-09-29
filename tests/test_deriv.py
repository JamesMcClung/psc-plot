import numpy as np
import pytest
import xarray as xr
from conftest import CONFIG_2D

from lib.data.adaptors.deriv import parse_deriv
from lib.data.adaptors.diff import Diff, _Diff1d, parse, parse_diffs_1d
from lib.data.loader import load


def _pfd_hy():
    return load(CONFIG_2D, "pfd").with_active(key="hy_fc")


def test_parse_diffs_1d_boundary_markers_apply_to_later_specs():
    diffs = parse_diffs_1d(["y=+", "pad", "z,x=-"], "fmt")
    assert diffs == [_Diff1d("y", 1, "truncate"), _Diff1d("z", -1, "pad"), _Diff1d("x", -1, "pad")]


def test_diff_name_fragment_unchanged():
    assert parse(["y=+", "pad", "z=-"]).get_name_fragments() == ["diff_truncate_y=+1_pad_z=-1"]


def test_diff_values_unchanged():
    data = _pfd_hy()
    da = data["hy_fc"]
    expected = (da.roll(y=-1, roll_coords=False) - da).isel(y=slice(0, -1))
    actual = Diff([_Diff1d("y", 1, "truncate")]).apply(data)["hy_fc"]
    xr.testing.assert_allclose(actual, expected)


def test_deriv_divides_by_spacing():
    data = _pfd_hy()
    da = data["hy_fc"]
    spacing = float(da.coords["y"][1] - da.coords["y"][0])
    expected = Diff([_Diff1d("y", 1, "truncate")]).apply(data)["hy_fc"] / spacing
    actual = parse_deriv(["truncate", "y=+"]).apply(data)["hy_fc"]
    xr.testing.assert_allclose(actual, expected)


def test_deriv_uses_each_dims_own_spacing():
    data = _pfd_hy()
    da = data["hy_fc"]
    dy = float(da.coords["y"][1] - da.coords["y"][0])
    dz = float(da.coords["z"][1] - da.coords["z"][0])
    expected = Diff([_Diff1d("y", 1, "truncate"), _Diff1d("z", 1, "truncate")]).apply(data)["hy_fc"] / (dy * dz)
    actual = parse_deriv(["y,z=+"]).apply(data)["hy_fc"]
    xr.testing.assert_allclose(actual, expected)


def test_deriv_nonuniform_spacing():
    x = np.array([0.0, 1.0, 3.0, 6.0])
    da = xr.DataArray(x**2, coords={"x": x}, dims="x")
    # forward difference quotient of x^2 is x_i + x_{i+1}
    expected = xr.DataArray([1.0, 4.0, 9.0], coords={"x": x[:-1]}, dims="x")
    xr.testing.assert_allclose(parse_deriv(["x=+"]).apply_field_bare(da), expected)
    expected = xr.DataArray([1.0, 4.0, 9.0], coords={"x": x[1:]}, dims="x")
    xr.testing.assert_allclose(parse_deriv(["x=-"]).apply_field_bare(da), expected)


def test_deriv_periodic_wraps_with_mean_spacing():
    x = np.array([0.0, 0.5, 1.0, 1.5])
    da = xr.DataArray([1.0, 2.0, 4.0, 8.0], coords={"x": x}, dims="x")
    expected = xr.DataArray([2.0, 4.0, 8.0, -14.0], coords={"x": x}, dims="x")
    xr.testing.assert_allclose(parse_deriv(["periodic", "x=+"]).apply_field_bare(da), expected)


def test_deriv_pad_boundary_is_zero():
    x = np.array([0.0, 1.0, 3.0])
    da = xr.DataArray([1.0, 2.0, 4.0], coords={"x": x}, dims="x")
    expected = xr.DataArray([1.0, 1.0, 0.0], coords={"x": x}, dims="x")
    xr.testing.assert_allclose(parse_deriv(["pad", "x=+"]).apply_field_bare(da), expected)


def test_deriv_rejects_dim_with_one_point():
    # test-2d is invariant in x (length 1)
    with pytest.raises(ValueError, match="'x'"):
        parse_deriv(["x=+"]).apply(_pfd_hy())["hy_fc"].compute()


def test_deriv_display_and_name_fragment():
    deriv = parse_deriv(["y=+"])
    result = deriv.apply(_pfd_hy())
    assert result.metadata.var_infos["hy_fc"].display.latex == r"\partial_{y}B_y"
    assert deriv.get_name_fragments() == ["partial_truncate_y=+1"]
