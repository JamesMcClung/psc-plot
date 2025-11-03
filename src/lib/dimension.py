from __future__ import annotations

from dataclasses import dataclass

INVERSE_ELECTRON_PLASMA_FREQUENCY = "\\omega_\\text{pe}^{-1}"
ELECTRON_SKIN_DEPTH = "d_\\text{e}"
RADIAN = "\\text{rad}"

FOURIER_NAME_PREFIX = "k_"


def _toggle_unit_fourier(unit: str) -> str:
    inverse_suffix = "^{-1}"
    if unit.endswith(inverse_suffix):
        return unit.removesuffix(inverse_suffix)
    else:
        return unit + inverse_suffix


@dataclass(frozen=True)
class Dimension:
    name: str  # latex-formated, sans '$'
    unit: str  # latex-formated, sans '$'

    def to_axis_label(self) -> str:
        return f"${self.name}\\ [{self.unit}]$"

    def get_coordinate_label(self, coord_val: float) -> str:
        return f"${self.name} = {coord_val:.3f}\\ {self.unit}$"

    def toggle_fourier(self) -> Dimension:
        # TODO make t <-> omega
        toggled_unit = _toggle_unit_fourier(self.unit)
        if self.is_fourier():
            return Dimension(self.name.removeprefix(FOURIER_NAME_PREFIX), toggled_unit)
        else:
            return Dimension(FOURIER_NAME_PREFIX + self.name, toggled_unit)

    def is_fourier(self) -> bool:
        return self.name.startswith(FOURIER_NAME_PREFIX)


DIMENSIONS: dict[str, Dimension] = {}


def register_dimension(dim: Dimension):
    DIMENSIONS[dim.name] = dim


register_dimension(Dimension("x", ELECTRON_SKIN_DEPTH))
register_dimension(Dimension("y", ELECTRON_SKIN_DEPTH))
register_dimension(Dimension("z", ELECTRON_SKIN_DEPTH))
register_dimension(Dimension("t", INVERSE_ELECTRON_PLASMA_FREQUENCY))

for dim in ["x", "y", "z"]:
    register_dimension(DIMENSIONS[dim].toggle_fourier())
