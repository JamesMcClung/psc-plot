from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable

from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.cm import ScalarMappable
from matplotlib.colorbar import Colorbar
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.projections import PolarAxes

from lib.plotting import plt_util
from lib.plotting.grid import Grid
from lib.plotting.labeler import UnitLabeler
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


def find_widest_bounds(boundss: Iterable[tuple[float | None, float | None]]) -> tuple[float | None, float | None]:
    lowest_bound = None
    highest_bound = None

    for bounds in boundss:
        if lowest_bound is None:
            lowest_bound = bounds[0]
        elif bounds[0] is not None and lowest_bound > bounds[0]:
            lowest_bound = bounds[0]

        if highest_bound is None:
            highest_bound = bounds[1]
        elif bounds[1] is not None and highest_bound < bounds[1]:
            highest_bound = bounds[1]

    return (lowest_bound, highest_bound)


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


def setup_labels(ax: Axes, infos: list[PlotInfo]):
    if all(isinstance(info, PlotInfo2D) for info in infos):
        UnitLabeler(ax.set_xlabel, "x", infos).update()
        UnitLabeler(ax.set_ylabel, "y", infos, require_display_match=False).update()
    elif all(isinstance(info, PolarMeshInfo) for info in infos):
        pass
    else:
        assert False


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


def setup_bounds_xy(ax: Axes, infos: list[PlotInfo2D]):
    ax.set_xlim(*find_widest_bounds(info.dim_bounds[info.x_dim] for info in infos))
    ax.set_ylim(*find_widest_bounds(info.dim_bounds[info.y_dim] for info in infos))


def setup_bounds(ax: Axes, infos: list[PlotInfo]):
    if all(isinstance(info, PlotInfo2D) for info in infos):
        setup_bounds_xy(ax, infos)
    elif all(isinstance(info, PolarMeshInfo) for info in infos):
        pass
    else:
        assert False


def setup_lone_line(panel: Panel, ax: Axes, info: LineInfo):
    panel.setup_and_wire_line(ax, info)


def setup_lone_image(panel: Panel, ax: Axes, info: ImageInfo):
    image = panel.setup_and_wire_image(ax, info)
    cbar = setup_colorbar(ax, image, info)
    panel.wire_cbar_label(cbar, info)


def setup_lone_scatter(panel: Panel, ax: Axes, info: ScatterInfo):
    scatter = panel.setup_and_wire_scatter(ax, info)
    if info.color_dim:
        cbar = setup_colorbar(ax, scatter, info)
        panel.wire_cbar_label(cbar, info)

    ax.set_aspect(info.get_aspect())


def setup_lone_polar_mesh(panel: Panel, ax: PolarAxes, info: PolarMeshInfo):
    mesh = panel.setup_and_wire_polar_mesh(ax, info)
    cbar = setup_colorbar(ax, mesh, info)
    panel.wire_cbar_label(cbar, info)


@dataclass
class AxesManagerImageAndLines(AxesManager):
    image_ax: Axes
    image_info: ImageInfo
    line_infos: list[LineInfo]
    lines: list[Line2D] = field(init=False, default_factory=list)

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
        for info, line in zip(self.line_infos, self.lines):
            self.panel.wire_legend_label(line, info)
        self.panel.wire_cbar_label(self.cbar, self.image_info)
        self.panel.wire_title(self.image_ax.title)

    def setup_labels(self):
        UnitLabeler(self.image_ax.set_xlabel, "x", self.infos).update()
        UnitLabeler(self.image_ax.set_ylabel, "y", [self.image_info]).update()
        UnitLabeler(self.line_ax.set_ylabel, "y", self.line_infos, require_display_match=False).update()

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
        self.image_ax.set_xlim(*find_widest_bounds(info.dim_bounds[info.x_dim] for info in self.infos))
        self.image_ax.set_ylim(*self.image_info.dim_bounds[self.image_info.y_dim])
        self.line_ax.set_ylim(*find_widest_bounds(info.dim_bounds[info.y_dim] for info in self.line_infos))

    def setup_data(self):
        image = self.panel.setup_and_wire_image(self.image_ax, self.image_info)
        self.cbar = setup_colorbar(self.image_ax, image, self.image_info)

        for info in self.line_infos:
            self.lines.append(self.panel.setup_and_wire_line(self.line_ax, info))


def setup_panel(ax: Axes, infos: list[PlotInfo]) -> Panel:
    panel: Panel
    if len(infos) == 1:
        info = infos[0]
        panel = Panel()

        panel.wire_title(ax.title, info)
        setup_labels(ax, infos)
        setup_scales(ax, infos)
        setup_bounds(ax, infos)

        if isinstance(info, LineInfo):
            setup_lone_line(panel, ax, info)
        elif isinstance(info, ImageInfo):
            setup_lone_image(panel, ax, info)
        elif isinstance(info, ScatterInfo):
            setup_lone_scatter(panel, ax, info)
        elif isinstance(info, PolarMeshInfo):
            setup_lone_polar_mesh(panel, ax, info)
        else:
            raise TypeError(f"unknown type: {infos.__class__!r}")
    else:
        image_infos = [info for info in infos if isinstance(info, ImageInfo)]
        line_infos = [info for info in infos if isinstance(info, LineInfo)]

        if not image_infos:
            panel = Panel()

            setup_labels(ax, line_infos)

            for info in line_infos:
                line = panel.setup_and_wire_line(ax, info)
                panel.wire_legend_label(line, info)

            panel.wire_title(ax.title)

            setup_scales(ax, line_infos)
            setup_bounds(ax, infos)
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

    return figure, grid
