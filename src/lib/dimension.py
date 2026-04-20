from __future__ import annotations

from dataclasses import KW_ONLY, dataclass
from typing import Literal

from .latex import Latex

INVERSE_ELECTRON_PLASMA_FREQUENCY = Latex("\\omega_\\text{pe}^{-1}")
ELECTRON_SKIN_DEPTH = Latex("d_\\text{e}")
RADIAN = Latex("\\text{rad}")
SPEED_OF_LIGHT = Latex("c")
ELEMENTARY_CHARGE = Latex("e")

FOURIER_NAME_PREFIX = "k_"


def _toggle_unit_fourier(unit: Latex) -> Latex:
    inverse_suffix = "^{-1}"
    if unit.ends_with(inverse_suffix):
        return unit.remove_suffix(inverse_suffix)
    else:
        return unit.append(inverse_suffix)


type DimensionGeometry = Literal["linear", "polar:r", "polar:theta", "spherical:r", "spherical:theta", "spherical:phi"]


@dataclass(frozen=True)
class Dimension:
    name: Latex
    unit: Latex
    geometry: DimensionGeometry
    _: KW_ONLY
    key: str = None

    def __post_init__(self):
        if self.key is None:
            object.__setattr__(self, "key", self.name.plain)

    def to_axis_label(self) -> str:
        if self.unit.latex:
            return f"${self.name.latex}\\ [{self.unit.latex}]$"
        return f"${self.name.latex}$"

    def get_coordinate_label(self, coord_val: float) -> str:
        return f"${self.name.latex} = {coord_val:.3f}\\ {self.unit.latex}$"

    def toggle_fourier(self) -> Dimension:
        # TODO make t <-> omega
        toggled_unit = _toggle_unit_fourier(self.unit)
        if self.is_fourier():
            return Dimension(self.name.remove_prefix(FOURIER_NAME_PREFIX), toggled_unit, self.geometry)
        else:
            return Dimension(self.name.prepend(FOURIER_NAME_PREFIX), toggled_unit, self.geometry)

    def is_fourier(self) -> bool:
        return self.name.starts_with(FOURIER_NAME_PREFIX)


def check_unit_compatability(dim_1: Dimension, dim_2: Dimension, dest_geometry: str):
    if dim_1.unit != dim_2.unit:
        raise ValueError(f"Dimensions {dim_1.name} and {dim_2.name} have incompatible units for transforming to {dest_geometry} coordinates ({dim_1.unit} and {dim_2.unit})")


DIM_DEFAULTS: dict[str, Dimension] = {}


def _register_default(dim: Dimension) -> None:
    DIM_DEFAULTS[dim.key] = dim


_register_default(Dimension(Latex("x"), ELECTRON_SKIN_DEPTH, "linear"))
_register_default(Dimension(Latex("y"), ELECTRON_SKIN_DEPTH, "linear"))
_register_default(Dimension(Latex("z"), ELECTRON_SKIN_DEPTH, "linear"))
_register_default(Dimension(Latex("t"), INVERSE_ELECTRON_PLASMA_FREQUENCY, "linear"))
_register_default(Dimension(Latex("\\gamma v_x"), SPEED_OF_LIGHT, "linear", key="px"))
_register_default(Dimension(Latex("\\gamma v_y"), SPEED_OF_LIGHT, "linear", key="py"))
_register_default(Dimension(Latex("\\gamma v_z"), SPEED_OF_LIGHT, "linear", key="pz"))
_register_default(Dimension(Latex("\\gamma v_{xy}"), SPEED_OF_LIGHT, "linear", key="pxy"))
_register_default(Dimension(Latex("\\gamma v_{yz}"), SPEED_OF_LIGHT, "linear", key="pyz"))
_register_default(Dimension(Latex("\\gamma v_{zx}"), SPEED_OF_LIGHT, "linear", key="pzx"))
_register_default(Dimension(Latex("q"), ELEMENTARY_CHARGE, "linear"))


def get_default_dim(key: str) -> Dimension:
    """Return the registered default `Dimension` for `key`, or a minimal fallback if unknown.

    If `key` looks like a Fourier-space key (prefix ``k_``) whose base is registered,
    return the Fourier toggle of the base dim so Fourier-space coords loaded directly
    from data inherit the correct unit/geometry.
    """
    if key in DIM_DEFAULTS:
        return DIM_DEFAULTS[key]
    if key.startswith(FOURIER_NAME_PREFIX):
        base_key = key[len(FOURIER_NAME_PREFIX):]
        if base_key in DIM_DEFAULTS:
            return DIM_DEFAULTS[base_key].toggle_fourier()
    return Dimension(Latex(key), Latex(""), "linear", key=key)
