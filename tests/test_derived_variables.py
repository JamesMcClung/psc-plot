import pytest
import xarray as xr
from conftest import _DATA_DIR, CONFIG_2D, CONFIG_3D, write_registry

from lib.config import PscPlotConfig
from lib.data.ensure_derived import ensure_derived, get_derivable_keys
from lib.data.loader import load


def _derivable_cases():
    # test-2d has no continuity files; the dim-suffixed variants need data with those dims
    for prefix in ("pfd", "pfd_moments", "gauss", "prt"):
        for key in CONFIG_2D.registry.derivable_keys(prefix):
            config = CONFIG_3D if key.endswith("_xyz") else CONFIG_2D
            yield pytest.param(config, prefix, key, id=f"{prefix}::{key}")


@pytest.mark.parametrize("config, prefix, key", _derivable_cases())
def test_every_default_derived_variable_derives(config, prefix, key):
    result = ensure_derived(load(config, prefix), key, config)[key].compute()
    assert result.notnull().any()


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
    xr.testing.assert_allclose(data["h2_cc"], ensure_derived(load(CONFIG_2D, "pfd"), "h2_cc", CONFIG_2D)["h2_cc"])


@pytest.mark.parametrize(
    "text, match",
    [
        ("a:\n  display: 'a'\n  pipeline: ['--with b']\nb:\n  display: 'b'\n  pipeline: ['--with a']\n", "Cyclic derived variable: a -> b -> a"),
        ("a:\n  display: 'a'\n  pipeline: ['--derive a=a+1']\n", "Cyclic derived variable: a -> a"),
        # --derive, not --with: an unknown --with name is taken as a prepath and fails in the loader instead
        ("a:\n  display: 'a'\n  pipeline: ['--derive a=missing_key+1']\n", "No variable named 'missing_key'"),
    ],
    ids=["cycle", "self_cycle", "unknown_input"],
)
def test_pipeline_errors(tmp_path, text, match):
    config = write_registry(tmp_path, {"pfd": text})
    with pytest.raises(ValueError, match=match):
        ensure_derived(load(config, "pfd"), "a", config)


def test_reused_pipeline_sees_new_data(tmp_path):
    # the registry parses each pipeline once, so its steps must not cache results between applications
    config = write_registry(tmp_path, {"pfd": "a:\n  display: 'a'\n  pipeline: ['--derive a=hx_fc+1']\n"})
    data = load(config, "pfd")
    ensure_derived(data, "a", config)
    zeroed = data.with_active(data=data["hx_fc"] * 0, key="hx_fc")
    second = ensure_derived(zeroed, "a", config)["a"]
    xr.testing.assert_allclose(second, xr.ones_like(second))
