from dataclasses import dataclass

INVERSE_ELECTRON_PLASMA_FREQUENCY = "\\omega_\\text{pe}^{-1}"
ELECTRON_SKIN_DEPTH = "d_\\text{e}"


@dataclass
class Dimension:
    name: str  # latex-formated, sans '$'
    unit: str  # latex-formated, sans '$'
