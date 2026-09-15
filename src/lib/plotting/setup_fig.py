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


def setup_scales_xy(ax: Axes, infos: list[PlotInfo2D]):
    x_scales = [info.dim_scales[info.x_dim] for info in infos]
    if (x_scale := _one_or_none(x_scales)) is not None:
        ax.set_xscale(x_scale.to_axis_scale())
    else:
        raise NotImplementedError(f"x scales must all be the same, but found {x_scales}")

    y_scales = [info.dim_scales[info.y_dim] for info in infos]
    if (y_scale := _one_or_none(y_scales)) is not None:
        ax.set_yscale(y_scale.to_axis_scale())
    else:
        raise NotImplementedError(f"y scales must all be the same, but found {y_scales}")


def setup_scales_rtheta(ax: PolarAxes, infos: list[PolarMeshInfo]):
    r_scales = [info.dim_scales[info.r_dim] for info in infos]
    if (r_scale := _one_or_none(r_scales)) is not None:
        ax.set_rscale(r_scale.to_axis_scale())
    else:
        raise NotImplementedError(f"r scales must all be the same, but found {r_scales}")


def setup_scales(ax: Axes, infos: list[PlotInfo]):
    if all(isinstance(info, PlotInfo2D) for info in infos):
        return setup_scales_xy(ax, infos)
    elif all(isinstance(info, PolarMeshInfo) for info in infos):
        assert isinstance(ax, PolarAxes)
        return setup_scales_rtheta(ax, infos)
    else:
        assert False


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
        x_scales = [info.dim_scales[info.x_dim] for info in self.infos]
        if (x_scale := _one_or_none(x_scales)) is not None:
            self.image_ax.set_xscale(x_scale.to_axis_scale())
        else:
            raise NotImplementedError(f"x scales must all be the same, but found {x_scales}")

        self.image_ax.set_yscale(self.image_info.dim_scales[self.image_info.y_dim].to_axis_scale())

        y_scales = [info.dim_scales[info.y_dim] for info in self.line_infos]
        if (y_scale := _one_or_none(y_scales)) is not None:
            self.line_ax.set_yscale(y_scale.to_axis_scale())
        else:
            raise NotImplementedError(f"y scales must all be the same, but found {y_scales}")

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

        setup_scales(ax, infos)

        if isinstance(info, PlotInfo2D):
            panel.wire_bounds_setter_xy(ax, "x", infos)
            panel.wire_bounds_setter_xy(ax, "y", infos)

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

            setup_scales(ax, line_infos)
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
