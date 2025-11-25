import argparse

from lib.animation.get_plot import get_plot
from lib.data.compile import compile_source

from .. import particle_util, plt_util
from ..animation.field_animation import AnimatedPlot
from ..data.adaptors import ADAPTORS, Adaptor
from ..data.particle_loader import ParticleLoader
from ..derived_particle_variables import DERIVED_PARTICLE_VARIABLES
from ..particle_util import PRT_VARIABLES, PrtVariable
from . import args_base

__all__ = ["add_particle_subparsers", "ParticleArgs"]


class ParticleArgs(args_base.ArgsTyped):
    axis_variables: tuple[PrtVariable, PrtVariable]
    adaptors: list[Adaptor]
    scales: list[plt_util.Scale]

    def get_animation(self) -> AnimatedPlot:
        steps = particle_util.get_available_particle_steps(self.prefix)

        loader = ParticleLoader(self.prefix, list(self.axis_variables), steps)
        source = compile_source(loader, self.adaptors)
        data = source.get_data()

        return get_plot(data, scales=self.scales)


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
        choices=plt_util.SCALES,
        nargs="+",
        default=[],
        dest="scales",
        help="linear or logarithmic scale for dependent variable and axes, in that order",
    )

    for adaptor_adder in ADAPTORS:
        adaptor_adder.add_to(parent)

    subparsers.add_parser("prt", parents=[parent])
