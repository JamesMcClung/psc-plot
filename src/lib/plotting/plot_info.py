from abc import ABC, abstractmethod
from dataclasses import KW_ONLY, dataclass, field
from typing import Literal

import numpy as np
from matplotlib.typing import LineStyleType

from lib.data.types import VarKey
from lib.latex import Latex, float_to_latex_str
from lib.scale import Scale

type Projection = Literal["rectilinear", "polar"]


def _format_coord_value(value: float) -> str:
    """Fixed-point (e.g. a time), unless that would hide the value's magnitude (e.g. a small fitted coefficient)."""
    if value == 0 or 1e-3 <= abs(value) < 1e6:
        return f"{value:.3f}"
    return float_to_latex_str(value, ".4g")


@dataclass
class PlotInfo(ABC):
    _: KW_ONLY
    subject_dim: VarKey | None = None
    """The dim that is the plotted variable itself, if any. Its axis (or colorbar) is where the subject belongs."""
    dim_scales: dict[VarKey, Scale] = field(default_factory=dict)
    dim_bounds: dict[VarKey, tuple[float | None, float | None]] = field(default_factory=dict)
    dim_displays: dict[VarKey, Latex] = field(default_factory=dict)
    dim_units: dict[VarKey, Latex] = field(default_factory=dict)
    time_dim: VarKey | None = None
    scalar_coord_values: dict[VarKey, float] = field(default_factory=dict)
    frames_scalar_coord_values: list[dict[VarKey, float]] = field(default_factory=list)
    """`scalar_coord_values` on every frame, known up front, so labels can be placed once for all of them."""

    axes_index: tuple[int, int] = (1, 1)
    projection: Projection = field(default="rectilinear", init=False)

    @property
    def subject(self) -> str | None:
        """What is plotted: the display of the subject dim (without its unit, which belongs to the axis)."""
        if self.subject_dim:
            return self.dim_displays[self.subject_dim].maybe_with_dollars()
        return None

    def get_coord_label(self, dim: VarKey, values: dict[VarKey, float] | None = None) -> Latex:
        """`dim`'s value, as in `values` (by default, the current frame's `scalar_coord_values`)."""
        display = self.dim_displays.get(dim, f"\\text{{{dim}}}")
        coord_val = _format_coord_value(float((self.scalar_coord_values if values is None else values)[dim]))
        unit = self.dim_units.get(dim, "")
        maybe_space = "\\ " if unit else ""
        return Latex(f"{display} = {coord_val}{maybe_space}{unit}")

    def get_frames_sublabels(self) -> dict[VarKey, tuple[str, ...]]:
        """Each scalar coord's sublabel on every frame ("" on frames it's missing from), in order of appearance."""
        framess = self.frames_scalar_coord_values or [self.scalar_coord_values]
        dims = {dim: None for values in framess for dim in values}  # a dict keeps the order
        return {dim: tuple(self.get_coord_label(dim, values).maybe_with_dollars() if dim in values else "" for values in framess) for dim in dims}

    @abstractmethod
    def has_legend(self) -> bool: ...

    @abstractmethod
    def has_colorbar(self) -> bool: ...


@dataclass
class PlotInfo2D(PlotInfo):
    _: KW_ONLY
    x_dim: VarKey
    y_dim: VarKey


@dataclass
class PlotInfoColor(PlotInfo):
    _: KW_ONLY
    color_dim: VarKey


@dataclass
class PlotInfoMaybeColor(PlotInfo):
    _: KW_ONLY
    color_data: np.ndarray | None = None
    color_dim: VarKey | None = None


@dataclass
class LineInfo(PlotInfo2D):
    _: KW_ONLY
    x_data: np.ndarray
    y_data: np.ndarray
    line_style: LineStyleType = "-"

    def has_legend(self) -> bool:
        return True

    def has_colorbar(self) -> bool:
        return False


@dataclass
class ImageInfo(PlotInfo2D, PlotInfoColor):
    _: KW_ONLY
    data: np.ndarray

    def has_legend(self) -> bool:
        return False

    def has_colorbar(self) -> bool:
        return True


@dataclass
class ScatterInfo(PlotInfo2D, PlotInfoMaybeColor):
    _: KW_ONLY
    xy_data: np.ndarray
    list_subject: str | None = None
    """What the list contains (e.g. "Ions"). Not a dim, so it has no axis of its own."""

    @property
    def subject(self) -> str | None:
        return self.list_subject

    def has_legend(self) -> bool:
        return True

    def has_colorbar(self) -> bool:
        return self.color_dim is not None


@dataclass
class PolarMeshInfo(PlotInfoColor):
    _: KW_ONLY
    data: np.ndarray
    r_vertices: np.ndarray
    theta_vertices: np.ndarray
    r_dim: VarKey
    theta_dim: VarKey
    projection: Projection = field(default="polar", init=False)

    def has_legend(self) -> bool:
        return False  # like an image, its colorbar says what it is

    def has_colorbar(self) -> bool:
        return True
