from lib.data.data_with_attrs import Field
from lib.parsing.args_registry import const_arg
from lib.plotting.frame_data_traits import HasAxes, HasFieldData, assert_impl
from lib.plotting.hook import Hook


def _get_center(field: Field, dim: str) -> float:
    other_dims = set(field.dims) - {dim}
    summed = field.active_data.sum(other_dims)
    return (summed * field.coordss[dim]).sum(dim) / summed.sum(dim)


def _get_centers(field: Field) -> list[float]:
    return [_get_center(field, dim) for dim in field.dims]


class ShowCom(Hook):
    class PostInitData(HasFieldData, HasAxes): ...

    def post_init_fig(self, init_data):
        init_data = assert_impl(init_data, ShowCom.PostInitData)

        data = init_data.data
        assert len(data.dims) == 2
        self.scatter = init_data.axes.scatter(*_get_centers(data), marker="x", label="center of mass")

        init_data.axes.legend()

    class PostUpdateData(HasFieldData): ...

    def post_update_fig(self, update_data):
        update_data = assert_impl(update_data, ShowCom.PostUpdateData)

        self.scatter.set_offsets([_get_centers(update_data.data)])

    def get_name_fragments(self) -> list[str]:
        return ["show_com"]


@const_arg(
    flags="--show-com",
    help="show the center of mass",
    dest="hooks",
)
def get() -> ShowCom:
    return ShowCom()
