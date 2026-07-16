from dataclasses import KW_ONLY, dataclass, field
from typing import Any, Callable, Literal

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from matplotlib.projections import PolarAxes
from matplotlib.typing import LineStyleType

from lib.latex import Latex
from lib.plotting import plt_util
from lib.plotting.scale import Scale

type DimKey = str
type AttrKey = str
type VarKey = str
type Projection = Literal["rectilinear", "polar"]


@dataclass
class PlotInfo:
    _: KW_ONLY
    subject: str | None = None
    dim_scales: dict[DimKey, Scale] = field(default_factory=dict)
    dim_bounds: dict[DimKey, tuple[float | None, float | None]] = field(default_factory=dict)
    dim_displays: dict[DimKey, Latex] = field(default_factory=dict)
    dim_units: dict[DimKey, Latex] = field(default_factory=dict)
    scalar_coord_values: dict[DimKey, float] = field(default_factory=dict)
    projection: Projection = field(default="rectilinear", init=False)

    _setter_callbacks: dict[AttrKey | tuple[AttrKey, DimKey], Callable[[Any], None]] = field(default_factory=dict, init=False)

    def set(self, key: AttrKey | tuple[AttrKey, DimKey], value: Any):
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

    def get_title(self) -> str:
        coord_labels = []
        for dim, coord_val in self.scalar_coord_values.items():
            dim_display = self.dim_displays.get(dim, f"\\text{{{dim}}}")
            dim_unit = self.dim_units.get(dim, "")
            maybe_space = "\\ " if dim_unit else ""
            coord_labels.append(f"${dim_display} = {coord_val:.3f}{maybe_space}{dim_unit}$")

        coord_labels_str = ", ".join(coord_labels)

        if self.subject and coord_labels_str:
            return f"{self.subject} ({coord_labels_str})"
        elif self.subject:
            return self.subject
        else:
            return coord_labels_str

    def get_dim_label(self, dim: DimKey) -> str:
        dim_label = f"${self.dim_displays.get(dim, f'\\text{{{dim}}}')}$"

        if unit := self.dim_units.get(dim):
            dim_label += f" [${unit}$]"

        return dim_label


@dataclass
class PlotInfo2D(PlotInfo):
    _: KW_ONLY
    x_dim: DimKey
    y_dim: DimKey


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
    color_dim: DimKey


@dataclass
class ScatterInfo(PlotInfo2D):
    _: KW_ONLY
    x_data: np.ndarray
    y_data: np.ndarray
    color_data: np.ndarray | None = None
    color_dim: DimKey | None = None


@dataclass
class PolarMeshInfo(PlotInfo):
    _: KW_ONLY
    data: np.ndarray
    r_vertices: np.ndarray
    theta_vertices: np.ndarray
    r_dim: DimKey
    theta_dim: DimKey
    color_dim: DimKey
    projection: Projection = field(default="polar", init=False)


def setup_fig(plot_info: PlotInfo) -> Figure:
    figure = plt.figure()
    ax = figure.add_subplot(1, 1, 1, projection=plot_info.projection)

    update_title = lambda _=None: ax.set_title(plot_info.get_title())
    plot_info._setter_callbacks["subject"] = update_title
    plot_info._setter_callbacks["dim_displays"] = update_title
    plot_info._setter_callbacks["dim_units"] = update_title
    plot_info._setter_callbacks["scalar_coord_values"] = update_title
    update_title()

    if isinstance(plot_info, PlotInfo2D):
        for dim, set_label in [
            (plot_info.x_dim, ax.set_xlabel),
            (plot_info.y_dim, ax.set_ylabel),
        ]:
            update_label = lambda _=None: set_label(plot_info.get_dim_label(dim))
            plot_info._setter_callbacks[("dim_displays", dim)] = update_label
            plot_info._setter_callbacks[("dim_units", dim)] = update_label
            update_label()

    if isinstance(plot_info, LineInfo):
        [line] = ax.plot(plot_info.x_data, plot_info.y_data, linestyle=plot_info.line_style, scalex=False, scaley=False)
        plot_info._setter_callbacks["x_data"] = line.set_xdata
        plot_info._setter_callbacks["y_data"] = line.set_ydata
        plot_info._setter_callbacks["line_style"] = line.set_linestyle

    if isinstance(plot_info, ImageInfo):
        image = ax.imshow(
            plot_info.data,
            origin="lower",
            extent=(*plot_info.dim_bounds[plot_info.x_dim], *plot_info.dim_bounds[plot_info.y_dim]),
            norm=plot_info.dim_scales[plot_info.color_dim].to_color_norm(),
            interpolation="nearest",
        )
        plot_info._setter_callbacks["data"] = image.set_data

        figure.colorbar(image)
        data_lower, data_upper = plot_info.dim_bounds[plot_info.color_dim]
        plt_util.update_cbar(image, data_min_override=data_lower, data_max_override=data_upper)

    if isinstance(plot_info, ScatterInfo):
        if plot_info.color_dim:
            scatter = ax.scatter(
                plot_info.x_data,
                plot_info.y_data,
                c=plot_info.color_data,
                norm=plot_info.dim_scales[plot_info.color_dim].to_color_norm(),
                s=1,
            )
            plot_info._setter_callbacks["color_data"] = scatter.set_array

            figure.colorbar(scatter, label=plot_info.get_dim_label(plot_info.color_dim))
            data_lower, data_upper = plot_info.dim_bounds[plot_info.color_dim]
            plt_util.update_cbar(scatter, data_min_override=data_lower, data_max_override=data_upper)
        else:
            scatter = ax.scatter(
                plot_info.x_data,
                plot_info.y_data,
                color=ax._get_lines.get_next_color(),
                s=0.5,
            )

        update_data = lambda _=None: scatter.set_offsets(np.array([plot_info.x_data, plot_info.y_data]).T)
        plot_info._setter_callbacks["x_data"] = update_data
        plot_info._setter_callbacks["y_data"] = update_data

    if isinstance(plot_info, PlotInfo2D):
        for dim, set_scale in [
            (plot_info.x_dim, ax.set_xscale),
            (plot_info.y_dim, ax.set_yscale),
        ]:
            update_scale = lambda _=None: set_scale(plot_info.dim_scales[dim].to_axis_scale())
            plot_info._setter_callbacks[("dim_scales", dim)] = update_scale
            update_scale(plot_info.dim_scales[dim])

        for dim, set_bound in [
            (plot_info.x_dim, ax.set_xbound),
            (plot_info.y_dim, ax.set_ybound),
        ]:
            plot_info._setter_callbacks[("dim_bounds", dim)] = set_bound
            set_bound(*plot_info.dim_bounds[dim])

    if isinstance(plot_info, (ScatterInfo, ImageInfo)):
        ax.set_aspect(1 / ax.get_data_ratio())

    if isinstance(plot_info, PolarMeshInfo):
        # FIXME make the labels work
        ax: PolarAxes

        ax.set_rscale(plot_info.dim_scales[plot_info.r_dim].to_axis_scale())

        image = ax.pcolormesh(
            *np.meshgrid(plot_info.theta_vertices, plot_info.r_vertices),
            plot_info.data,
            shading="flat",
            norm=plot_info.dim_scales[plot_info.color_dim].to_color_norm(),
        )
        plot_info._setter_callbacks["data"] = image.set_array

        figure.colorbar(image)
        data_lower, data_upper = plot_info.dim_bounds[plot_info.color_dim]
        plt_util.update_cbar(image, data_min_override=data_lower, data_max_override=data_upper)

    return figure
