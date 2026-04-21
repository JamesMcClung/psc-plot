"""Unified registry mapping variable/dimension keys to Dimension objects.

Used by loaders and adaptors to populate `Metadata.var_info`.
"""

from __future__ import annotations

from lib.dimension import (
    ELECTRON_MASS,
    ELECTRON_SKIN_DEPTH,
    ELEMENTARY_CHARGE,
    FOURIER_KEY_PREFIX,
    INVERSE_ELECTRON_PLASMA_FREQUENCY,
    SPEED_OF_LIGHT,
    Geometry,
    VarInfo,
)
from lib.file_util import Prefix
from lib.latex import Latex

_REGISTRY: dict[tuple[str | None, str], VarInfo] = {}


def _register(prefix: str | Prefix, key: str, display: str | Latex, *, unit: str | Latex = "", geometry: Geometry | None = None):
    if isinstance(display, str):
        display = Latex(display)
    if isinstance(unit, str):
        unit = Latex(unit)
    _REGISTRY[(prefix, key)] = VarInfo(display, unit, geometry, key=key)


_register(None, "x", "x", unit=ELECTRON_SKIN_DEPTH, geometry="linear")
_register(None, "y", "y", unit=ELECTRON_SKIN_DEPTH, geometry="linear")
_register(None, "z", "z", unit=ELECTRON_SKIN_DEPTH, geometry="linear")
_register(None, "t", "t", unit=INVERSE_ELECTRON_PLASMA_FREQUENCY, geometry="linear")


_register("pfd", "ex_ec", "E_x")
_register("pfd", "ey_ec", "E_y")
_register("pfd", "ez_ec", "E_z")
_register("pfd", "hx_fc", "B_x")
_register("pfd", "hy_fc", "B_y")
_register("pfd", "hz_fc", "B_z")
_register("pfd", "jx_ec", "j_x")
_register("pfd", "jy_ec", "j_y")
_register("pfd", "jz_ec", "j_z")

_register("pfd", "h2_cc", "B^2")
_register("pfd", "hxz2_cc", "B_x^2 + B_z^2")
_register("pfd", "hxzhat2", r"|\hat{B}_x|^2 + |\hat{B}_z|^2")
_register("pfd", "hhat2", r"|\hat{B}|^2")
_register("pfd", "h_cc", "B")
_register("pfd", "div_h_cc", r"\nabla\cdot \vec B")
_register("pfd", "sy_p", "S_y^+")
_register("pfd", "sy_m", "S_y^-")
_register("pfd", "py_p", "P_y^+")
_register("pfd", "py_m", "P_y^-")


_register("gauss", "dive", r"\nabla\cdot\vec E")
_register("gauss", "rho", r"\rho")
_register("gauss", "error", r"\rho - \nabla\cdot\vec E")


_register("continuity", "d_rho", r"\partial_t \rho")
_register("continuity", "dt_divj", r"\partial_t \nabla\cdot\vec j")
_register("continuity", "error", r"\partial_t \rho + \partial_t \nabla\cdot\vec j")


for species in ["e", "i"]:
    _register("pfd_moments", f"rho_{species}", rf"\rho_\text{{{species}}}")
    _register("pfd_moments", f"jx_{species}", rf"j_{{x,\text{{{species}}}}}")
    _register("pfd_moments", f"jy_{species}", rf"j_{{y,\text{{{species}}}}}")
    _register("pfd_moments", f"jz_{species}", rf"j_{{z,\text{{{species}}}}}")
    _register("pfd_moments", f"px_{species}", rf"u_{{x,\text{{{species}}}}}", unit=SPEED_OF_LIGHT)
    _register("pfd_moments", f"py_{species}", rf"u_{{y,\text{{{species}}}}}", unit=SPEED_OF_LIGHT)
    _register("pfd_moments", f"pz_{species}", rf"u_{{z,\text{{{species}}}}}", unit=SPEED_OF_LIGHT)
    _register("pfd_moments", f"txx_{species}", rf"T_{{xx,\text{{{species}}}}}")
    _register("pfd_moments", f"tyy_{species}", rf"T_{{yy,\text{{{species}}}}}")
    _register("pfd_moments", f"tzz_{species}", rf"T_{{zz,\text{{{species}}}}}")
    _register("pfd_moments", f"txy_{species}", rf"T_{{xy,\text{{{species}}}}}")
    _register("pfd_moments", f"tyz_{species}", rf"T_{{yz,\text{{{species}}}}}")
    _register("pfd_moments", f"tzx_{species}", rf"T_{{zx,\text{{{species}}}}}")

_register("pfd_moments", "rho", r"\rho")


_register("prt", "x", "x", unit=ELECTRON_SKIN_DEPTH)
_register("prt", "y", "y", unit=ELECTRON_SKIN_DEPTH)
_register("prt", "z", "z", unit=ELECTRON_SKIN_DEPTH)
_register("prt", "px", "u_x", unit=SPEED_OF_LIGHT)
_register("prt", "py", "u_y", unit=SPEED_OF_LIGHT)
_register("prt", "pz", "u_z", unit=SPEED_OF_LIGHT)
_register("prt", "q", "q", unit=ELEMENTARY_CHARGE)
_register("prt", "m", "m", unit=ELECTRON_MASS)
_register("prt", "w", "w")
_register("prt", "id", r"\text{id}")
_register("prt", "tag", r"\text{tag}")

_register("prt", "pxy", r"\sqrt{u_x^2 + u_y^2}", unit=SPEED_OF_LIGHT)
_register("prt", "pyz", r"\sqrt{u_y^2 + u_z^2}", unit=SPEED_OF_LIGHT)
_register("prt", "pzx", r"\sqrt{u_z^2 + u_x^2}", unit=SPEED_OF_LIGHT)
_register("prt", "anisotropy_y_zx", r"u_y^2 / (u_z^2 + u_x^2)")
_register("prt", "wx", "W_x")
_register("prt", "wy", "W_y")
_register("prt", "wz", "W_z")
_register("prt", "wxy", "W_{xy}")
_register("prt", "wyz", "W_{yz}")
_register("prt", "wzx", "W_{zx}")
_register("prt", "wxyz", "W")
_register("prt", "f", "f")


def lookup(prefix: str | None, key: str) -> VarInfo:
    """Look up display/unit info for a key, checking prefixed registry then dim registry."""
    if (prefix, key) in _REGISTRY:
        return _REGISTRY[(prefix, key)]

    if (None, key) in _REGISTRY:
        return _REGISTRY[(None, key)]

    if key.startswith(FOURIER_KEY_PREFIX):
        # TODO: remove this (can't until registered derived field vars can use Fourier adaptor again)
        base_key = key[len(FOURIER_KEY_PREFIX) :]
        base = _REGISTRY.get((prefix, base_key))
        if not base:
            base = _REGISTRY.get((None, base_key))
        if base:
            return base.toggle_fourier()

    return VarInfo(Latex(key), Latex(""), key=key)
