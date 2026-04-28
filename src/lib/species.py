from __future__ import annotations

from dataclasses import dataclass

from lib.latex import Latex


@dataclass(frozen=True)
class SpeciesInfo:
    species_key: str
    display: Latex
    q: float
    m: float


def build_species_display(subject: str, show_q: float | None = None, show_m: float | None = None) -> Latex:
    """Wraps `subject` in `\\text` and appends optional `q` and/or `m` info."""
    display = rf"\text{{{subject}}}"
    if show_q is not None:
        q_char = "+" if show_q > 0 else "-"
        q_mag = int(abs(show_q))
        display += rf"^{{{q_mag if q_mag > 1 else ""}{q_char}}}"
    if show_m is not None:
        display += rf"_{{{show_m:g}}}"
    return Latex(display)
