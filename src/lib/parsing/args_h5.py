import argparse

from .. import h5_util
from ..animation import Animation
from ..animation.animation_h5 import *
from ..h5_util import PRT_VARIABLES, SPECIES, PrtVariable, Species
from ..plugins import PLUGINS_H5, PluginH5
from . import args_base

__all__ = ["add_subparsers_h5", "ArgsH5"]


class ArgsH5(args_base.ArgsTyped):
    axis_variables: tuple[PrtVariable, PrtVariable]
    species: Species | None
    plugins: list[PluginH5]

    @property
    def save_name(self) -> str:
        maybe_species = f"-{self.species}" if self.species else ""
        return f"{self.prefix}{maybe_species}-{self.axis_variables[0]}-{self.axis_variables[1]}.mp4"

    def get_animation(self) -> Animation:
        steps = h5_util.get_available_steps_h5(self.prefix)

        anim = H5Animation(
            steps,
            self.prefix,
            self.species,
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

    for kwargs in PLUGINS_H5:
        parent.add_argument(
            *kwargs.name_or_flags,
            type=kwargs.type,
            dest="plugins",
            action="append",
            metavar=kwargs.metavar,
            help=kwargs.help,
        )
    parent.set_defaults(plugins=[])

    parent.add_argument(
        "--species",
        choices=SPECIES,
        help="include only particles of this species",
    )

    subparsers.add_parser("prt", parents=[parent])
