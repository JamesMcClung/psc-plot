import argparse

from .. import particle_util
from ..adaptors import PARTICLE_ADAPTORS, ParticleAdaptor
from ..adaptors.particle_adaptors.species_filter import SpeciesFilter
from ..animation import Animation
from ..animation.particle_animation import *
from ..particle_util import PRT_VARIABLES, PrtVariable
from . import args_base

__all__ = ["add_particle_subparsers", "ParticleArgs"]


class ParticleArgs(args_base.ArgsTyped):
    axis_variables: tuple[PrtVariable, PrtVariable]
    adaptors: list[ParticleAdaptor]

    def get_animation(self) -> Animation:
        steps = particle_util.get_available_particle_steps(self.prefix)

        anim = ParticleAnimation(
            steps,
            self.prefix,
            axis_variables=self.axis_variables,
            bins=None,  # guess
            nicell=100,  # FIXME don't hardcode this
        )

        for adaptor in self.adaptors:
            anim.add_adaptor(adaptor)

        return anim


def add_particle_subparsers(subparsers: argparse._SubParsersAction):
    parent = args_base.get_subparser_parent(ParticleArgs)

    parent.add_argument(
        "-a",
        "--axis-variables",
        type=str,
        choices=PRT_VARIABLES,
        nargs=2,
        default=("y", "z"),
        help="variables to use as the x and y axes",
    )

    for adaptor_adder in PARTICLE_ADAPTORS:
        adaptor_adder.add_to(parent)

    subparsers.add_parser("prt", parents=[parent])
