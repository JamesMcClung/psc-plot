from dataclasses import replace

from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import DataWithAttrs
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser
from lib.scale import SCALE_TYPES, Scale


class SetScale(MetadataAdaptor):
    def __init__(self, key: str | None, scale: Scale):
        self.key = key
        self.scale = scale

    def apply(self, data: DataWithAttrs) -> DataWithAttrs:
        key = self.key or data.metadata.active_key
        info = replace(data.metadata.var_infos[key], scale=self.scale)
        return data.with_info(key, info)

    def get_name_fragments(self) -> list[str]:
        maybe_dim_name = f"{self.key}=" if self.key is not None else ""
        return [f"scale_{maybe_dim_name}{self.scale.to_name_fragment_part()}"]


ANY_SCALE_ARGS_FORMAT = "{" + ",".join(scale_type.to_argparse_format() for scale_type in SCALE_TYPES) + "}"
SCALE_FORMAT = f"[var_key=]{ANY_SCALE_ARGS_FORMAT}"


@arg_parser(
    flags="--scale",
    metavar=SCALE_FORMAT,
    help="set the axis scale or color normalization of the given quantity (default is 'linear')",
    dest="adaptors",
)
def parse_scale(arg: str) -> Scale:
    if "=" in arg:
        var_key, scale_arg = parse_util.parse_assignment(arg, SCALE_FORMAT)
        parse_util.parse_identifier(var_key, "var_key")
    else:
        var_key = None
        scale_arg = arg

    for scale_type in SCALE_TYPES:
        maybe_scale = scale_type.try_from_argparse_format(scale_arg)
        if maybe_scale:
            return SetScale(var_key, maybe_scale)

    parse_util.fail_format(scale_arg, ANY_SCALE_ARGS_FORMAT)
