from lib.parsing.args_registry import const_arg
from lib.plotting.hook import Hook
from lib.plotting.plot_info import LineInfo


class ShowInitial(Hook):
    def post_init_fig(self, message):
        assert isinstance(message.plot_info, LineInfo)
        assert message.plot_info.time_dim

        message.axes.plot(message.plot_info.x_data, message.plot_info.y_data, "-", label=message.plot_info.get_coord_label(message.plot_info.time_dim))
        message.plot_info.set("line_style", "--")

    def post_init_fig(self, message):
        message.axes.legend()


@const_arg(
    flags="--show-initial",
    help="always show the initial data",
    dest="hooks",
)
def get() -> ShowInitial:
    return ShowInitial()
