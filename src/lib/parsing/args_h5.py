import argparse

import numpy as np

from .. import h5_util
from ..animation import Animation
from ..animation.animation_h5 import *
from ..h5_util import PRT_VARIABLES, PrtVariable
from . import args_base

__all__ = ["add_subparsers_h5", "ArgsH5"]


class ArgsH5(args_base.ArgsTyped):
    axis_variables: tuple[PrtVariable, PrtVariable]

    @property
    def save_name(self) -> str:
        return f"{self.prefix}.mp4"

    def get_animation(self) -> Animation:
        steps = h5_util.get_available_steps_h5(self.prefix)

        # FIXME don't hardcode this; it needs to work for non-spatial dimensions, too
        x_edges = np.linspace(0, 500, 1000, endpoint=True)
        y_edges = np.linspace(0, 20, 40, endpoint=True)

        anim = H5Animation(
            steps,
            self.prefix,
            axis_variables=self.axis_variables,
            bins=(x_edges, y_edges),
            nicell=100,  # FIXME don't hardcode this
        )
        return anim


def add_subparsers_h5(subparsers: argparse._SubParsersAction):
    parent = args_base.get_subparser_parent(ArgsH5)
    parent.add_argument(
        "-a",
        "--axis-variables",
        type=str,
        choices=PRT_VARIABLES,
        nargs=2,
        default=("y", "z"),
        help="variables to use as the x and y axes",
    )

    subparsers.add_parser("prt", parents=[parent])
