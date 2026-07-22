from lib.data.data_with_attrs import Field
from lib.parsing.args_registry import const_arg
from lib.plotting.hook import Hook
from lib.plotting.plot_info import PlotInfo2D


def _get_center(field: Field, dim: str) -> float:
    other_dims = set(field.dims) - {dim}
    summed = field.active_data.sum(other_dims)
    return (summed * field.coordss[dim]).sum(dim) / summed.sum(dim)


def _get_centers(field: Field) -> list[float]:
    return [_get_center(field, dim) for dim in field.dims]


class ShowCom(Hook):
    def post_init_fig(self, message):
        assert isinstance(message.plot_info, PlotInfo2D)

        self.scatter = message.axes.scatter(*_get_centers(message.frame_data), marker="x", label="center of mass")
        message.axes.legend()

    def post_update_fig(self, message):
        assert isinstance(message.plot_info, PlotInfo2D)

        self.scatter.set_offsets([_get_centers(message.frame_data)])

    def get_name_fragments(self) -> list[str]:
        return ["show_com"]


@const_arg(
    flags="--show-com",
    help="show the center of mass",
    dest="hooks",
)
def get() -> ShowCom:
    return ShowCom()
