import argparse

from .. import h5_util
from ..adaptors import PLUGINS_H5, ParticleAdaptor
from ..adaptors.particle_adaptors.species_filter import SpeciesFilter
from ..animation import Animation
from ..animation.animation_h5 import *
from ..h5_util import PRT_VARIABLES, PrtVariable
from . import args_base

__all__ = ["add_subparsers_h5", "ArgsH5"]


class ArgsH5(args_base.ArgsTyped):
    axis_variables: tuple[PrtVariable, PrtVariable]
    plugins: list[ParticleAdaptor]

    def get_animation(self) -> Animation:
        steps = h5_util.get_available_steps_h5(self.prefix)

        anim = H5Animation(
            steps,
            self.prefix,
            axis_variables=self.axis_variables,
            bins=None,  # guess
            nicell=100,  # FIXME don't hardcode this
        )

        for plugin in self.plugins:
            anim.add_plugin(plugin)

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

    for plugin_adder in PLUGINS_H5:
        plugin_adder.add_to(parent)

    subparsers.add_parser("prt", parents=[parent])
