from dataclasses import dataclass, field

from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.colorbar import Colorbar
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.text import Text

from lib.plotting.data_setter import ImageSetter, LineSetter
from lib.plotting.labeler import Labeler, SubjectAndUnitLabeler, SubjectLabeler, UnitLabeler
from lib.plotting.plot_info import ImageInfo, LineInfo, PlotInfo, PlotInfoColor
from lib.plotting.renderer2 import Renderer2


@dataclass
class Panel:
    title_labeler: SubjectLabeler | None = field(init=False, default=None)
    legend_labelers: list[SubjectLabeler] = field(init=False, default_factory=list)
    cbar_labeler: Labeler | None = field(init=False, default=None)
    data_setters: list[Renderer2] = field(init=False, default_factory=list)

    def wire_title(self, title: Text, info: PlotInfo | None = None):
        self.title_labeler = SubjectLabeler(title.set_text, info)
        for legend_labeler in self.legend_labelers:
            self.title_labeler.add_child(legend_labeler)
        if self.cbar_labeler and isinstance(self.cbar_labeler, SubjectAndUnitLabeler):
            self.title_labeler.add_child(self.cbar_labeler.subject_labeler)

    def wire_legend_label(self, artist: Artist, info: PlotInfo):
        legend_labeler = SubjectLabeler(artist.set_label, info)
        self.legend_labelers.append(legend_labeler)
        if self.title_labeler:
            self.title_labeler.add_child(legend_labeler)

    def wire_cbar_label(self, cbar: Colorbar, info: PlotInfoColor):
        is_subject = info.dim_displays[info.color_dim].maybe_with_dollars() == info.subject
        if is_subject:
            self.cbar_labeler = SubjectAndUnitLabeler(cbar.set_label, "color", info)
            if self.title_labeler:
                self.title_labeler.add_child(self.cbar_labeler.subject_labeler)
        else:
            self.cbar_labeler = UnitLabeler(cbar.set_label, "color", [info])

    def setup_and_wire_image(self, ax: Axes, info: ImageInfo) -> AxesImage:
        setter = ImageSetter.setup(ax, info)
        self.data_setters.append(setter)
        return setter.image

    def setup_and_wire_line(self, ax: Axes, info: LineInfo) -> Line2D:
        setter = LineSetter.setup(ax, info)
        self.data_setters.append(setter)
        return setter.line
