from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser
from lib.plotting.frame_data_traits import HasAxes, assert_impl
from lib.plotting.hook import Hook


class VLine(Hook):
    def __init__(self, pos: float, label: str | None):
        self.pos = pos
        self.label = label

    class InitData(HasAxes): ...

    def pre_init_fig(self, init_data):
        init_data = assert_impl(init_data, VLine.InitData)

        lower_spine = init_data.axes.spines["bottom"]
        init_data.axes.axvline(
            self.pos,
            color="lightgray",
            linewidth=lower_spine.get_linewidth(),
        )

    def post_init_fig(self, init_data):
        if not self.label:
            return

        init_data = assert_impl(init_data, VLine.InitData)

        lower_spine = init_data.axes.spines["bottom"]

        init_data.axes.text(
            self.pos,
            init_data.axes.get_ybound()[0],
            self.label,
            horizontalalignment="center",
            verticalalignment="baseline",
            bbox=dict(
                boxstyle="round",
                facecolor=(1.0, 1.0, 1.0),
                edgecolor=lower_spine.get_edgecolor(),
                linewidth=lower_spine.get_linewidth(),
            ),
        )


VLINE_FORMAT = "pos[=label]"


@arg_parser(
    flags="--vline",
    metavar=VLINE_FORMAT,
    help="(1d only) put a vertical line at the given pos, optionally with a given label",
    dest="hooks",
)
def parse_vline(arg: str) -> VLine:
    if "=" in arg:
        pos_arg, label = parse_util.parse_assignment(arg, VLINE_FORMAT)
    else:
        pos_arg, label = arg, None

    pos = parse_util.parse_number(pos_arg, "pos", float)

    return VLine(pos, label)
