from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import Self

import numpy as np
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection, QuadMesh
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D

from lib.plotting.plot_info import ImageInfo, LineInfo, PlotInfo, PolarMeshInfo, ScatterInfo
from lib.plotting.renderer2 import Renderer2


@dataclass
class DataSetter[A: Artist = Artist, I: PlotInfo = PlotInfo](Renderer2):
    artist: A
    info: I

    @classmethod
    @abstractmethod
    def setup(cls, ax: Axes, info: I) -> Self: ...


@dataclass
class LineSetter(DataSetter[Line2D, LineInfo]):
    def update(self):
        self.artist.set_xdata(self.info.x_data)
        self.artist.set_ydata(self.info.y_data)
        self.artist.set_linestyle(self.info.line_style)

    @classmethod
    def setup(cls, ax: Axes, info: LineInfo) -> Self:
        [line] = ax.plot(info.x_data, info.y_data, linestyle=info.line_style, scalex=False, scaley=False)
        return cls(line, info)


@dataclass
class ImageSetter(DataSetter[AxesImage, ImageInfo]):
    def update(self):
        self.artist.set_data(self.info.data)

    @classmethod
    def setup(cls, ax: Axes, info: ImageInfo) -> Self:
        image = ax.imshow(
            info.data,
            origin="lower",
            extent=(*info.dim_bounds[info.x_dim], *info.dim_bounds[info.y_dim]),
            norm=info.dim_scales[info.color_dim].to_color_norm(),
            interpolation="nearest",
            aspect=info.get_aspect(),
        )
        return cls(image, info)


@dataclass
class ScatterSetter(DataSetter[PathCollection, ScatterInfo]):
    def update(self):
        self.artist.set_array(self.info.color_data)
        self.artist.set_offsets(self.info.xy_data)

    @classmethod
    def setup(cls, ax: Axes, info: ScatterInfo) -> Self:
        if info.color_dim:
            scatter = ax.scatter(
                info.xy_data[:, 0],
                info.xy_data[:, 1],
                c=info.color_data,
                norm=info.dim_scales[info.color_dim].to_color_norm(),
                s=1,
            )
        else:
            scatter = ax.scatter(
                info.xy_data[:, 0],
                info.xy_data[:, 1],
                color=ax._get_lines.get_next_color(),
                s=0.5,
            )
        return cls(scatter, info)


@dataclass
class PolarMeshSetter(DataSetter[QuadMesh, PolarMeshInfo]):
    def update(self):
        self.artist.set_array(self.info.data)

    @classmethod
    def setup(cls, ax: Axes, info: PolarMeshInfo) -> Self:
        mesh = ax.pcolormesh(
            *np.meshgrid(info.theta_vertices, info.r_vertices),
            info.data,
            shading="flat",
            norm=info.dim_scales[info.color_dim].to_color_norm(),
        )
        return cls(mesh, info)
