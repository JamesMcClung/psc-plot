from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass

import numpy as np
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection, QuadMesh
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D

from lib.plotting.plot_info import ImageInfo, LineInfo, PlotInfo, PolarMeshInfo, ScatterInfo


@dataclass
class DataSetter[A: Artist = Artist, I: PlotInfo = PlotInfo]:
    artist: A
    info: I

    def __init__(self, axes: Axes, info: I):
        self.info = info
        self.artist = self.setup_artist(axes, info)

    @staticmethod
    @abstractmethod
    def setup_artist(axes: Axes, info: I) -> A: ...

    @staticmethod
    def dispatch_init(axes: Axes, info: PlotInfo) -> DataSetter:
        if isinstance(info, LineInfo):
            return LineSetter(axes, info)
        if isinstance(info, ImageInfo):
            return ImageSetter(axes, info)
        if isinstance(info, ScatterInfo):
            return ScatterSetter(axes, info)
        if isinstance(info, PolarMeshInfo):
            return PolarMeshSetter(axes, info)
        assert False


class LineSetter(DataSetter[Line2D, LineInfo]):
    def update(self):
        self.artist.set_xdata(self.info.x_data)
        self.artist.set_ydata(self.info.y_data)
        self.artist.set_linestyle(self.info.line_style)

    @staticmethod
    def setup_artist(ax: Axes, info: LineInfo) -> Line2D:
        [line] = ax.plot(info.x_data, info.y_data, linestyle=info.line_style, scalex=False, scaley=False)
        return line


class ImageSetter(DataSetter[AxesImage, ImageInfo]):
    def update(self):
        self.artist.set_data(self.info.data)

    @staticmethod
    def setup_artist(ax: Axes, info: ImageInfo) -> AxesImage:
        return ax.imshow(
            info.data,
            origin="lower",
            extent=(*info.dim_bounds[info.x_dim], *info.dim_bounds[info.y_dim]),
            norm=info.dim_scales[info.color_dim].to_color_norm(),
            interpolation="nearest",
            aspect=info.get_aspect(),
        )


class ScatterSetter(DataSetter[PathCollection, ScatterInfo]):
    def update(self):
        self.artist.set_array(self.info.color_data)
        self.artist.set_offsets(self.info.xy_data)

    @staticmethod
    def setup_artist(ax: Axes, info: ScatterInfo) -> PathCollection:
        if info.color_dim:
            return ax.scatter(
                info.xy_data[:, 0],
                info.xy_data[:, 1],
                c=info.color_data,
                norm=info.dim_scales[info.color_dim].to_color_norm(),
                s=1,
            )
        else:
            return ax.scatter(
                info.xy_data[:, 0],
                info.xy_data[:, 1],
                color=ax._get_lines.get_next_color(),
                s=0.5,
            )


class PolarMeshSetter(DataSetter[QuadMesh, PolarMeshInfo]):
    def update(self):
        self.artist.set_array(self.info.data)

    @staticmethod
    def setup_artist(ax: Axes, info: PolarMeshInfo) -> QuadMesh:
        return ax.pcolormesh(
            *np.meshgrid(info.theta_vertices, info.r_vertices),
            info.data,
            shading="flat",
            norm=info.dim_scales[info.color_dim].to_color_norm(),
        )
