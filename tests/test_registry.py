from pathlib import Path

import pytest

from lib.data.adaptors.copy import Copy
from lib.registry import Registry, RegistryError

DEFAULT_REGISTRIES_DIR = Path(__file__).parent.parent / "src" / "lib" / "default_registries"


def _write(dir: Path, name: str, text: str) -> Path:
    path = dir / name
    path.write_text(text)
    return dir


# --- default registry ---


def test_default_registry_loads():
    registry = Registry.load(DEFAULT_REGISTRIES_DIR)
    assert registry.lookup("pfd", "hx_fc").display.latex == "B_x"
    assert registry.lookup("pfd_moments", "px_e").unit.latex == "c"


def test_default_registry_derivable_keys():
    registry = Registry.load(DEFAULT_REGISTRIES_DIR)
    assert set(registry.derivable_keys("pfd")) == {"h2_cc", "hxz2_cc", "h_cc", "hxzhat2_xyz", "hxzhat2_yz", "hhat2_xyz", "hhat2_yz", "div_h_cc_xyz", "div_h_cc_yz", "sy_p", "sy_m", "py_p", "py_m"}
    assert set(registry.derivable_keys("pfd_moments")) == {"rho", "Txx_e", "Tyy_e", "Tzz_e", "Txx_i", "Tyy_i", "Tzz_i"}
    assert set(registry.derivable_keys("gauss")) == {"error"}
    assert set(registry.derivable_keys("continuity")) == {"error"}
    assert set(registry.derivable_keys("prt")) == {"pxy", "pyz", "pzx", "anisotropy_y_zx", "wx", "wy", "wz", "wxy", "wyz", "wzx", "wxyz"}


# --- lookup ---


def test_shared_file_is_the_none_prefix(tmp_path):
    _write(tmp_path, "shared.yml", "x: {display: 'x', unit: 'd', geometry: linear}\n")
    registry = Registry.load(tmp_path)
    assert registry.entry(None, "x").var_info.geometry == "linear"
    assert registry.lookup("anything", "x").unit.latex == "d"


def test_prefix_entry_wins_over_shared(tmp_path):
    _write(tmp_path, "shared.yml", "x: {display: 'x', unit: 'd'}\n")
    _write(tmp_path, "prt.yml", "x: {display: 'x', unit: 'p'}\n")
    registry = Registry.load(tmp_path)
    assert registry.lookup("prt", "x").unit.latex == "p"
    assert registry.lookup("pfd", "x").unit.latex == "d"


def test_lookup_fourier_toggle_fallback(tmp_path):
    _write(tmp_path, "shared.yml", "x: {display: 'x', unit: 'd'}\n")
    info = Registry.load(tmp_path).lookup("pfd", "k_x")
    assert info.display.latex == "k_x"
    assert info.unit.latex == "d^{-1}"


def test_lookup_unknown_key_falls_back_to_key(tmp_path):
    info = Registry.load(tmp_path).lookup("pfd", "mystery")
    assert (info.display.latex, info.unit.latex, info.key) == ("mystery", "", "mystery")


def test_prt_species_prefix_normalizes_to_prt(tmp_path):
    _write(tmp_path, "prt.yml", "uy: {display: 'u_y'}\nwx:\n  display: 'W_x'\n  pipeline: ['--derive wx=0.5*m*px^2']\n")
    registry = Registry.load(tmp_path)
    assert registry.lookup("prt.e", "uy").display.latex == "u_y"
    assert registry.derivable_keys("prt.e") == ["wx"]
    assert registry.pipeline("prt.i", "wx") is not None


def test_pipeline_is_parsed(tmp_path):
    _write(tmp_path, "pfd.yml", "a:\n  display: 'a'\n  pipeline: ['--copy a=hx_fc']\n")
    [step] = Registry.load(tmp_path).pipeline("pfd", "a")
    assert isinstance(step, Copy)


def test_entry_without_pipeline_is_not_derivable(tmp_path):
    _write(tmp_path, "pfd.yml", "hx_fc: {display: 'B_x'}\n")
    registry = Registry.load(tmp_path)
    assert registry.pipeline("pfd", "hx_fc") is None
    assert registry.derivable_keys("pfd") == []


def test_empty_file_is_allowed(tmp_path):
    _write(tmp_path, "pfd.yml", "# nothing yet\n")
    assert Registry.load(tmp_path).derivable_keys("pfd") == []


# --- validation ---


@pytest.mark.parametrize(
    "text, match",
    [
        ("a: {display: 'a', colour: red}\n", r"pfd\.yml: a: unknown field"),
        ("a: {unit: 'c'}\n", r"pfd\.yml: a: missing 'display'"),
        ("a: {display: 'a', geometry: cubic}\n", r"pfd\.yml: a: .*geometry"),
        ("a: {display: 1}\n", r"pfd\.yml: a: 'display' must be a string"),
        ("a: 'B_x'\n", r"pfd\.yml: a: expected a mapping"),
        ("a:\n  display: 'a'\n  pipeline: '--pow 2'\n", r"pfd\.yml: a: 'pipeline' must be a list"),
        ("a:\n  display: 'a'\n  pipeline: ['--idx y=abc']\n", r"pfd\.yml: a: step '--idx y=abc'"),
        ("a:\n  display: 'a'\n  pipeline: ['-v y']\n", r"pfd\.yml: a: .*versus"),
        ("a:\n  display: 'a'\n  pipeline: ['--fit 10:20']\n", r"pfd\.yml: a: .*unrecognized"),
        ("on: {display: 'a'}\n", r"pfd\.yml: .*must be a string"),
        ("- a\n- b\n", r"pfd\.yml: expected a mapping"),
    ],
)
def test_invalid_entries(tmp_path, text, match):
    _write(tmp_path, "pfd.yml", text)
    with pytest.raises(RegistryError, match=match):
        Registry.load(tmp_path)


def test_shared_entries_cannot_have_pipelines(tmp_path):
    _write(tmp_path, "shared.yml", "x:\n  display: 'x'\n  pipeline: ['--pow 2']\n")
    with pytest.raises(RegistryError, match=r"shared\.yml: x: .*pipeline"):
        Registry.load(tmp_path)


def test_duplicate_key_rejected(tmp_path):
    _write(tmp_path, "pfd.yml", "a: {display: 'a'}\na: {display: 'b'}\n")
    with pytest.raises(RegistryError, match=r"pfd\.yml.*duplicate key 'a'"):
        Registry.load(tmp_path)


def test_control_character_rejected(tmp_path):
    # double-quoted YAML turns the \t of \text into a tab
    _write(tmp_path, "pfd.yml", 'a: {display: "\\text{e}"}\n')
    with pytest.raises(RegistryError, match=r"pfd\.yml: a: .*single quotes"):
        Registry.load(tmp_path)


def test_missing_registries_dir(tmp_path):
    with pytest.raises(RegistryError, match="nope"):
        Registry.load(tmp_path / "nope")


def test_registries_dir_that_is_a_file(tmp_path):
    path = tmp_path / "file.yml"
    path.write_text("")
    with pytest.raises(RegistryError, match="not a directory"):
        Registry.load(path)
