import argparse

import numpy as np

from .. import h5_util
from ..animation import Animation, H5Animation, animation_h5
from . import args_base

__all__ = ["add_subparsers_h5", "H5Args"]


class H5Args(args_base.TypedArgs):
    axis_variables: tuple[animation_h5.PrtVariable, animation_h5.PrtVariable]

    @property
    def save_name(self) -> str:
        return f"{self.prefix}.mp4"

    def get_animation(self) -> Animation:
        steps = h5_util.get_available_steps_h5(self.prefix)

        # FIXME don't hardcode this; it needs to work for non-spatial dimensions, too
        x_edges = np.linspace(0, 500, 1000, endpoint=True)
        y_edges = np.linspace(0, 20, 40, endpoint=True)

        anim = H5Animation(steps, self.prefix, self.axis_variables, (x_edges, y_edges))
        return anim


def add_subparsers_h5(subparsers: argparse._SubParsersAction):
    parent = args_base.get_subparser_parent(H5Args)
    parent.add_argument("-a", "--axis-variables", type=str, choices=animation_h5.PRT_VARIABLES, nargs=2, default=("y", "z"))

    subparsers.add_parser("prt", parents=[parent])
