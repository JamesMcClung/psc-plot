import pytest
import xarray as xr
from conftest import CONFIG_2D

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
