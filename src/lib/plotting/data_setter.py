from __future__ import annotations

from dataclasses import dataclass

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


@dataclass
class ImageSetter(Renderer2):
    image: AxesImage
    info: ImageInfo

    def update(self):
        self.image.set_data(self.info.data)


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
