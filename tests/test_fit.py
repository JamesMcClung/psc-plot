"""Tests for `--fit`."""

import numpy as np
import pandas as pd
import pytest
import scipy.stats
import xarray as xr
from conftest import CONFIG_2D, make_plot

from lib.data.adaptors.fit import Fit
from lib.data.adaptors.log import Log
from lib.data.data_with_attrs import Field, FieldMetadata, FullList, ListMetadata
from lib.data.data_world import DataWorld
from lib.data.loader import load
from lib.latex import Latex
from lib.parsing.parse import StepParseError, parse_steps
from lib.scale import LogScale
from lib.var_info import VarInfo

# --- fields ---


def _info(key: str, unit: str = "", **kwargs) -> VarInfo:
    return VarInfo(Latex(key), Latex(unit), key=key, **kwargs)


def _field(da: xr.DataArray, **extra: xr.DataArray) -> Field:
    """A field whose active variable `f` is `da`, with unit U and a log scale."""
    var_infos = {"f": _info("f", "U", scale=LogScale())} | {dim: _info(dim) for dim in da.dims} | {key: _info(key) for key in extra}
    return Field({"f": da} | extra, FieldMetadata(prepath="pfd", active_key="f", var_infos=var_infos))


def _fit(data, names: list[str], assignment: str):
    world = DataWorld({"pfd": data}, "pfd", config=CONFIG_2D)
    return Fit(names, assignment).apply_world(world).require_active_data()


def _f_y_t() -> xr.DataArray:
    """f(y, t) = (t+1) * y on y = 1..5, t = 0..2."""
    y = np.arange(1.0, 6.0)
    t = np.arange(3.0)
    return xr.DataArray(np.outer(y, t + 1), coords={"y": y, "t": t}, dims=("y", "t"))


def test_power_law_matches_linregress():
    """The old hook's log-log linear regression, reproduced by --log + --fit."""
    y = np.linspace(1, 20, 40)
    f = 3 * y**-1.7 * (1 + 0.01 * np.sin(y))
    data = Log(None).apply(_field(xr.DataArray(f, coords={"y": y}, dims="y")))
    curve = _fit(data, ["c", "gamma"], "fit=c-gamma*log(y)")["fit"]

    slope, intercept, *_ = scipy.stats.linregress(np.log(y), np.log(f))
    assert float(curve.coords["gamma"]) == pytest.approx(-slope, rel=1e-6)
    assert float(curve.coords["c"]) == pytest.approx(intercept, rel=1e-6)


def test_field_fit_output_metadata():
    y = np.arange(1.0, 6.0)
    data = _fit(_field(xr.DataArray(2 * y, coords={"y": y}, dims="y")), ["a"], "fit=a*y")
    assert data.active_key == "fit"
    info = data.active_info
    assert info.key == "fit" and not info.display
    assert info.unit == Latex("U") and info.scale == LogScale()
    assert data["fit"].coords["a"].shape == ()
    assert "a" in data.metadata.var_infos
    np.testing.assert_allclose(data["fit"], 2 * y)


def test_field_fit_per_value_dim():
    curve = _fit(_field(_f_y_t()), ["a", "t"], "fit=a*y")["fit"]
    assert curve.coords["a"].dims == ("t",)
    np.testing.assert_allclose(curve.coords["a"], [1, 2, 3])
    assert curve.isel(t=0).coords["a"].shape == ()
    xr.testing.assert_allclose(curve.drop_vars("a"), _f_y_t())


def test_field_fit_two_variables():
    y, z = np.arange(1.0, 5.0), np.arange(1.0, 4.0)
    da = xr.DataArray(2 * y[:, None] + 3 * z[None, :], coords={"y": y, "z": z}, dims=("y", "z"))
    curve = _fit(_field(da), ["a", "b"], "fit=a*y+b*z")["fit"]
    assert float(curve.coords["a"]) == pytest.approx(2.0)
    assert float(curve.coords["b"]) == pytest.approx(3.0)
    xr.testing.assert_allclose(curve.drop_vars(["a", "b"]), da)


def test_field_fit_pools_unlisted_dims():
    curve = _fit(_field(_f_y_t()), ["a"], "fit=a*y")["fit"]
    assert float(curve.coords["a"]) == pytest.approx(2.0)
    assert set(curve.dims) == {"y", "t"}


def test_field_fit_skips_nans():
    y = np.arange(1.0, 8.0)
    f = 2 * y
    f[[1, 4]] = np.nan
    curve = _fit(_field(xr.DataArray(f, coords={"y": y}, dims="y")), ["a"], "fit=a*y")["fit"]
    assert float(curve.coords["a"]) == pytest.approx(2.0)


def test_field_fit_named_variable_errors():
    da = _f_y_t()
    with pytest.raises(ValueError, match="--scatter"):
        _fit(_field(da, g=da), ["a"], "fit=a*g")


def test_per_value_name_not_a_dim_errors():
    with pytest.raises(ValueError, match="'q'"):
        _fit(_field(_f_y_t()), ["a", "q"], "fit=a*y")


def test_coefficient_colliding_with_dim_errors():
    with pytest.raises(ValueError, match="'t'"):
        _fit(_field(_f_y_t()), ["t"], "fit=t*y")


def test_expression_without_independent_variable_errors():
    with pytest.raises(ValueError, match="besides the coefficients"):
        Fit(["c"], "fit=c")


def test_no_coefficients_errors():
    with pytest.raises(ValueError, match="coefficient"):
        Fit(["t"], "fit=y")


def test_scoped_variable_errors():
    with pytest.raises(ValueError, match="prepath::key"):
        Fit(["a"], "fit=a*pfd::y")


def test_degenerate_group_errors():
    da = _f_y_t().copy()
    da[1:, 1] = np.nan  # t=1 keeps a single point, fewer than the 2 coefficients
    with pytest.raises(ValueError, match="fewer"):
        _fit(_field(da), ["a", "b", "t"], "fit=a*y+b")


def test_fit_real_field():
    pfd = load(CONFIG_2D, "pfd").with_active(key="hx_fc")
    curve = _fit(pfd, ["a", "b", "t"], "fit=a*y+b")["fit"]
    assert set(curve.dims) == set(pfd["hx_fc"].dims)
    assert curve.coords["a"].dims == ("t",)


# --- lists ---


def _list(df: pd.DataFrame, coordss: dict[str, np.ndarray] | None = None, **infos: VarInfo) -> FullList:
    """A list whose active variable is the column `f`, with unit U and a log scale."""
    var_infos = {key: _info(key) for key in df.columns} | {"f": _info("f", "U", scale=LogScale())} | infos
    return FullList(df, ListMetadata(prepath="prt.e", active_key="f", var_infos=var_infos, coordss=coordss or {}))


def _u_t_list() -> FullList:
    """Rows of f = (t+1) * u for u = 0..4, t in {0, 1}."""
    u = np.tile(np.linspace(0, 4, 50), 2)
    t = np.repeat([0.0, 1.0], 50)
    return _list(pd.DataFrame({"u": u, "t": t, "f": (t + 1) * u}), {"t": np.array([0.0, 1.0])})


def test_list_fit_artificial_coords():
    data = _fit(_u_t_list(), ["a", "t"], "fit=a*u")
    assert isinstance(data, Field)
    curve = data["fit"]
    assert curve.dims == ("u", "t")
    np.testing.assert_allclose(curve.coords["u"], np.linspace(0, 4, 100))
    np.testing.assert_allclose(curve.coords["a"], [1, 2])
    assert curve.coords["a"].dims == ("t",)


def test_list_fit_output_metadata():
    data = _fit(_u_t_list(), ["a", "t"], "fit=a*u")
    info = data.active_info
    assert data.active_key == "fit" and info.key == "fit" and not info.display
    assert info.unit == Latex("U") and info.scale == LogScale()
    assert {"a", "u", "t"} <= data.metadata.var_infos.keys()


def test_list_fit_uses_existing_coords():
    x = np.linspace(0, 4, 30)
    grid = np.arange(4.0)
    curve = _fit(_list(pd.DataFrame({"x": x, "f": 2 * x}), {"x": grid}), ["a"], "fit=a*x")["fit"]
    np.testing.assert_allclose(curve.coords["x"], grid)
    np.testing.assert_allclose(curve, 2 * grid)


def test_list_fit_pools_unlisted_coords():
    rng = np.random.default_rng(0)
    x, y = rng.uniform(0, 4, 40), rng.uniform(0, 4, 40)
    data = _list(pd.DataFrame({"x": x, "y": y, "f": 2 * x}), {"x": np.arange(4.0), "y": np.arange(4.0)})
    curve = _fit(data, ["a"], "fit=a*x")["fit"]
    assert curve.dims == ("x",)
    assert float(curve.coords["a"]) == pytest.approx(2.0)


def test_log_scaled_artificial_coords_are_geometric():
    u = np.geomspace(1, 100, 20)
    data = _list(pd.DataFrame({"u": u, "f": 2 * u}), u=_info("u", scale=LogScale()))
    curve = _fit(data, ["a"], "fit=a*u")["fit"]
    np.testing.assert_allclose(curve.coords["u"], np.geomspace(1, 100, 100))


def test_log_scaled_artificial_coords_need_positive_range():
    u = np.linspace(0, 100, 20)
    data = _list(pd.DataFrame({"u": u, "f": 2 * u}), u=_info("u", scale=LogScale()))
    with pytest.raises(ValueError, match="positive range"):
        _fit(data, ["a"], "fit=a*u")


def test_list_power_law_matches_linregress():
    k = np.linspace(1, 20, 40)
    f = 3 * k**-1.7 * (1 + 0.01 * np.sin(k))
    data = Log(None).apply(_list(pd.DataFrame({"k": k, "f": f})))
    curve = _fit(data, ["c", "gamma"], "fit=c-gamma*log(k)")["fit"]
    slope, intercept, *_ = scipy.stats.linregress(np.log(k), np.log(f))
    assert float(curve.coords["gamma"]) == pytest.approx(-slope, rel=1e-6)
    assert float(curve.coords["c"]) == pytest.approx(intercept, rel=1e-6)


def test_list_fit_skips_nans():
    u = np.linspace(0, 4, 20)
    f = 2 * u
    f[[3, 7]] = np.nan
    curve = _fit(_list(pd.DataFrame({"u": u, "f": f})), ["a"], "fit=a*u")["fit"]
    assert float(curve.coords["a"]) == pytest.approx(2.0)


def test_list_degenerate_group_errors():
    data = _u_t_list()
    data = data.assign(coordss={"t": np.array([0.0, 1.0, 2.0])})  # no rows at t=2
    with pytest.raises(ValueError, match="fewer"):
        _fit(data, ["a", "t"], "fit=a*u")


def test_list_per_value_dim_without_coords_errors():
    with pytest.raises(ValueError, match="'u'"):
        _fit(_u_t_list(), ["a", "u"], "fit=a*t")


def test_list_unknown_variable_errors():
    with pytest.raises(ValueError, match="'q'"):
        _fit(_u_t_list(), ["a"], "fit=a*q")


def test_list_fit_real_particles():
    prt = load(CONFIG_2D, "prt.e").with_active(key="px")
    curve = _fit(prt, ["a", "b", "t"], "fit=a*py+b")["fit"]
    assert curve.dims == ("py", "t")
    assert curve.coords["a"].dims == ("t",)
    assert len(curve.coords["py"]) == 100


def test_list_coefficient_may_shadow_a_coord():
    curve = _fit(_u_t_list(), ["t"], "fit=t*u")["fit"]
    assert curve.dims == ("u",)
    assert float(curve.coords["t"]) == pytest.approx(1.5)


# --- parsing ---


def test_parse_fit_classifies_names():
    [fit] = parse_steps(["--fit c gamma t fit=c-gamma*log(k_s)"])
    assert isinstance(fit, Fit)
    assert fit.coef_keys == ["c", "gamma"] and fit.per_value_dims == ["t"] and fit.new_key == "fit"


@pytest.mark.parametrize(
    "step, match",
    [
        ("--fit a b", "exactly one"),
        ("--fit a f=a*y g=a*y", "exactly one"),
        ("--fit a fit=b*y", "at least one coefficient"),
        ("--fit a-b fit=a*y", "identifier"),
        ("--fit a fit=a*", "argument --fit: .*fit=a\\*"),
    ],
)
def test_parse_fit_errors(step, match):
    with pytest.raises(StepParseError, match=match):
        parse_steps([step])


# --- plotting ---


def test_fit_curve_shares_the_data_axis_and_label():
    """The curve copies the data's unit and scale, so it lands on the data's y axis; its empty display defers to the data's."""
    fig = make_plot("pfd hhat2_xyz --scatter --transform-spherical k_y k_z k_x --pos k_s=1e-8: --scale hhat2_xyz=log -cv k_s hhat2_xyz --pos k_s=25:45 --log --fit c gamma t fit=c-gamma*log(k_s) --exp -v k_s".split(), data_dir="test-3d")
    [axes] = fig.axes
    assert "B" in axes.get_ylabel()
    assert axes.get_yscale() == "log"


# --- non-finite values and dask (from review) ---


def test_field_fit_skips_infinite_data():
    """e.g. --log of a zero gives -inf, which is as unusable as a NaN."""
    y = np.arange(1.0, 7.0)
    f = 2 * y
    f[2] = -np.inf
    curve = _fit(_field(xr.DataArray(f, coords={"y": y}, dims="y")), ["a"], "fit=a*y")["fit"]
    assert float(curve.coords["a"]) == pytest.approx(2.0)


def test_list_fit_skips_infinite_data():
    u = np.linspace(1, 4, 20)
    f = 2 * u
    f[[3, 7]] = -np.inf
    curve = _fit(_list(pd.DataFrame({"u": u, "f": f})), ["a"], "fit=a*u")["fit"]
    assert float(curve.coords["a"]) == pytest.approx(2.0)


def test_field_fit_skips_points_where_the_model_is_infinite():
    """log(k) at k=0 is -inf for any coefficients; those points can't inform the fit (and used to return p0 silently)."""
    k = np.arange(0.0, 6.0)
    with np.errstate(divide="ignore"):
        f = np.where(k > 0, 2 - 1.5 * np.log(k), 7.0)
    curve = _fit(_field(xr.DataArray(f, coords={"k": k}, dims="k")), ["c", "gamma"], "fit=c-gamma*log(k)")["fit"]
    assert float(curve.coords["c"]) == pytest.approx(2.0)
    assert float(curve.coords["gamma"]) == pytest.approx(1.5)


def test_list_fit_skips_points_where_the_model_is_infinite():
    k = np.arange(0.0, 6.0)
    with np.errstate(divide="ignore"):
        f = np.where(k > 0, 2 - 1.5 * np.log(k), 7.0)
    curve = _fit(_list(pd.DataFrame({"k": k, "f": f})), ["c", "gamma"], "fit=c-gamma*log(k)")["fit"]
    assert float(curve.coords["c"]) == pytest.approx(2.0)
    assert float(curve.coords["gamma"]) == pytest.approx(1.5)


def test_dask_field_fit_reads_the_data_once():
    import dask
    from dask.callbacks import Callback

    computes = []
    pfd = load(CONFIG_2D, "pfd").with_active(key="hx_fc")
    assert dask.is_dask_collection(pfd["hx_fc"])
    with Callback(start=lambda dsk: computes.append(1)):
        curve = _fit(pfd, ["a", "b", "t"], "fit=a*y+b")["fit"]
        curve.values
    assert len(computes) == 1
