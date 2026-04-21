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


type Geometry = Literal["linear", "polar:r", "polar:theta", "spherical:r", "spherical:theta", "spherical:phi"]


@dataclass(frozen=True)
class Dimension:
    display: Latex
    unit: Latex
    geometry: Geometry | None = None
    _: KW_ONLY
    key: str = None

    def __post_init__(self):
        if self.key is None:
            object.__setattr__(self, "key", self.display.plain)

    def to_axis_label(self) -> str:
        if self.unit.latex:
            return f"${self.display.latex}\\ [{self.unit.latex}]$"
        return f"${self.display.latex}$"

    def get_coordinate_label(self, coord_val: float) -> str:
        return f"${self.display.latex} = {coord_val:.3f}\\ {self.unit.latex}$"

    def toggle_fourier(self) -> Dimension:
        # TODO make t <-> omega
        toggled_unit = _toggle_unit_fourier(self.unit)
        if self.is_fourier():
            return Dimension(self.display.remove_prefix(FOURIER_NAME_PREFIX), toggled_unit, self.geometry)
        else:
            return Dimension(self.display.prepend(FOURIER_NAME_PREFIX), toggled_unit, self.geometry)

    def is_fourier(self) -> bool:
        return self.display.starts_with(FOURIER_NAME_PREFIX)


def check_unit_compatability(dim_1: Dimension, dim_2: Dimension, dest_geometry: str):
    if dim_1.unit != dim_2.unit:
        raise ValueError(f"Dimensions {dim_1.display} and {dim_2.display} have incompatible units for transforming to {dest_geometry} coordinates ({dim_1.unit} and {dim_2.unit})")
