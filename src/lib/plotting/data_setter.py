from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from matplotlib.axes import Axes
from matplotlib.collections import PathCollection, QuadMesh
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D

from lib.plotting.plot_info import ImageInfo, LineInfo, PolarMeshInfo, ScatterInfo
from lib.plotting.renderer2 import Renderer2


@dataclass
class LineSetter(Renderer2):
    line: Line2D
    info: LineInfo

    def update(self):
        self.line.set_xdata(self.info.x_data)
        self.line.set_ydata(self.info.y_data)
        self.line.set_linestyle(self.info.line_style)

    @classmethod
    def setup(cls, ax: Axes, info: LineInfo) -> Self:
        [line] = ax.plot(info.x_data, info.y_data, linestyle=info.line_style, scalex=False, scaley=False)
        return cls(line, info)


@dataclass
class ImageSetter(Renderer2):
    image: AxesImage
    info: ImageInfo

    def update(self):
        self.image.set_data(self.info.data)

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
class ScatterSetter(Renderer2):
    scatter: PathCollection
    info: ScatterInfo

    def update(self):
        self.scatter.set_array(self.info.color_data)
        self.scatter.set_offsets(self.info.xy_data)


@dataclass
class PolarMeshSetter(Renderer2):
    mesh: QuadMesh
    info: PolarMeshInfo

    def update(self):
        self.mesh.set_array(self.info.data)
