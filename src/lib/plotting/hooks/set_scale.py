from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser
from lib.plotting.frame_data_traits import (
    HasColorNorm,
    HasData,
    HasSpatialScales,
    assert_impl,
    check_impl,
)
from lib.plotting.hook import Hook
from lib.plotting.scale import SCALE_TYPES, Scale


class SetScale(Hook):
    def __init__(self, dim_name: str | None, scale: Scale):
        self.dim_name = dim_name
        self.scale = scale

    def pre_init_fig(self, init_data):
        init_data = assert_impl(init_data, HasData)

        data = init_data.data

        if self.dim_name is None:
            # find and set the dependent scale/norm
            if check_impl(init_data, HasSpatialScales) and init_data.last_spatial_dim_is_dependent:
                init_data.spatial_scales[-1] = self.scale
            elif check_impl(init_data, HasColorNorm) and init_data.color_is_dependent:
                init_data.color_norm = self.scale
            else:
                message = f"dependent scale not found"
                raise Exception(message)
        else:
            spatial_dims = data.metadata.spatial_dims
            color_dim = data.metadata.color_dim

            if self.dim_name in spatial_dims:
                init_data = assert_impl(init_data, HasSpatialScales)
                init_data.spatial_scales[spatial_dims.index(self.dim_name)] = self.scale
            elif self.dim_name == color_dim:
                init_data = assert_impl(init_data, HasColorNorm)
                init_data.color_norm = self.scale
            else:
                message = f"'{self.dim_name}' isn't a dimension"
                raise Exception(message)

    def get_name_fragments(self) -> list[str]:
        maybe_dim_name = f"{self.dim_name}=" if self.dim_name is not None else ""
        return [f"scale_{maybe_dim_name}{self.scale.to_name_fragment_part()}"]


ANY_SCALE_ARGS_FORMAT = "{" + ",".join(scale_type.to_argparse_format() for scale_type in SCALE_TYPES) + "}"
SCALE_FORMAT = f"[dim_name=]{ANY_SCALE_ARGS_FORMAT}"


@arg_parser(
    flags="--scale",
    metavar=SCALE_FORMAT,
    help="set the axis/color scale of the dependent variable or specified dimension (default: linear)",
    dest="hooks",
)
def parse_scale(arg: str) -> Scale:
    if "=" in arg:
        dim_name, scale_arg = parse_util.parse_assignment(arg, SCALE_FORMAT)
        parse_util.parse_identifier(dim_name, "dim_name")
    else:
        dim_name = None
        scale_arg = arg

    for scale_type in SCALE_TYPES:
        maybe_scale = scale_type.try_from_argparse_format(scale_arg)
        if maybe_scale:
            return SetScale(dim_name, maybe_scale)

    parse_util.fail_format(scale_arg, ANY_SCALE_ARGS_FORMAT)
