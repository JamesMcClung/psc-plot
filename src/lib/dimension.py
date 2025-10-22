from dataclasses import dataclass

INVERSE_ELECTRON_PLASMA_FREQUENCY = "\\omega_\\text{pe}^{-1}"
ELECTRON_SKIN_DEPTH = "d_\\text{e}"


@dataclass(frozen=True)
class Dimension:
    name: str  # latex-formated, sans '$'
    unit: str  # latex-formated, sans '$'

    def to_axis_label(self) -> str:
        return f"${self.name}\\ [{self.unit}]$"

    def get_coordinate_label(self, coord_val: float) -> str:
        return f"${self.name} = {coord_val:.3f}\\ {self.unit}$"


DIMENSIONS: dict[str, Dimension] = {}


def register_dimension(dim: Dimension):
    DIMENSIONS[dim.name] = dim


register_dimension(Dimension("x", ELECTRON_SKIN_DEPTH))
register_dimension(Dimension("y", ELECTRON_SKIN_DEPTH))
register_dimension(Dimension("z", ELECTRON_SKIN_DEPTH))
register_dimension(Dimension("t", INVERSE_ELECTRON_PLASMA_FREQUENCY))
