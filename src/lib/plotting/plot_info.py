from dataclasses import KW_ONLY, dataclass, field
from typing import Any, Callable, Literal

import numpy as np
from matplotlib.typing import LineStyleType

from lib.data.types import VarKey
from lib.latex import Latex
from lib.scale import Scale

type AttrKey = str
type Projection = Literal["rectilinear", "polar"]


@dataclass
class PlotInfo:
    _: KW_ONLY
    subject: str | None = None
    dim_scales: dict[VarKey, Scale] = field(default_factory=dict)
    dim_bounds: dict[VarKey, tuple[float | None, float | None]] = field(default_factory=dict)
    dim_displays: dict[VarKey, Latex] = field(default_factory=dict)
    dim_units: dict[VarKey, Latex] = field(default_factory=dict)
    time_dim: VarKey | None = None
    scalar_coord_values: dict[VarKey, float] = field(default_factory=dict)

    axes_index: tuple[int, int] = (1, 1)
    projection: Projection = field(default="rectilinear", init=False)

    _setter_callbacks: dict[AttrKey | tuple[AttrKey, VarKey], Callable[[Any], None]] = field(default_factory=dict, init=False)

    def set(self, key: AttrKey | tuple[AttrKey, VarKey], value: Any):
        if isinstance(key, str):
            attr_key = key
            setattr(self, key, value)
        else:
            attr_key, dim_key = key
            getattr(self, attr_key)[dim_key] = value

            if key in self._setter_callbacks:
                self._setter_callbacks[key](value)

        if attr_key in self._setter_callbacks:
            self._setter_callbacks[attr_key](value)

    def get_coord_label(self, dim: VarKey) -> Latex:
        display = self.dim_displays.get(dim, f"\\text{{{dim}}}")
        coord_val = self.scalar_coord_values[dim]
        unit = self.dim_units.get(dim, "")
        maybe_space = "\\ " if unit else ""
        return Latex(f"{display} = {coord_val:.3f}{maybe_space}{unit}")

    def get_sublabels(self) -> list[str]:
        return [f"${self.get_coord_label(dim)}$" for dim in self.scalar_coord_values]

    def get_title(self) -> str:
        coord_labels_str = ", ".join(self.get_sublabels())

        if self.subject and coord_labels_str:
            return f"{self.subject} ({coord_labels_str})"
        elif self.subject:
            return self.subject
        else:
            return coord_labels_str

    def get_dim_label(self, dim: VarKey) -> str:
        dim_label = f"${self.dim_displays.get(dim, f'\\text{{{dim}}}')}$"

        if unit := self.dim_units.get(dim):
            dim_label += f" [${unit}$]"

        return dim_label


@dataclass
class PlotInfo2D(PlotInfo):
    _: KW_ONLY
    x_dim: VarKey
    y_dim: VarKey


@dataclass
class LineInfo(PlotInfo2D):
    _: KW_ONLY
    x_data: np.ndarray
    y_data: np.ndarray
    line_style: LineStyleType = "-"


@dataclass
class ImageInfo(PlotInfo2D):
    _: KW_ONLY
    data: np.ndarray
    color_dim: VarKey


@dataclass
class ScatterInfo(PlotInfo2D):
    _: KW_ONLY
    xy_data: np.ndarray
    color_data: np.ndarray | None = None
    color_dim: VarKey | None = None


@dataclass
class PolarMeshInfo(PlotInfo):
    _: KW_ONLY
    data: np.ndarray
    r_vertices: np.ndarray
    theta_vertices: np.ndarray
    r_dim: VarKey
    theta_dim: VarKey
    color_dim: VarKey
    projection: Projection = field(default="polar", init=False)
