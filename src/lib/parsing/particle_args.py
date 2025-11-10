import argparse

from .. import particle_util
from ..adaptors import PARTICLE_ADAPTORS, ParticleAdaptor, ParticlePipeline
from ..animation import Animation
from ..animation.particle_animation import *
from ..derived_particle_variables import DERIVED_PARTICLE_VARIABLES
from ..particle_util import PRT_VARIABLES, PrtVariable
from . import args_base

__all__ = ["add_particle_subparsers", "ParticleArgs"]


class ParticleArgs(args_base.ArgsTyped):
    axis_variables: tuple[PrtVariable, PrtVariable]
    adaptors: list[ParticleAdaptor]
    scales: list[Scale]

    def get_animation(self) -> Animation:
        steps = particle_util.get_available_particle_steps(self.prefix)

        anim = ParticleAnimation(
            steps,
            self.prefix,
            ParticlePipeline(*self.adaptors),
            axis_variables=self.axis_variables,
            bins=None,  # guess
            nicell=100,  # FIXME don't hardcode this
        )

        return anim


def add_particle_subparsers(subparsers: argparse._SubParsersAction):
    parent = args_base.get_subparser_parent(ParticleArgs)

    parent.add_argument(
        "-a",
        "--axis-variables",
        type=str,
        choices=set(PRT_VARIABLES) | set(DERIVED_PARTICLE_VARIABLES["prt"]),
        nargs=2,
        default=("y", "z"),
        help="variables to use as the x and y axes",
    )

    parent.add_argument(
        "--scale",
        choices=SCALES,
        nargs="+",
        default=[],
        dest="scales",
        help="linear or logarithmic scale for dependent variable and axes, in that order",
    )

    for adaptor_adder in PARTICLE_ADAPTORS:
        adaptor_adder.add_to(parent)

    subparsers.add_parser("prt", parents=[parent])
