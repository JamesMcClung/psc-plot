from __future__ import annotations

from dataclasses import dataclass

INVERSE_ELECTRON_PLASMA_FREQUENCY = "\\omega_\\text{pe}^{-1}"
ELECTRON_SKIN_DEPTH = "d_\\text{e}"

FOURIER_NAME_PREFIX = "k_"


@dataclass(frozen=True)
class Dimension:
    name: str  # latex-formated, sans '$'
    unit: str  # latex-formated, sans '$'

    def to_axis_label(self) -> str:
        return f"${self.name}\\ [{self.unit}]$"

    def get_coordinate_label(self, coord_val: float) -> str:
        return f"${self.name} = {coord_val:.3f}\\ {self.unit}$"

    def to_fourier(self) -> Dimension:
        # TODO make t <-> omega
        # TODO handle kx -> x
        return Dimension(FOURIER_NAME_PREFIX + self.name, f"{self.unit}^{{-1}}")


DIMENSIONS: dict[str, Dimension] = {}


def register_dimension(dim: Dimension):
    DIMENSIONS[dim.name] = dim


register_dimension(Dimension("x", ELECTRON_SKIN_DEPTH))
register_dimension(Dimension("y", ELECTRON_SKIN_DEPTH))
register_dimension(Dimension("z", ELECTRON_SKIN_DEPTH))
register_dimension(Dimension("t", INVERSE_ELECTRON_PLASMA_FREQUENCY))

for dim in ["x", "y", "z"]:
    register_dimension(DIMENSIONS[dim].to_fourier())
