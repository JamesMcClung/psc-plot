from dataclasses import dataclass, field

from matplotlib.artist import Artist
from matplotlib.text import Text

from lib.plotting.labeler import TreeLabeler
from lib.plotting.plot_info import PlotInfo
from lib.plotting.renderer2 import Renderer2


@dataclass
class Panel:
    title_labeler: TreeLabeler | None = field(init=False, default=None)
    legend_labelers: list[TreeLabeler] = field(init=False, default_factory=list)
    data_setters: list[Renderer2] = field(init=False, default_factory=list)

    def wire_title(self, title: Text, info: PlotInfo | None = None):
        self.title_labeler = TreeLabeler(title.set_text, info)
        for legend_labeler in self.legend_labelers:
            self.title_labeler.add_child(legend_labeler)

    def wire_legend_label(self, artist: Artist, info: PlotInfo):
        legend_labeler = TreeLabeler(artist.set_label, info)
        self.legend_labelers.append(legend_labeler)
        if self.title_labeler:
            self.title_labeler.add_child(legend_labeler)
