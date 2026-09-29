import pytest
from conftest import CONFIG_2D, write_registry

from lib.config import PscPlotConfig
from lib.data.adaptors.copy import Copy
from lib.data.loader import load
from lib.registry import Registry, RegistryError

# --- default registry ---


def test_default_registry_derivable_keys():
    registry = CONFIG_2D.registry
    assert set(registry.derivable_keys("pfd")) == {"h2_cc", "hxz2_cc", "h_cc", "hxzhat2_xyz", "hxzhat2_yz", "hhat2_xyz", "hhat2_yz", "div_h_cc_xyz", "div_h_cc_yz", "sy_p", "sy_m", "py_p", "py_m"}
    assert set(registry.derivable_keys("pfd_moments")) == {"rho", "Txx_e", "Tyy_e", "Tzz_e", "Txx_i", "Tyy_i", "Tzz_i"}
    assert set(registry.derivable_keys("gauss")) == {"error"}
    assert set(registry.derivable_keys("continuity")) == {"error"}
    assert set(registry.derivable_keys("prt")) == {"pxy", "pyz", "pzx", "anisotropy_y_zx", "wx", "wy", "wz", "wxy", "wyz", "wzx", "wxyz"}


# --- lookup ---


def test_prefix_entry_wins_over_shared(tmp_path):
    registry = write_registry(tmp_path, {"shared": "x: {display: 'x', unit: 'd', geometry: linear}\n", "prt": "x: {display: 'x', unit: 'p'}\n"}).registry
    assert registry.entry(None, "x").var_info.geometry == "linear"
    assert registry.lookup("prt", "x").unit.latex == "p"
    assert registry.lookup("pfd", "x").unit.latex == "d"


def test_lookup_unknown_key_falls_back_to_key(tmp_path):
    info = Registry.load(tmp_path).lookup("pfd", "mystery")
    assert (info.display.latex, info.unit.latex, info.key) == ("mystery", "", "mystery")


def test_prt_species_prefix_normalizes_to_prt(tmp_path):
    registry = write_registry(tmp_path, {"prt": "uy: {display: 'u_y'}\nwx:\n  display: 'W_x'\n  pipeline: ['--derive wx=0.5*m*px^2']\n"}).registry
    assert registry.lookup("prt.e", "uy").display.latex == "u_y"
    assert registry.derivable_keys("prt.e") == ["wx"]
    assert registry.pipeline("prt.i", "wx") is not None


def test_pipeline_is_parsed(tmp_path):
    registry = write_registry(tmp_path, {"pfd": "a:\n  display: 'a'\n  pipeline: ['--copy a=hx_fc']\nhx_fc: {display: 'B_x'}\n"}).registry
    [step] = registry.pipeline("pfd", "a")
    assert isinstance(step, Copy)
    assert registry.pipeline("pfd", "hx_fc") is None
    assert registry.derivable_keys("pfd") == ["a"]


def test_empty_file_is_allowed(tmp_path):
    assert write_registry(tmp_path, {"pfd": "# nothing yet\n"}).registry.derivable_keys("pfd") == []


# --- validation ---


@pytest.mark.parametrize(
    "stem, text, match",
    [
        ("pfd", "a: {display: 'a', colour: red}\n", r"pfd\.yml: a: unknown field"),
        ("pfd", "a: {unit: 'c'}\n", r"pfd\.yml: a: missing 'display'"),
        ("pfd", "a: {display: 'a', geometry: cubic}\n", r"pfd\.yml: a: .*geometry"),
        ("pfd", "a: {display: 1}\n", r"pfd\.yml: a: 'display' must be a string"),
        ("pfd", "a: 'B_x'\n", r"pfd\.yml: a: expected a mapping"),
        ("pfd", "a:\n  display: 'a'\n  pipeline: '--pow 2'\n", r"pfd\.yml: a: 'pipeline' must be a list"),
        ("pfd", "a:\n  display: 'a'\n  pipeline: ['--idx y=abc']\n", r"pfd\.yml: a: step '--idx y=abc'"),
        ("pfd", "on: {display: 'a'}\n", r"pfd\.yml: .*must be a string"),
        ("pfd", "- a\n- b\n", r"pfd\.yml: expected a mapping"),
        ("pfd", "a: {display: 'a'}\na: {display: 'b'}\n", r"pfd\.yml.*duplicate key 'a'"),
        # double-quoted YAML turns the \t of \text into a tab
        ("pfd", 'a: {display: "\\text{e}"}\n', r"pfd\.yml: a: .*single quotes"),
        ("shared", "x:\n  display: 'x'\n  pipeline: ['--pow 2']\n", r"shared\.yml: x: .*pipeline"),
    ],
)
def test_invalid_entries(tmp_path, stem, text, match):
    config = write_registry(tmp_path, {stem: text})
    with pytest.raises(RegistryError, match=match):
        config.registry


@pytest.mark.parametrize("name, match", [("nope", "does not exist"), ("file.yml", "not a directory")])
def test_bad_registries_dir(tmp_path, name, match):
    (tmp_path / "file.yml").write_text("")
    with pytest.raises(RegistryError, match=match):
        Registry.load(tmp_path / name)


# --- config ---


def test_config_registries_dir_from_env(monkeypatch, tmp_path):
    monkeypatch.delenv("PSC_PLOT_REGISTRIES", raising=False)
    assert (PscPlotConfig.from_env().registries_dir / "pfd.yml").is_file()
    monkeypatch.setenv("PSC_PLOT_REGISTRIES", str(tmp_path))
    assert PscPlotConfig.from_env().registries_dir == tmp_path


def test_config_custom_registry_replaces_defaults(tmp_path):
    config = write_registry(tmp_path, {"prt": "py: {display: 'U_Y', unit: 'c'}\n"})
    assert config.registry is config.registry
    assert config.registry.entry("pfd", "hx_fc") is None
    # the loaders read config.registry (test-2d's prt.e files carry px/py/pz)
    assert load(config, "prt.e").metadata.var_infos["py"].display.latex == "U_Y"
