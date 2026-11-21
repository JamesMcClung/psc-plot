from dataclasses import dataclass

DEFAULT_DPI = 100.0
"""matplotlib's own default, made explicit: the layout's auto sizes depend on it."""


@dataclass(frozen=True)
class FigSizeSpec:
    """The figure's size in inches. A side that is `None` is auto: computed from the plots."""

    width: float | None
    height: float | None


@dataclass(frozen=True)
class LayoutOptions:
    figsize: FigSizeSpec
    dpi: float
