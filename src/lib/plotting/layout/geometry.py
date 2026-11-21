import math
from dataclasses import dataclass

SIZE_TOLERANCE_DOTS = 0.05
"""Sizes closer than this many output dots are the same size."""


@dataclass(frozen=True)
class Box:
    """A rectangle in the figure, in inches from its bottom left corner."""

    x0: float
    y0: float
    width: float
    height: float

    @property
    def x1(self) -> float:
        return self.x0 + self.width

    @property
    def y1(self) -> float:
        return self.y0 + self.height

    def to_figure_fraction(self, fig_width: float, fig_height: float) -> tuple[float, float, float, float]:
        """`(left, bottom, width, height)` as fractions of the figure, which is what `Axes.set_position` takes."""
        return (self.x0 / fig_width, self.y0 / fig_height, self.width / fig_width, self.height / fig_height)


@dataclass(frozen=True)
class Margins:
    """How far, in inches, something extends past a plot area on each side."""

    left: float = 0.0
    right: float = 0.0
    bottom: float = 0.0
    top: float = 0.0


def sizes_close(a: float, b: float, dpi: float) -> bool:
    """Whether two sizes, in inches, are the same as far as the output can tell. Never compare sizes with `==`."""
    return math.isclose(a, b, rel_tol=0.0, abs_tol=SIZE_TOLERANCE_DOTS / dpi)


def even_figure_size(width: float, height: float, dpi: float) -> tuple[float, float]:
    """Round each side up to an even number of dots, which mp4 (yuv420p) needs."""

    def round_side(inches: float) -> float:
        dots = inches * dpi
        return 2 * math.ceil(dots / 2 - SIZE_TOLERANCE_DOTS) / dpi

    return (round_side(width), round_side(height))
