import argparse

from .. import bp_util
from ..animation import Animation, BpAnimation
from ..bp_util import BP_DIMS, BpDim
from . import args_base

__all__ = ["add_subparsers_bp", "ArgsBp"]


class ArgsBp(args_base.ArgsTyped):
    variable: str
    versus_1d: BpDim | None

    @property
    def save_name(self) -> str:
        maybe_versus = f"-vs_{self.versus_1d}" if self.versus_1d else ""
        return f"{self.prefix}-{self.variable}{maybe_versus}.mp4"

    def get_animation(self) -> Animation:
        steps = bp_util.get_available_steps_bp(self.prefix)

        anim = BpAnimation(steps, self.prefix, self.variable)
        return anim


def add_subparsers_bp(subparsers: argparse._SubParsersAction):
    parent = args_base.get_subparser_parent(ArgsBp)
    parent.add_argument("variable", type=str, help="the variable to plot")
    parent.add_argument("--versus-1d", type=str, choices=BP_DIMS, help="plot the variable against this axis as a line plot, averaging over other dimensions")

    subparsers.add_parser("pfd", parents=[parent])
    subparsers.add_parser("pfd_moments", parents=[parent])
    subparsers.add_parser("gauss", parents=[parent])
