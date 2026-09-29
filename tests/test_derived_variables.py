from pathlib import Path

import numpy as np
import pandas as pd
import pscpy
import pytest
import xarray as xr
from conftest import _DATA_DIR, CONFIG_2D
from xarray import DataArray, Dataset

from lib.config import PscPlotConfig
from lib.data.adaptors.fourier import toggle_fourier
from lib.data.adaptors.mag import Magnitude
from lib.data.ensure_derived import ensure_derived, get_derivable_keys
from lib.data.loader import load

CONFIG_3D = PscPlotConfig(data_root=_DATA_DIR / "test-3d")


def _derived(config: PscPlotConfig, prepath: str, key: str):
    return ensure_derived(load(config, prepath), key, config)[key]


def _assert_field_close(actual: DataArray, expected: DataArray):
    xr.testing.assert_allclose(actual.transpose(*expected.dims), expected)


# --- reference implementations: the deleted Python registry, verbatim in substance ---


def _ref_temperature(t_aa, p_a, j_a, rho, q):
    return (t_aa - p_a * j_a / rho) * q / rho


def _ref_s_or_p(e, h, sign):
    h = pscpy.get_recentered(h, "y", -1)
    return (e + sign * h).isel(y=slice(1, None)) / 2


def _ref_h2(*components: tuple[str, DataArray]):
    h = Dataset({f"h2{dim}_fc": da**2 for dim, da in components})
    pscpy.auto_recenter(h, "cc", x="periodic", y="periodic", z="periodic")
    return sum(h[f"h2{dim}_cc"] for dim, _ in components)


def _ref_hat2(components: list[DataArray], registry):
    first = components[0]
    dims = [registry.lookup("pfd", dim) for dim in first.dims if dim in {"x", "y", "z"} and len(first.coords[dim]) > 1]
    cut_nyquist = {dim.toggle_fourier().key: slice(1, None) for dim in dims}
    total = None
    for da in components:
        for dim in dims:
            da = toggle_fourier(da, dim)
        hat = Magnitude().apply_field_bare(da.isel(cut_nyquist))
        total = hat**2 if total is None else total + hat**2
    return total


def _ref_div_h(hx_fc, hy_fc, hz_fc):
    coords = hx_fc.coords
    noninvariant_dims = {dim for dim in ("x", "y", "z") if len(coords[dim]) > 1}
    h_comps = {"x": hx_fc, "y": hy_fc, "z": hz_fc}
    div = None
    for d in noninvariant_dims:
        other_dims = noninvariant_dims - {d}
        hd = h_comps[d].isel({other: slice(0, -1) for other in other_dims})
        delta = hd.isel({d: slice(1, None)}).data - hd.isel({d: slice(0, -1)}).data
        diff = delta / float(coords[d][1] - coords[d][0])
        div = diff if div is None else div + diff
    new_coords = {d: (coord[:-1] if d in noninvariant_dims else coord) for d, coord in coords.items()}
    return DataArray(div, new_coords, dims=hx_fc.dims)


# --- field parity ---


@pytest.mark.parametrize("species, q", [("e", -1.0), ("i", 1.0)])
@pytest.mark.parametrize("a", ["x", "y", "z"])
def test_temperature(species, q, a):
    data = load(CONFIG_2D, "pfd_moments")
    expected = _ref_temperature(data[f"t{a}{a}_{species}"], data[f"p{a}_{species}"], data[f"j{a}_{species}"], data[f"rho_{species}"], q)
    _assert_field_close(_derived(CONFIG_2D, "pfd_moments", f"T{a}{a}_{species}"), expected)


def test_moments_rho():
    data = load(CONFIG_2D, "pfd_moments")
    _assert_field_close(_derived(CONFIG_2D, "pfd_moments", "rho"), data["rho_i"] + data["rho_e"])


def test_gauss_error():
    data = load(CONFIG_2D, "gauss")
    _assert_field_close(_derived(CONFIG_2D, "gauss", "error"), data["rho"] - data["dive"])


@pytest.mark.parametrize("key, e, h, sign", [("sy_p", "ez_ec", "hx_fc", 1), ("sy_m", "ez_ec", "hx_fc", -1), ("py_p", "ex_ec", "hz_fc", -1), ("py_m", "ex_ec", "hz_fc", 1)])
def test_poynting_like(key, e, h, sign):
    data = load(CONFIG_2D, "pfd")
    _assert_field_close(_derived(CONFIG_2D, "pfd", key), _ref_s_or_p(data[e], data[h], sign))


@pytest.mark.parametrize("config", [CONFIG_2D, CONFIG_3D], ids=["2d", "3d"])
def test_h2_cc(config):
    data = load(config, "pfd")
    expected = _ref_h2(("x", data["hx_fc"]), ("y", data["hy_fc"]), ("z", data["hz_fc"]))
    _assert_field_close(_derived(config, "pfd", "h2_cc"), expected)


def test_hxz2_cc():
    data = load(CONFIG_2D, "pfd")
    _assert_field_close(_derived(CONFIG_2D, "pfd", "hxz2_cc"), _ref_h2(("x", data["hx_fc"]), ("z", data["hz_fc"])))


def test_h_cc_derives_recursively():
    data = load(CONFIG_2D, "pfd")
    expected = np.sqrt(_ref_h2(("x", data["hx_fc"]), ("y", data["hy_fc"]), ("z", data["hz_fc"])))
    _assert_field_close(_derived(CONFIG_2D, "pfd", "h_cc"), expected)


@pytest.mark.parametrize("config, suffix", [(CONFIG_2D, "yz"), (CONFIG_3D, "xyz")], ids=["2d", "3d"])
def test_hhat2(config, suffix):
    data = load(config, "pfd")
    expected = _ref_hat2([data["hx_fc"], data["hy_fc"], data["hz_fc"]], config.registry)
    _assert_field_close(_derived(config, "pfd", f"hhat2_{suffix}"), expected)


@pytest.mark.parametrize("config, suffix", [(CONFIG_2D, "yz"), (CONFIG_3D, "xyz")], ids=["2d", "3d"])
def test_hxzhat2(config, suffix):
    data = load(config, "pfd")
    expected = _ref_hat2([data["hx_fc"], data["hz_fc"]], config.registry)
    _assert_field_close(_derived(config, "pfd", f"hxzhat2_{suffix}"), expected)


@pytest.mark.parametrize("config, suffix", [(CONFIG_2D, "yz"), (CONFIG_3D, "xyz")], ids=["2d", "3d"])
def test_div_h_cc(config, suffix):
    data = load(config, "pfd")
    _assert_field_close(_derived(config, "pfd", f"div_h_cc_{suffix}"), _ref_div_h(data["hx_fc"], data["hy_fc"], data["hz_fc"]))


# --- particle parity ---

_PARTICLE_REFERENCES = {
    "pxy": lambda d: (d.px**2 + d.py**2) ** 0.5,
    "pyz": lambda d: (d.py**2 + d.pz**2) ** 0.5,
    "pzx": lambda d: (d.pz**2 + d.px**2) ** 0.5,
    "anisotropy_y_zx": lambda d: d.py**2 / (d.pz**2 + d.px**2),
    "wx": lambda d: 0.5 * d.m * d.px**2,
    "wy": lambda d: 0.5 * d.m * d.py**2,
    "wz": lambda d: 0.5 * d.m * d.pz**2,
    "wxy": lambda d: 0.5 * d.m * (d.px**2 + d.py**2),
    "wyz": lambda d: 0.5 * d.m * (d.py**2 + d.pz**2),
    "wzx": lambda d: 0.5 * d.m * (d.pz**2 + d.px**2),
    "wxyz": lambda d: 0.5 * d.m * (d.px**2 + d.py**2 + d.pz**2),
}


@pytest.mark.parametrize("key", list(_PARTICLE_REFERENCES))
def test_particle(key):
    data = load(CONFIG_2D, "prt")
    expected = _PARTICLE_REFERENCES[key](data.data).compute()
    actual = _derived(CONFIG_2D, "prt", key).compute()
    pd.testing.assert_series_equal(actual, expected, check_names=False, rtol=1e-6)


# --- behavior ---


def test_derived_var_info_comes_from_registry():
    data = ensure_derived(load(CONFIG_2D, "pfd"), "h2_cc", CONFIG_2D)
    assert data.metadata.var_infos["h2_cc"].display.latex == "B^2"


def test_temporaries_do_not_leak():
    data = ensure_derived(load(CONFIG_2D, "pfd"), "h2_cc", CONFIG_2D)
    assert "h2x" not in data
    assert "h2x" not in data.metadata.var_infos


def test_active_key_is_unchanged():
    data = load(CONFIG_2D, "pfd").with_active(key="hx_fc")
    assert ensure_derived(data, "h2_cc", CONFIG_2D).active_key == "hx_fc"


def test_fourier_dims_get_var_infos():
    data = ensure_derived(load(CONFIG_2D, "pfd"), "hhat2_yz", CONFIG_2D)
    assert data.metadata.var_infos["k_y"].display.latex == "k_y"


def test_unknown_key_lists_derivable_keys():
    with pytest.raises(ValueError, match=r"(?s)No variable named 'nope'.*h2_cc"):
        ensure_derived(load(CONFIG_2D, "pfd"), "nope", CONFIG_2D)


def test_get_derivable_keys():
    assert "hhat2_yz" in get_derivable_keys(load(CONFIG_2D, "pfd"), CONFIG_2D)
    assert "wx" in get_derivable_keys(load(CONFIG_2D, "prt.e"), CONFIG_2D)


def test_derived_on_subdir_prepath():
    config = PscPlotConfig(data_root=_DATA_DIR)
    data = ensure_derived(load(config, "test-2d/pfd"), "h2_cc", config)
    assert data.metadata.var_infos["h2_cc"].display.latex == "B^2"
    _assert_field_close(data["h2_cc"], _derived(CONFIG_2D, "pfd", "h2_cc"))


def _write_registry(dir: Path, text: str) -> PscPlotConfig:
    (dir / "pfd.yml").write_text(text)
    return PscPlotConfig(data_root=CONFIG_2D.data_root, registries_dir=dir)


def test_cycle_detected(tmp_path):
    config = _write_registry(tmp_path, "a:\n  display: 'a'\n  pipeline: ['--with b']\nb:\n  display: 'b'\n  pipeline: ['--with a']\n")
    with pytest.raises(ValueError, match="Cyclic derived variable: a -> b -> a"):
        ensure_derived(load(config, "pfd"), "a", config)


def test_self_cycle_detected(tmp_path):
    config = _write_registry(tmp_path, "a:\n  display: 'a'\n  pipeline: ['--derive a=a+1']\n")
    with pytest.raises(ValueError, match="Cyclic derived variable: a -> a"):
        ensure_derived(load(config, "pfd"), "a", config)


def test_pipeline_error_names_the_variable(tmp_path):
    # --derive, not --with: an unknown --with name is taken as a prepath and fails in the loader instead
    config = _write_registry(tmp_path, "a:\n  display: 'a'\n  pipeline: ['--derive a=missing_key+1']\n")
    with pytest.raises(ValueError, match="No variable named 'missing_key'"):
        ensure_derived(load(config, "pfd"), "a", config)
