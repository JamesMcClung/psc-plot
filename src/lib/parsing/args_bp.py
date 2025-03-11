import argparse

from .. import bp_util
from ..animation import Animation, BpAnimation
from . import args_base

__all__ = ["add_subparsers_bp", "BpArgs"]


class BpArgs(args_base.Args):
    variable: str

    @property
    def save_name(self) -> str:
        return f"{self.prefix}-{self.variable}.mp4"

    def get_animation(self) -> Animation:
        steps = bp_util.get_available_steps_bp(self.prefix)

        anim = BpAnimation(steps, self.prefix, self.variable)
        return anim


def add_subparsers_bp(subparsers: argparse._SubParsersAction):
    parent = args_base.get_subparser_parent(BpArgs)
    parent.add_argument("variable", type=str)

    subparsers.add_parser("pfd", parents=[parent])
    subparsers.add_parser("pfd_moments", parents=[parent])
