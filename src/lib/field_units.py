"""Unified registry mapping variable/dimension keys to Dimension objects.

Used by loaders and adaptors to populate `Metadata.var_info`.
"""

from __future__ import annotations

from lib.dimension import (
    ELECTRON_SKIN_DEPTH,
    ELEMENTARY_CHARGE,
    FOURIER_NAME_PREFIX,
    INVERSE_ELECTRON_PLASMA_FREQUENCY,
    SPEED_OF_LIGHT,
    Dimension,
)
from lib.latex import Latex

# --- Coordinate dimension registry --------------------------------------------

DIM_REGISTRY: dict[str, Dimension] = {}


def _register_dim(dim: Dimension) -> None:
    DIM_REGISTRY[dim.key] = dim


_register_dim(Dimension(Latex("x"), ELECTRON_SKIN_DEPTH, "linear"))
_register_dim(Dimension(Latex("y"), ELECTRON_SKIN_DEPTH, "linear"))
_register_dim(Dimension(Latex("z"), ELECTRON_SKIN_DEPTH, "linear"))
_register_dim(Dimension(Latex("t"), INVERSE_ELECTRON_PLASMA_FREQUENCY, "linear"))


# --- Prefixed variable registry -----------------------------------------------


def _dim(display: str, unit: str = "", *, key: str) -> Dimension:
    return Dimension(Latex(display), Latex(unit), "linear", key=key)


_PFD: dict[str, Dimension] = {
    "ex_ec": _dim("E_x", key="ex_ec"),
    "ey_ec": _dim("E_y", key="ey_ec"),
    "ez_ec": _dim("E_z", key="ez_ec"),
    "hx_fc": _dim("B_x", key="hx_fc"),
    "hy_fc": _dim("B_y", key="hy_fc"),
    "hz_fc": _dim("B_z", key="hz_fc"),
    "jx_ec": _dim("j_x", key="jx_ec"),
    "jy_ec": _dim("j_y", key="jy_ec"),
    "jz_ec": _dim("j_z", key="jz_ec"),
    "h2_cc": _dim("B^2", key="h2_cc"),
    "hxz2_cc": _dim("B_x^2 + B_z^2", key="hxz2_cc"),
    "hxzhat2": _dim(r"|\hat{B}_x|^2 + |\hat{B}_z|^2", key="hxzhat2"),
    "hhat2": _dim(r"|\hat{B}|^2", key="hhat2"),
    "h_cc": _dim("B", key="h_cc"),
    "div_h_cc": _dim(r"\nabla\cdot \vec B", key="div_h_cc"),
    "sy_p": _dim("S_y^+", key="sy_p"),
    "sy_m": _dim("S_y^-", key="sy_m"),
    "py_p": _dim("P_y^+", key="py_p"),
    "py_m": _dim("P_y^-", key="py_m"),
}

_GAUSS: dict[str, Dimension] = {
    "dive": _dim(r"\nabla\cdot\vec E", key="dive"),
    "rho": _dim(r"\rho", key="rho"),
    "error": _dim(r"\rho - \nabla\cdot\vec E", key="error"),
}

_CONTINUITY: dict[str, Dimension] = {
    "d_rho": _dim(r"\partial_t \rho", key="d_rho"),
    "dt_divj": _dim(r"\partial_t \nabla\cdot\vec j", key="dt_divj"),
    "error": _dim(r"\partial_t \rho + \partial_t \nabla\cdot\vec j", key="error"),
}


def _moments_for(species: str, subscript: str) -> dict[str, Dimension]:
    return {
        f"rho_{species}": _dim(rf"\rho_\text{{{subscript}}}", key=f"rho_{species}"),
        f"jx_{species}": _dim(rf"j_{{x,\text{{{subscript}}}}}", key=f"jx_{species}"),
        f"jy_{species}": _dim(rf"j_{{y,\text{{{subscript}}}}}", key=f"jy_{species}"),
        f"jz_{species}": _dim(rf"j_{{z,\text{{{subscript}}}}}", key=f"jz_{species}"),
        f"px_{species}": _dim(rf"u_{{x,\text{{{subscript}}}}}", key=f"px_{species}"),
        f"py_{species}": _dim(rf"u_{{y,\text{{{subscript}}}}}", key=f"py_{species}"),
        f"pz_{species}": _dim(rf"u_{{z,\text{{{subscript}}}}}", key=f"pz_{species}"),
        f"txx_{species}": _dim(rf"T_{{xx,\text{{{subscript}}}}}", key=f"txx_{species}"),
        f"tyy_{species}": _dim(rf"T_{{yy,\text{{{subscript}}}}}", key=f"tyy_{species}"),
        f"tzz_{species}": _dim(rf"T_{{zz,\text{{{subscript}}}}}", key=f"tzz_{species}"),
        f"txy_{species}": _dim(rf"T_{{xy,\text{{{subscript}}}}}", key=f"txy_{species}"),
        f"tyz_{species}": _dim(rf"T_{{yz,\text{{{subscript}}}}}", key=f"tyz_{species}"),
        f"tzx_{species}": _dim(rf"T_{{zx,\text{{{subscript}}}}}", key=f"tzx_{species}"),
    }


_PFD_MOMENTS: dict[str, Dimension] = {
    **_moments_for("e", "e"),
    **_moments_for("i", "i"),
    "rho": _dim(r"\rho", key="rho"),
}


_PARTICLE: dict[str, Dimension] = {
    "x": _dim("x", r"d_\text{e}", key="x"),
    "y": _dim("y", r"d_\text{e}", key="y"),
    "z": _dim("z", r"d_\text{e}", key="z"),
    "px": _dim("u_x", "c", key="px"),
    "py": _dim("u_y", "c", key="py"),
    "pz": _dim("u_z", "c", key="pz"),
    "q": _dim("q", "e", key="q"),
    "m": _dim("m", r"m_\text{e}", key="m"),
    "w": _dim("w", key="w"),
    "id": _dim(r"\text{id}", key="id"),
    "tag": _dim(r"\text{tag}", key="tag"),
    "pxy": _dim(r"\sqrt{u_x^2 + u_y^2}", "c", key="pxy"),
    "pyz": _dim(r"\sqrt{u_y^2 + u_z^2}", "c", key="pyz"),
    "pzx": _dim(r"\sqrt{u_z^2 + u_x^2}", "c", key="pzx"),
    "anisotropy_y_zx": _dim(r"u_y^2 / (u_z^2 + u_x^2)", key="anisotropy_y_zx"),
    "wx": _dim("W_x", r"m_\text{e}c^2", key="wx"),
    "wy": _dim("W_y", r"m_\text{e}c^2", key="wy"),
    "wz": _dim("W_z", r"m_\text{e}c^2", key="wz"),
    "wxy": _dim("W_{xy}", r"m_\text{e}c^2", key="wxy"),
    "wyz": _dim("W_{yz}", r"m_\text{e}c^2", key="wyz"),
    "wzx": _dim("W_{zx}", r"m_\text{e}c^2", key="wzx"),
    "wxyz": _dim("W", r"m_\text{e}c^2", key="wxyz"),
    "f": _dim("f", key="f"),
}


PREFIXED_REGISTRY: dict[tuple[str, str], Dimension] = {
    **{("pfd", k): v for k, v in _PFD.items()},
    **{("pfd_moments", k): v for k, v in _PFD_MOMENTS.items()},
    **{("gauss", k): v for k, v in _GAUSS.items()},
    **{("continuity", k): v for k, v in _CONTINUITY.items()},
    **{("prt", k): v for k, v in _PARTICLE.items()},
}


def lookup(prefix: str | None, key: str) -> Dimension:
    """Look up display/unit info for a key, checking prefixed registry then dim registry."""
    if prefix is not None:
        info = PREFIXED_REGISTRY.get((prefix, key))
        if info is not None:
            return info
    if key in DIM_REGISTRY:
        return DIM_REGISTRY[key]
    if key.startswith(FOURIER_NAME_PREFIX):
        # TODO: remove this (can't until registered derived field vars can use Fourier adaptor again)
        base_key = key[len(FOURIER_NAME_PREFIX) :]
        base = None
        if prefix is not None:
            base = PREFIXED_REGISTRY.get((prefix, base_key))
        if base is None:
            base = DIM_REGISTRY.get(base_key)
        if base is not None:
            return base.toggle_fourier()
    return Dimension(Latex(key), Latex(""), "linear", key=key)
