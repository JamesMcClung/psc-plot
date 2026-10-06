import os
import re
from pathlib import Path

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


@pytest.mark.parametrize("prefix", ["pfd", "pfd_moments", "gauss"])
def test_default_registry_covers_test_data(prefix):
    assert [key for key in load(CONFIG_2D, prefix).data if CONFIG_2D.registry.entry(prefix, key) is None] == []


# --- lookup ---


def test_prefix_entry_wins_over_shared(tmp_path):
    registry = write_registry(tmp_path, {"shared": "x: {display: 'x', unit: 'd', geometry: linear}\n", "prt": "x: {display: 'x', unit: 'p'}\n"}).registry
    assert registry.entry(None, "x").var_info.geometry == "linear"
    assert registry.lookup("prt", "x").unit.latex == "p"
    assert registry.lookup("pfd", "x").unit.latex == "d"


def test_lookup_unknown_key_falls_back_to_key():
    info = Registry.load([]).lookup("pfd", "mystery")
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


def test_same_stem_files_merge(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "pfd.yml").write_text("one: {display: '1'}\n")
    (tmp_path / "b" / "pfd.yml").write_text("two: {display: '2'}\n")
    registry = Registry.load([tmp_path / "a" / "pfd.yml", tmp_path / "b" / "pfd.yml"])
    assert registry.lookup("pfd", "one").display.latex == "1"
    assert registry.lookup("pfd", "two").display.latex == "2"


def test_empty_file_is_allowed(tmp_path):
    assert write_registry(tmp_path, {"pfd": "# nothing yet\n"}).registry.derivable_keys("pfd") == []


# --- validation ---


def test_duplicate_key_across_files_errors(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first, second = tmp_path / "a" / "pfd.yml", tmp_path / "b" / "pfd.yml"
    first.write_text("x: {display: 'x'}\n")
    second.write_text("x: {display: 'X'}\n")
    with pytest.raises(RegistryError, match=re.escape(f"{second}: x already defined in {first}")):
        Registry.load([first, second])


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


def _files_config(*patterns: str, use_defaults: bool = False) -> PscPlotConfig:
    return PscPlotConfig.create_minimal(data_root=CONFIG_2D.data_root, registries_use_defaults=use_defaults, registry_patterns=list(patterns))


def test_registry_path_missing(tmp_path):
    with pytest.raises(RegistryError, match="does not exist"):
        _files_config(str(tmp_path / "nope.yml")).registry_files


def test_registry_glob_matches_nothing(tmp_path):
    with pytest.raises(RegistryError, match="matches no files"):
        _files_config(str(tmp_path / "*.yml")).registry_files


def test_registry_path_is_directory(tmp_path):
    with pytest.raises(RegistryError, match=re.escape(f"{tmp_path} is a directory; list its files, e.g. {tmp_path}/*.yml")):
        _files_config(str(tmp_path)).registry_files


def test_glob_matching_directory_errors(tmp_path):
    (tmp_path / "a.yml").write_text("")
    (tmp_path / "sub").mkdir()
    with pytest.raises(RegistryError, match="sub is a directory"):
        _files_config(str(tmp_path / "*")).registry_files


def test_registry_patterns_resolve_against_cwd_in_order(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "regs").mkdir()
    for name in ["b.yml", "a.yml", "z.yml"]:
        (tmp_path / "regs" / name).write_text("")
    assert _files_config("regs/z.yml", "regs/[ab].yml").registry_files == [Path("regs/z.yml"), Path("regs/a.yml"), Path("regs/b.yml")]


# --- config ---


def test_use_defaults_adds_listed_files(tmp_path):
    (tmp_path / "pfd.yml").write_text("my_var: {display: 'M'}\n")
    registry = _files_config(str(tmp_path / "pfd.yml"), use_defaults=True).registry
    assert registry.entry("pfd", "hx_fc") is not None
    assert registry.entry("pfd", "my_var") is not None


def test_redefining_default_entry_errors(tmp_path):
    (tmp_path / "pfd.yml").write_text("hx_fc: {display: 'H'}\n")
    with pytest.raises(RegistryError, match=r"pfd\.yml: hx_fc already defined in .*default_registries/pfd\.yml"):
        _files_config(str(tmp_path / "pfd.yml"), use_defaults=True).registry


def test_registry_settings_from_env(monkeypatch):
    for value, expected in [("FALSE", False), ("false", False), ("0", False), ("True", True), ("1", True)]:
        monkeypatch.setenv("PSC_PLOT_REGISTRIES_USE_DEFAULTS", value)
        assert PscPlotConfig.from_env().registries_use_defaults is expected

    monkeypatch.setenv("PSC_PLOT_REGISTRIES_USE_DEFAULTS", "maybe")
    with pytest.raises(ValueError, match="maybe"):
        PscPlotConfig.from_env()
    monkeypatch.delenv("PSC_PLOT_REGISTRIES_USE_DEFAULTS")

    monkeypatch.setenv("PSC_PLOT_REGISTRIES", f"a.yml{os.pathsep}b/*.yml")
    assert PscPlotConfig.from_env().registry_patterns == ["a.yml", "b/*.yml"]
    monkeypatch.setenv("PSC_PLOT_REGISTRIES", "")
    assert PscPlotConfig.from_env().registry_patterns == []


def test_config_custom_registry_replaces_defaults(tmp_path):
    config = write_registry(tmp_path, {"prt": "py: {display: 'U_Y', unit: 'c'}\n"})
    assert config.registry is config.registry
    assert config.registry.entry("pfd", "hx_fc") is None
    # the loaders read config.registry (test-2d's prt.e files carry px/py/pz)
    assert load(config, "prt.e").metadata.var_infos["py"].display.latex == "U_Y"
