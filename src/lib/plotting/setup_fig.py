from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable

from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.cm import ScalarMappable
from matplotlib.colorbar import Colorbar
from matplotlib.figure import Figure
from matplotlib.projections import PolarAxes

from lib.plotting import plt_util
from lib.plotting.axis_id import AxisId
from lib.plotting.data_setter import DataSetter
from lib.plotting.grid import Grid
from lib.plotting.panel import Panel
from lib.plotting.plot_info import ImageInfo, LineInfo, PlotInfo, PlotInfo2D, PlotInfoColor, PlotInfoMaybeColor, PolarMeshInfo, ScatterInfo


def _one_or_none[T](objs: Iterable[T]) -> T | None:
    one = None
    for obj in objs:
        if one is None:
            one = obj
        elif obj != one:
            return None
    return one


def setup_colorbar(ax: Axes, target: ScalarMappable, info: PlotInfoColor | PlotInfoMaybeColor) -> Colorbar:
    assert info.color_dim
    cbar = ax.figure.colorbar(target)
    data_lower, data_upper = info.dim_bounds[info.color_dim]
    plt_util.update_cbar(target, data_min_override=data_lower, data_max_override=data_upper)
    return cbar


@dataclass
class AxesManager(ABC):
    panel: Panel = field(init=False, default_factory=Panel)

    @abstractmethod
    def setup(self) -> Panel: ...

    @abstractmethod
    def setup_title(self): ...

    @abstractmethod
    def setup_labels(self): ...

    @abstractmethod
    def setup_scales(self): ...

    @abstractmethod
    def setup_bounds(self): ...

    @abstractmethod
    def setup_data(self): ...


def set_scales_xy(ax: Axes, axis_id: AxisId, infos: list[PlotInfo2D]):
    match axis_id:
        case "x":
            scales = [info.dim_scales[info.x_dim] for info in infos]
            set_scale = ax.set_xscale
        case "y":
            scales = [info.dim_scales[info.y_dim] for info in infos]
            set_scale = ax.set_yscale
    if (scale := _one_or_none(scales)) is not None:
        set_scale(scale.to_axis_scale())
    else:
        raise NotImplementedError(f"{axis_id} scales must all be the same, but found {scales}")


def set_scales_rtheta(ax: PolarAxes, infos: list[PolarMeshInfo]):
    r_scales = [info.dim_scales[info.r_dim] for info in infos]
    if (r_scale := _one_or_none(r_scales)) is not None:
        ax.set_rscale(r_scale.to_axis_scale())
    else:
        raise NotImplementedError(f"r scales must all be the same, but found {r_scales}")


def setup_line(panel: Panel, ax: Axes, info: LineInfo):
    setter = DataSetter.dispatch_init(ax, info)
    panel.wire_data_setter(setter)
    panel.wire_legend_label(setter.artist, info)
    return setter


def setup_image(panel: Panel, ax: Axes, info: ImageInfo):
    setter = DataSetter.dispatch_init(ax, info)
    panel.wire_data_setter(setter)
    cbar = setup_colorbar(ax, setter.artist, info)
    panel.wire_cbar_label(cbar, info)
    return setter


def setup_scatter(panel: Panel, ax: Axes, info: ScatterInfo):
    setter = DataSetter.dispatch_init(ax, info)
    panel.wire_data_setter(setter)
    panel.wire_legend_label(setter.artist, info)
    if info.color_dim:
        cbar = setup_colorbar(ax, setter.artist, info)
        panel.wire_cbar_label(cbar, info)

    ax.set_aspect(info.get_aspect())
    return setter


def setup_polar_mesh(panel: Panel, ax: PolarAxes, info: PolarMeshInfo):
    setter = DataSetter.dispatch_init(ax, info)
    panel.wire_data_setter(setter)
    cbar = setup_colorbar(ax, setter.artist, info)
    panel.wire_cbar_label(cbar, info)
    return setter


@dataclass
class AxesManagerImageAndLines(AxesManager):
    image_ax: Axes
    image_info: ImageInfo
    line_infos: list[LineInfo]

    line_ax: Axes = field(init=False)
    infos: list[PlotInfo2D] = field(init=False)

    def __post_init__(self):
        self.line_ax = self.image_ax.twinx()
        self.infos = [self.image_info, *self.line_infos]

    def setup(self):
        self.setup_labels()
        self.setup_data()
        self.setup_title()  # after data to get line info and cbar
        self.setup_scales()
        self.setup_bounds()
        return self.panel

    def setup_title(self):
        self.panel.wire_title(self.image_ax.title)

    def setup_labels(self):
        self.panel.wire_units(self.image_ax, "x", self.infos)
        self.panel.wire_units(self.image_ax, "y", [self.image_info])
        self.panel.wire_units(self.line_ax, "y", self.line_infos, require_display_match=False)

    def setup_scales(self):
        set_scales_xy(self.image_ax, "x", self.infos)
        set_scales_xy(self.image_ax, "y", [self.image_info])
        set_scales_xy(self.line_ax, "y", self.line_infos)

    def setup_bounds(self):
        self.panel.wire_bounds_setter_xy(self.image_ax, "x", self.infos)
        self.panel.wire_bounds_setter_xy(self.image_ax, "y", [self.image_info])
        self.panel.wire_bounds_setter_xy(self.line_ax, "y", self.line_infos)

    def setup_data(self):
        setup_image(self.panel, self.image_ax, self.image_info)
        for info in self.line_infos:
            setup_line(self.panel, self.line_ax, info)


def setup_panel(ax: Axes, infos: list[PlotInfo]) -> Panel:
    panel: Panel
    if len(infos) == 1:
        info = infos[0]
        panel = Panel()

        panel.wire_title(ax.title)

        if isinstance(info, PlotInfo2D):
            panel.wire_units(ax, "x", infos)
            panel.wire_units(ax, "y", infos)

            set_scales_xy(ax, "x", infos)
            set_scales_xy(ax, "y", infos)

            panel.wire_bounds_setter_xy(ax, "x", infos)
            panel.wire_bounds_setter_xy(ax, "y", infos)
        else:
            set_scales_rtheta(ax, infos)

        if isinstance(info, LineInfo):
            setup_line(panel, ax, info)
        elif isinstance(info, ImageInfo):
            setup_image(panel, ax, info)
        elif isinstance(info, ScatterInfo):
            setup_scatter(panel, ax, info)
        elif isinstance(info, PolarMeshInfo):
            setup_polar_mesh(panel, ax, info)
        else:
            raise TypeError(f"unknown type: {infos.__class__!r}")
    else:
        image_infos = [info for info in infos if isinstance(info, ImageInfo)]
        line_infos = [info for info in infos if isinstance(info, LineInfo)]

        if not image_infos:
            panel = Panel()

            panel.wire_units(ax, "x", infos)
            panel.wire_units(ax, "y", infos, require_display_match=False)

            for info in line_infos:
                setup_line(panel, ax, info)

            panel.wire_title(ax.title)

            set_scales_xy(ax, "x", infos)
            set_scales_xy(ax, "y", infos)

            panel.wire_bounds_setter_xy(ax, "x", infos)
            panel.wire_bounds_setter_xy(ax, "y", infos)
        elif len(image_infos) == 1:
            panel = AxesManagerImageAndLines(ax, image_infos[0], line_infos).setup()
        else:
            raise NotImplementedError("don't yet support multiple non-line plots per axes")

    return panel


def setup_fig(plot_infos: list[PlotInfo]) -> tuple[Figure, Grid]:
    figure = plt.figure(layout="constrained")

    grid = Grid(figure, plot_infos)
    for loc, infos in grid.infos.items():
        ax = grid.setup_ax(loc)
        panel = setup_panel(ax, infos)
        grid.set_panel(loc, panel)

    grid.update_labels()
    grid.update_bounds()

    return figure, grid
