from __future__ import annotations

from dataclasses import dataclass

from matplotlib.image import AxesImage
from matplotlib.lines import Line2D

from lib.plotting.plot_info import ImageInfo, LineInfo
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
