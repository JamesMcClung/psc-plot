import argparse

from .. import bp_util, plugins_bp
from ..animation import Animation, BpAnimation1d, BpAnimation2d
from ..bp_util import BP_DIMS, BpDim
from . import args_base

__all__ = ["add_subparsers_bp", "ArgsBp"]


class RollArg:
    def __init__(self, as_str: str):
        split_str = as_str.split("=")

        if len(split_str) != 2:
            raise argparse.ArgumentTypeError(f"Expected value of form 'dim_name=window_size'; got '{as_str}'")

        [self.dim_name, window_size] = split_str

        if self.dim_name not in BP_DIMS:
            raise argparse.ArgumentTypeError(f"Expected dim_name to be one of {BP_DIMS}; got '{self.dim_name}'")

        try:
            self.window_size = int(window_size)
        except:
            raise argparse.ArgumentTypeError(f"Expected window_size to be an integer; got '{window_size}'")

    def to_plugin(self) -> plugins_bp.Roll:
        return plugins_bp.Roll(self.dim_name, self.window_size)


class ArgsBp(args_base.ArgsTyped):
    variable: str
    versus_1d: BpDim | None
    versus_2d: tuple[BpDim, BpDim] | None
    rolls: list[RollArg]

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

        for roll in self.rolls:
            anim.add_plugin(roll.to_plugin())

        return anim


def add_subparsers_bp(subparsers: argparse._SubParsersAction):
    parent = args_base.get_subparser_parent(ArgsBp)
    parent.add_argument("variable", type=str, help="the variable to plot")

    parent.add_argument(
        "--roll",
        type=RollArg,
        dest="rolls",
        action="append",
        metavar="dim_name=window_size",
        help="plot the rolling average against this dimension with this window size",
    )

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

    subparsers.add_parser("pfd", parents=[parent])
    subparsers.add_parser("pfd_moments", parents=[parent])
    subparsers.add_parser("gauss", parents=[parent])
