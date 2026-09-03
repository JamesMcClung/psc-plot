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
from lib.plotting.labeler import SubjectLabeler, UnitLabeler
from lib.plotting.panel import Panel
from lib.plotting.plot_info import ImageInfo, LineInfo, PlotInfo, PlotInfo2D, PlotInfoColor, PlotInfoMaybeColor, PolarMeshInfo, ScatterInfo
from lib.plotting.renderer2 import Renderer2


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


@dataclass
class AxesManagerSingle[A: Axes, PI: PlotInfo](AxesManager):
    ax: A
    info: PI

    def setup_title(self):
        self.panel.wire_title(self.ax.title, self.info)


class AxesManagerSingle2D[PI2D: PlotInfo2D](AxesManagerSingle[Axes, PI2D]):
    def setup(self):
        self.setup_title()
        self.setup_labels()
        self.setup_data()
        self.setup_scales()
        self.setup_bounds()
        return self.panel

    def setup_labels(self):
        UnitLabeler(self.ax.set_xlabel, "x", [self.info]).update()
        UnitLabeler(self.ax.set_ylabel, "y", [self.info]).update()

    def setup_scales(self):
        self.ax.set_xscale(self.info.dim_scales[self.info.x_dim].to_axis_scale())
        self.ax.set_yscale(self.info.dim_scales[self.info.y_dim].to_axis_scale())

    def setup_bounds(self):
        self.ax.set_xlim(*self.info.dim_bounds[self.info.x_dim])
        self.ax.set_ylim(*self.info.dim_bounds[self.info.y_dim])


class AxesManagerSingleLine(AxesManagerSingle2D[LineInfo]):
    def setup_data(self):
        self.panel.setup_and_wire_line(self.ax, self.info)


class AxesManagerSingleImage(AxesManagerSingle2D[ImageInfo]):
    def setup_title(self):
        self.panel.wire_title(self.ax.title)

    def setup_data(self):
        image = self.panel.setup_and_wire_image(self.ax, self.info)
        cbar = setup_colorbar(self.ax, image, self.info)
        self.panel.wire_cbar_label(cbar, self.info)


class AxesManagerSingleScatter(AxesManagerSingle2D[ScatterInfo]):
    def setup_data(self):
        scatter = self.panel.setup_and_wire_scatter(self.ax, self.info)
        if self.info.color_dim:
            cbar = setup_colorbar(self.ax, scatter, self.info)
            self.panel.wire_cbar_label(cbar, self.info)

        self.ax.set_aspect(self.info.get_aspect())


class AxesManagerSinglePolarMesh(AxesManagerSingle[PolarAxes, PolarMeshInfo]):
    def setup(self):
        self.setup_title()
        self.setup_labels()
        self.setup_scales()
        self.setup_data()
        return self.panel

    def setup_labels(self):
        # FIXME make the labels work
        pass

    def setup_bounds(self):
        pass

    def setup_scales(self):
        self.ax.set_rscale(self.info.dim_scales[self.info.r_dim].to_axis_scale())

    def setup_data(self):
        mesh = self.panel.setup_and_wire_polar_mesh(self.ax, self.info)
        cbar = setup_colorbar(self.ax, mesh, self.info)
        self.panel.wire_cbar_label(cbar, self.info)


@dataclass
class AxesManagerMultiLine(AxesManager):
    ax: Axes
    infos: list[LineInfo]
    lines: list[Line2D] = field(init=False, default_factory=list)

    def setup(self):
        self.setup_labels()
        self.setup_data()
        self.setup_title()  # after data, to make sure lines is populated
        self.setup_scales()
        self.setup_bounds()
        return self.panel

    def setup_title(self):
        for info, line in zip(self.infos, self.lines):
            self.panel.wire_legend_label(line, info)
        self.panel.wire_title(self.ax.title)

    def setup_labels(self):
        UnitLabeler(self.ax.set_xlabel, "x", self.infos).update()
        UnitLabeler(self.ax.set_ylabel, "y", self.infos, require_display_match=False).update()

    def setup_scales(self):
        x_scales = [info.dim_scales[info.x_dim] for info in self.infos]
        if (x_scale := _one_or_none(x_scales)) is not None:
            self.ax.set_xscale(x_scale.to_axis_scale())
        else:
            raise NotImplementedError(f"x scales must all be the same, but found {x_scales}")

        y_scales = [info.dim_scales[info.y_dim] for info in self.infos]
        if (y_scale := _one_or_none(y_scales)) is not None:
            self.ax.set_yscale(y_scale.to_axis_scale())
        else:
            raise NotImplementedError(f"y scales must all be the same, but found {y_scales}")

    def setup_bounds(self):
        self.ax.set_xbound(*find_widest_bounds(info.dim_bounds[info.x_dim] for info in self.infos))
        self.ax.set_ybound(*find_widest_bounds(info.dim_bounds[info.y_dim] for info in self.infos))

    def setup_data(self):
        for info in self.infos:
            self.lines.append(self.panel.setup_and_wire_line(self.ax, info))


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


def setup_fig(plot_infos: list[PlotInfo]) -> tuple[Figure, Grid]:
    figure = plt.figure(layout="constrained")

    grid = Grid(figure, plot_infos)
    for loc, infos in grid.infos.items():
        ax = grid.setup_ax(loc)
        manager: AxesManager
        if len(infos) == 1:
            info = infos[0]
            if isinstance(info, LineInfo):
                manager = AxesManagerSingleLine(ax, info)
            elif isinstance(info, ImageInfo):
                manager = AxesManagerSingleImage(ax, info)
            elif isinstance(info, ScatterInfo):
                manager = AxesManagerSingleScatter(ax, info)
            elif isinstance(info, PolarMeshInfo):
                manager = AxesManagerSinglePolarMesh(ax, info)
            else:
                raise TypeError(f"unknown type: {infos.__class__!r}")
        else:
            image_infos = [info for info in infos if isinstance(info, ImageInfo)]
            line_infos = [info for info in infos if isinstance(info, LineInfo)]
            if not image_infos:
                manager = AxesManagerMultiLine(ax, line_infos)
            elif len(image_infos) == 1:
                manager = AxesManagerImageAndLines(ax, image_infos[0], line_infos)
            else:
                raise NotImplementedError("don't yet support multiple non-line plots per axes")

        panel = manager.setup()
        grid.set_panel(loc, panel)

    grid.wire_suptitle()
    grid.update_labels()

    return figure, grid
