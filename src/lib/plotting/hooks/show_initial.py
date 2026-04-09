from lib.data.data_with_attrs import Field
from lib.dimension import DIMENSIONS
from lib.parsing.args_registry import const_arg
from lib.plotting.frame_data_traits import HasAxes, HasData, HasLineType, assert_impl
from lib.plotting.hook import Hook


class ShowInitial(Hook):
    class PreInitData(HasData, HasAxes, HasLineType): ...

    def pre_init_fig(self, init_data):
        init_data = assert_impl(init_data, ShowInitial.PreInitData)

        data = init_data.data
        xdata = data.coordss[data.dims[0]]
        ydata = data.active_data if isinstance(data, Field) else data.data
        time_dim = data.metadata.time_dim
        init_data.axes.plot(xdata, ydata, "-", label=DIMENSIONS[time_dim].get_coordinate_label(data.coordss[time_dim]))

        init_data.line_type = "--"

    class PostInitData(HasAxes): ...

    def post_init_fig(self, init_data):
        init_data = assert_impl(init_data, ShowInitial.PostInitData)
        init_data.axes.legend()


@const_arg(
    flags="--show-initial",
    help="always show the initial data",
    dest="hooks",
)
def get() -> ShowInitial:
    return ShowInitial()
