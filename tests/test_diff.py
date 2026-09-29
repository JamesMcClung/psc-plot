import numpy as np
import pytest
import xarray as xr
from conftest import CONFIG_2D

from lib.data.adaptors.diff import Diff, _Diff1d, parse, parse_diffs_1d
from lib.data.adaptors.partial import parse_partial
from lib.data.loader import load


def _pfd_hy():
    return load(CONFIG_2D, "pfd").with_active(key="hy_fc")


def test_parse_diffs_1d_boundary_markers_apply_to_later_specs():
    diffs = parse_diffs_1d(["y=+", "pad", "z,x=-"], "fmt")
    assert diffs == [_Diff1d("y", 1, "truncate"), _Diff1d("z", -1, "pad"), _Diff1d("x", -1, "pad")]


def test_diff_values():
    data = _pfd_hy()
    da = data["hy_fc"]
    expected = (da.roll(y=-1, roll_coords=False) - da).isel(y=slice(0, -1))
    xr.testing.assert_allclose(parse(["y=+"]).apply(data)["hy_fc"], expected)


@pytest.mark.parametrize("dims", [["y"], ["y", "z"]])
def test_partial_divides_by_each_dims_spacing(dims):
    data = _pfd_hy()
    coords = data["hy_fc"].coords
    spacing = np.prod([float(coords[dim][1] - coords[dim][0]) for dim in dims])
    expected = Diff([_Diff1d(dim, 1, "truncate") for dim in dims]).apply(data)["hy_fc"] / spacing
    xr.testing.assert_allclose(parse_partial([f"{','.join(dims)}=+"]).apply(data)["hy_fc"], expected)


@pytest.mark.parametrize(
    "x, values, args, expected, expected_x",
    [
        # forward/backward difference quotients of x^2 are x_i + x_{i+1}
        ([0, 1, 3, 6], [0, 1, 9, 36], ["x=+"], [1, 4, 9], slice(0, -1)),
        ([0, 1, 3, 6], [0, 1, 9, 36], ["x=-"], [1, 4, 9], slice(1, None)),
        ([0, 0.5, 1, 1.5], [1, 2, 4, 8], ["periodic", "x=+"], [2, 4, 8, -14], slice(None)),
        # nonuniform: the wrap spacing is the average of the first and last spacings (1), not the mean spacing (4/3)
        ([0, 1, 3, 4], [1, 2, 4, 8], ["periodic", "x=+"], [1, 1, 4, -7], slice(None)),
        ([0, 1, 3, 4], [1, 2, 4, 8], ["periodic", "x=-"], [-7, 1, 1, 4], slice(None)),
        ([0, 1, 3], [1, 2, 4], ["pad", "x=+"], [1, 1, 0], slice(None)),
    ],
    ids=["nonuniform+", "nonuniform-", "periodic", "periodic_nonuniform+", "periodic_nonuniform-", "pad"],
)
def test_partial_1d(x, values, args, expected, expected_x):
    x = np.array(x, dtype=float)
    da = xr.DataArray(np.array(values, dtype=float), coords={"x": x}, dims="x")
    expected = xr.DataArray(np.array(expected, dtype=float), coords={"x": x[expected_x]}, dims="x")
    xr.testing.assert_allclose(parse_partial(args).apply_field_bare(da), expected)


def test_partial_rejects_dim_with_one_point():
    # test-2d is invariant in x (length 1)
    with pytest.raises(ValueError, match="'x'"):
        parse_partial(["x=+"]).apply(_pfd_hy())["hy_fc"].compute()


def test_display_and_name_fragments():
    assert parse(["y=+", "pad", "z=-"]).get_name_fragments() == ["diff_truncate_y=+1_pad_z=-1"]
    partial = parse_partial(["y=+"])
    assert partial.apply(_pfd_hy()).metadata.var_infos["hy_fc"].display.latex == r"\partial_{y}B_y"
    assert partial.get_name_fragments() == ["partial_truncate_y=+1"]
