import argparse

from .. import bp_util, plugins_bp
from ..animation import Animation, BpAnimation1d, BpAnimation2d
from ..bp_util import BP_DIMS, BpDim
from ..file_util import BP_PREFIXES
from . import args_base

__all__ = ["add_subparsers_bp", "ArgsBp"]


def parse_roll(arg: str) -> plugins_bp.Roll:
    split_str = arg.split("=")

    if len(split_str) != 2:
        raise argparse.ArgumentTypeError(f"Expected value of form 'dim_name=window_size'; got '{arg}'")

    [dim_name, window_size] = split_str

    if dim_name not in BP_DIMS:
        raise argparse.ArgumentTypeError(f"Expected dim_name to be one of {BP_DIMS}; got '{dim_name}'")

    try:
        window_size = int(window_size)
    except:
        raise argparse.ArgumentTypeError(f"Expected window_size to be an integer; got '{window_size}'")

    return plugins_bp.Roll(dim_name, window_size)


class ArgsBp(args_base.ArgsTyped):
    variable: str
    versus_1d: BpDim | None
    versus_2d: tuple[BpDim, BpDim] | None
    plugins: list[plugins_bp.PluginBp]

    @property
    def save_name(self) -> str:
        if self.versus_1d:
            versus = self.versus_1d
        else:
            versus = "".join(self.versus_2d)
        return f"{self.prefix}-{self.variable}-vs_{versus}.mp4"

    def get_animation(self) -> Animation:
        steps = bp_util.get_available_steps_bp(self.prefix)

        if self.versus_1d:
            anim = BpAnimation1d(steps, self.prefix, self.variable, self.versus_1d)
        else:
            anim = BpAnimation2d(steps, self.prefix, self.variable, self.versus_2d)

        for plugin in self.plugins:
            anim.add_plugin(plugin)

        return anim


def add_subparsers_bp(subparsers: argparse._SubParsersAction):
    parent = args_base.get_subparser_parent(ArgsBp)
    parent.add_argument("variable", type=str, help="the variable to plot")

    parent.add_argument(
        "--roll",
        type=parse_roll,
        dest="plugins",
        action="append",
        metavar="dim_name=window_size",
        help="plot the rolling average against this dimension with this window size",
    )
    parent.set_defaults(plugins=[])

    versus_group = parent.add_mutually_exclusive_group()
    versus_group.add_argument(
        "--versus-1d",
        type=str,
        choices=BP_DIMS,
        help="plot the variable against this dimension as a line plot, averaging over other dimensions",
    )
    versus_group.add_argument(
        "--versus-2d",
        nargs=2,
        type=str,
        choices=BP_DIMS,
        default=("y", "z"),
        help="plot the variable against these dimensions as a heat map, averaging over the third dimension",
    )

    # may have to unroll this loop later when e.g. different prefixes have different derived variables
    for bp_prefix in BP_PREFIXES:
        subparsers.add_parser(bp_prefix, parents=[parent])
