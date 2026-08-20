from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.projections import PolarAxes

from lib.plotting import plt_util
from lib.plotting.data_setter import LineSetter, PolarMeshSetter, ScatterSetter
from lib.plotting.grid import Grid
from lib.plotting.labeler import TreeLabeler
from lib.plotting.panel import Panel
from lib.plotting.plot_info import ImageInfo, LineInfo, PlotInfo, PlotInfo2D, PolarMeshInfo, ScatterInfo
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
        self.panel.title_labeler.update()


class AxesManagerSingle2D[PI2D: PlotInfo2D](AxesManagerSingle[Axes, PI2D]):
    def setup(self):
        self.setup_title()
        self.setup_labels()
        self.setup_data()
        self.setup_scales()
        self.setup_bounds()
        return self.panel

    def setup_labels(self):
        self.ax.set_xlabel(self.info.get_dim_label(self.info.x_dim))
        self.ax.set_ylabel(self.info.get_dim_label(self.info.y_dim))

    def setup_scales(self):
        self.ax.set_xscale(self.info.dim_scales[self.info.x_dim].to_axis_scale())
        self.ax.set_yscale(self.info.dim_scales[self.info.y_dim].to_axis_scale())

    def setup_bounds(self):
        self.ax.set_xlim(*self.info.dim_bounds[self.info.x_dim])
        self.ax.set_ylim(*self.info.dim_bounds[self.info.y_dim])


class AxesManagerSingleLine(AxesManagerSingle2D[LineInfo]):
    def setup_data(self):
        [line] = self.ax.plot(self.info.x_data, self.info.y_data, linestyle=self.info.line_style, scalex=False, scaley=False)
        self.panel.data_setters.append(LineSetter(line, self.info))


class AxesManagerSingleImage(AxesManagerSingle2D[ImageInfo]):
    def setup_data(self):
        image = self.panel.setup_and_wire_image(self.ax, self.info)

        self.ax.figure.colorbar(image)
        data_lower, data_upper = self.info.dim_bounds[self.info.color_dim]
        plt_util.update_cbar(image, data_min_override=data_lower, data_max_override=data_upper)


class AxesManagerSingleScatter(AxesManagerSingle2D[ScatterInfo]):
    def setup_data(self):
        if self.info.color_dim:
            scatter = self.ax.scatter(
                self.info.xy_data[:, 0],
                self.info.xy_data[:, 1],
                c=self.info.color_data,
                norm=self.info.dim_scales[self.info.color_dim].to_color_norm(),
                s=1,
            )

            self.ax.figure.colorbar(scatter, label=self.info.get_dim_label(self.info.color_dim))
            data_lower, data_upper = self.info.dim_bounds[self.info.color_dim]
            plt_util.update_cbar(scatter, data_min_override=data_lower, data_max_override=data_upper)
        else:
            scatter = self.ax.scatter(
                self.info.xy_data[:, 0],
                self.info.xy_data[:, 1],
                color=self.ax._get_lines.get_next_color(),
                s=0.5,
            )
        self.ax.set_aspect(self.info.get_aspect())

        self.panel.data_setters.append(ScatterSetter(scatter, self.info))


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
        mesh = self.ax.pcolormesh(
            *np.meshgrid(self.info.theta_vertices, self.info.r_vertices),
            self.info.data,
            shading="flat",
            norm=self.info.dim_scales[self.info.color_dim].to_color_norm(),
        )
        self.panel.data_setters.append(PolarMeshSetter(mesh, self.info))

        self.ax.figure.colorbar(mesh)
        data_lower, data_upper = self.info.dim_bounds[self.info.color_dim]
        plt_util.update_cbar(mesh, data_min_override=data_lower, data_max_override=data_upper)


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
        self.panel.title_labeler.update()

        self.ax.legend()

    def setup_labels(self):
        x_labels = [info.get_dim_label(info.x_dim) for info in self.infos]
        if (x_label := _one_or_none(x_labels)) is not None:
            self.ax.set_xlabel(x_label)
        else:
            raise NotImplementedError(f"x labels must all be the same, but found {x_labels}")

        y_labels = [info.get_dim_label(info.y_dim) for info in self.infos]
        y_units = [info.dim_units[info.y_dim] for info in self.infos]
        if (y_label := _one_or_none(y_labels)) is not None:
            self.ax.set_ylabel(y_label)
        elif (y_unit := _one_or_none(y_units)) is not None:
            self.ax.set_ylabel(y_unit.maybe_with_dollars())
        else:
            raise NotImplementedError(f"y labels must all be the same unit, but found {y_units}")

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
            [line] = self.ax.plot(info.x_data, info.y_data, linestyle=info.line_style, scalex=False, scaley=False)
            self.panel.data_setters.append(LineSetter(line, info))
            self.lines.append(line)


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
        self.panel.title_labeler.update()

        self.line_ax.legend()

    def setup_labels(self):
        x_labels = [info.get_dim_label(info.x_dim) for info in self.infos]
        if (x_label := _one_or_none(x_labels)) is not None:
            self.image_ax.set_xlabel(x_label)
        else:
            raise NotImplementedError(f"x labels must all be the same, but found {x_labels}")

        self.image_ax.set_ylabel(self.image_info.get_dim_label(self.image_info.y_dim))

        y_labels = [info.get_dim_label(info.y_dim) for info in self.line_infos]
        y_units = [info.dim_units[info.y_dim] for info in self.line_infos]
        if (y_label := _one_or_none(y_labels)) is not None:
            self.line_ax.set_ylabel(y_label)
        elif (y_unit := _one_or_none(y_units)) is not None:
            self.line_ax.set_ylabel(y_unit.maybe_with_dollars())
        else:
            raise NotImplementedError(f"line y labels must all be the same unit, but found {y_units}")

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

        self.cbar = self.image_ax.figure.colorbar(image)
        data_lower, data_upper = self.image_info.dim_bounds[self.image_info.color_dim]
        plt_util.update_cbar(image, data_min_override=data_lower, data_max_override=data_upper)

        for info in self.line_infos:
            [line] = self.line_ax.plot(info.x_data, info.y_data, linestyle=info.line_style, scalex=False, scaley=False)
            self.panel.data_setters.append(LineSetter(line, info))
            self.lines.append(line)


def setup_fig(plot_infos: list[PlotInfo]) -> tuple[Figure, list[Renderer2]]:
    figure = plt.figure(layout="constrained")
    renderers: list[Renderer2] = []

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
        renderers += [panel.title_labeler, *panel.data_setters]

    # lift labels to title
    if len(grid.infos) > 1:
        suptitle_labeler = TreeLabeler(figure.suptitle("").set_text)
        for renderer in renderers:
            if isinstance(renderer, TreeLabeler):
                suptitle_labeler.add_child(renderer)
        renderers.append(suptitle_labeler)
        suptitle_labeler.update()

    return figure, renderers
