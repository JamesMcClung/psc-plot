from __future__ import annotations

from dataclasses import dataclass

from lib.latex import Latex


@dataclass(frozen=True)
class SpeciesInfo:
    species_key: str
    display: Latex
    q: float
    m: float
