"""Registry mapping (prefix, var_name) to display-LaTeX and unit-LaTeX.

Used by loaders (and `--derive`) to populate `Metadata.display_latex`/`unit_latex`
at load time, so plots show e.g. ``B_x`` instead of ``hx_fc`` on axis labels.

This is deliberately separate from `lib.dimension.Dimension`, which handles
*coordinate axes* (with Fourier toggling and unit switching). `VarInfo` only
describes the dependent variable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VarInfo:
    display_latex: str
    unit_latex: str = ""


# --- Field variables ---------------------------------------------------------
# Keyed by (prefix, var_name). PSC normalized units leave `unit_latex` blank;
# users can override with `--unit`.

_PFD: dict[str, VarInfo] = {
    # E field components (edge-centered)
    "ex_ec": VarInfo("E_x"),
    "ey_ec": VarInfo("E_y"),
    "ez_ec": VarInfo("E_z"),
    # B field components (face-centered) — PSC stores B as "h"
    "hx_fc": VarInfo("B_x"),
    "hy_fc": VarInfo("B_y"),
    "hz_fc": VarInfo("B_z"),
    # current density (edge-centered)
    "jx_ec": VarInfo("j_x"),
    "jy_ec": VarInfo("j_y"),
    "jz_ec": VarInfo("j_z"),
    # derived (see lib.derived_field_variables.registry)
    "h2_cc": VarInfo("B^2"),
    "hxz2_cc": VarInfo("B_x^2 + B_z^2"),
    "hxzhat2": VarInfo(r"|\hat{B}_x|^2 + |\hat{B}_z|^2"),
    "hhat2": VarInfo(r"|\hat{B}|^2"),
    "h_cc": VarInfo("B"),
    "div_h_cc": VarInfo(r"\nabla\cdot \vec B"),
    "sy_p": VarInfo("S_y^+"),
    "sy_m": VarInfo("S_y^-"),
    "py_p": VarInfo("P_y^+"),
    "py_m": VarInfo("P_y^-"),
}

_GAUSS: dict[str, VarInfo] = {
    "dive": VarInfo(r"\nabla\cdot\vec E"),
    "rho": VarInfo(r"\rho"),
    "error": VarInfo(r"\rho - \nabla\cdot\vec E"),
}

_CONTINUITY: dict[str, VarInfo] = {
    "d_rho": VarInfo(r"\partial_t \rho"),
    "dt_divj": VarInfo(r"\partial_t \nabla\cdot\vec j"),
    "error": VarInfo(r"\partial_t \rho + \partial_t \nabla\cdot\vec j"),
}


def _moments_for(species: str, subscript: str) -> dict[str, VarInfo]:
    return {
        f"rho_{species}": VarInfo(rf"\rho_\text{{{subscript}}}"),
        f"jx_{species}": VarInfo(rf"j_{{x,\text{{{subscript}}}}}"),
        f"jy_{species}": VarInfo(rf"j_{{y,\text{{{subscript}}}}}"),
        f"jz_{species}": VarInfo(rf"j_{{z,\text{{{subscript}}}}}"),
        f"px_{species}": VarInfo(rf"u_{{x,\text{{{subscript}}}}}"),
        f"py_{species}": VarInfo(rf"u_{{y,\text{{{subscript}}}}}"),
        f"pz_{species}": VarInfo(rf"u_{{z,\text{{{subscript}}}}}"),
        f"txx_{species}": VarInfo(rf"T_{{xx,\text{{{subscript}}}}}"),
        f"tyy_{species}": VarInfo(rf"T_{{yy,\text{{{subscript}}}}}"),
        f"tzz_{species}": VarInfo(rf"T_{{zz,\text{{{subscript}}}}}"),
        f"txy_{species}": VarInfo(rf"T_{{xy,\text{{{subscript}}}}}"),
        f"tyz_{species}": VarInfo(rf"T_{{yz,\text{{{subscript}}}}}"),
        f"tzx_{species}": VarInfo(rf"T_{{zx,\text{{{subscript}}}}}"),
    }


_PFD_MOMENTS: dict[str, VarInfo] = {
    **_moments_for("e", "e"),
    **_moments_for("i", "i"),
    # derived
    "rho": VarInfo(r"\rho"),
}


FIELD_VAR_INFO: dict[tuple[str, str], VarInfo] = {
    **{("pfd", k): v for k, v in _PFD.items()},
    **{("pfd_moments", k): v for k, v in _PFD_MOMENTS.items()},
    **{("gauss", k): v for k, v in _GAUSS.items()},
    **{("continuity", k): v for k, v in _CONTINUITY.items()},
}


# --- Particle variables ------------------------------------------------------
# Keyed by var_name only; particle data has a single prefix ("prt").

PARTICLE_VAR_INFO: dict[str, VarInfo] = {
    "x": VarInfo("x", r"d_\text{e}"),
    "y": VarInfo("y", r"d_\text{e}"),
    "z": VarInfo("z", r"d_\text{e}"),
    "px": VarInfo("u_x", "c"),
    "py": VarInfo("u_y", "c"),
    "pz": VarInfo("u_z", "c"),
    "q": VarInfo("q", "e"),
    "m": VarInfo("m", r"m_\text{e}"),
    "w": VarInfo("w"),
    "id": VarInfo(r"\text{id}"),
    "tag": VarInfo(r"\text{tag}"),
    # derived
    "pxy": VarInfo(r"\sqrt{u_x^2 + u_y^2}", "c"),
    "pyz": VarInfo(r"\sqrt{u_y^2 + u_z^2}", "c"),
    "pzx": VarInfo(r"\sqrt{u_z^2 + u_x^2}", "c"),
    "anisotropy_y_zx": VarInfo(r"u_y^2 / (u_z^2 + u_x^2)"),
    "wx": VarInfo("W_x", r"m_\text{e}c^2"),
    "wy": VarInfo("W_y", r"m_\text{e}c^2"),
    "wz": VarInfo("W_z", r"m_\text{e}c^2"),
    "wxy": VarInfo("W_{xy}", r"m_\text{e}c^2"),
    "wyz": VarInfo("W_{yz}", r"m_\text{e}c^2"),
    "wzx": VarInfo("W_{zx}", r"m_\text{e}c^2"),
    "wxyz": VarInfo("W", r"m_\text{e}c^2"),
    "f": VarInfo("f"),
}


def _fallback(var_name: str) -> VarInfo:
    return VarInfo(rf"\text{{{var_name}}}", "")


def lookup_field(prefix: str | None, var_name: str) -> VarInfo:
    """Look up a field variable by prefix + var_name. Falls back to ``\\text{var_name}`` if missing."""
    if prefix is not None:
        info = FIELD_VAR_INFO.get((prefix, var_name))
        if info is not None:
            return info
    return _fallback(var_name)


def lookup_particle(var_name: str) -> VarInfo:
    """Look up a particle variable. Falls back to the variable name if missing."""
    info = PARTICLE_VAR_INFO.get(var_name)
    if info is not None:
        return info
    return _fallback(var_name)
