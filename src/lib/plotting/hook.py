from dataclasses import dataclass

from matplotlib.axes import Axes

from lib.data.data_with_attrs import DataWithAttrs
from lib.has_name_fragments import HasNameFragments
from lib.plotting.plot_info import PlotInfo


@dataclass(kw_only=True)
class DrawMessage:
    plot_info: PlotInfo
    axes: Axes
    frame_data: DataWithAttrs


class Hook(HasNameFragments):
    def post_init_fig(self, message: DrawMessage):
        pass

    def post_update_fig(self, message: DrawMessage):
        pass
