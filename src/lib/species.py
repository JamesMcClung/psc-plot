from __future__ import annotations

import re
from dataclasses import dataclass

from lib.latex import Latex


@dataclass(frozen=True)
class SpeciesInfo:
    species_key: str
    display: Latex
    q: float
    m: float


_SPECIES_KEY_RE = re.compile(r"^([a-zA-Z]+)(\d+)?$")


def build_species_info(species_key: str, q: float, m: float) -> SpeciesInfo:
    """Construct SpeciesInfo with the standard display convention.

    - species_key matching ``^[a-zA-Z]+$`` (pure letters) is treated as a
      singleton: display is ``\\text{Electrons}`` (q<0) or ``\\text{Ions}`` (q>=0).
    - species_key with a trailing digit suffix (e.g. 'i25') gets a mass-bearing
      display: ``\\text{Ions, } m=25``.
    """
    subject = "Electrons" if q < 0 else "Ions"
    match = _SPECIES_KEY_RE.match(species_key)
    if match and match.group(2) is not None:
        display = Latex(rf"\text{{{subject}, }} m={m:g}")
    else:
        display = Latex(rf"\text{{{subject}}}")
    return SpeciesInfo(species_key=species_key, display=display, q=q, m=m)
