import argparse

import numpy as np

from .. import h5_util
from ..animation import Animation, H5Animation
from . import args_base

__all__ = ["add_subparsers_h5", "H5Args"]


class H5Args(args_base.Args):
    @property
    def save_name(self) -> str:
        return f"{self.prefix}.mp4"


def _get_animation_h5(args: H5Args) -> Animation:
    steps = h5_util.get_available_steps_h5(args.prefix)

    # FIXME don't hardcode this
    x_edges = np.linspace(0, 500, 1000, endpoint=True)
    y_edges = np.linspace(0, 20, 40, endpoint=True)

    anim = H5Animation(steps, args.prefix, ("y", "z"), (x_edges, y_edges))
    return anim


def add_subparsers_h5(subparsers: argparse._SubParsersAction):
    parent = args_base.get_subparser_parent(_get_animation_h5, H5Args)

    subparsers.add_parser("prt", parents=[parent])
