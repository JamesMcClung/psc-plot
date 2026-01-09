import argparse

from lib.data.adaptor import Adaptor
from lib.data.compile import compile_source
from lib.parsing.args_registry import CUSTOM_ARGS
from lib.plotting.get_plot import get_plot
from lib.plotting.plot import Hook

from .. import particle_util
from ..data.particle_loader import ParticleLoader
from ..derived_particle_variables import DERIVED_PARTICLE_VARIABLES
from ..particle_util import PRT_VARIABLES, PrtVariable
from ..plotting import plt_util
from ..plotting.animated_field_plot import AnimatedFieldPlot
from . import args_base

__all__ = ["add_particle_subparsers", "ParticleArgs"]


class ParticleArgs(args_base.ArgsTyped):
    axis_variables: tuple[PrtVariable, PrtVariable]
    adaptors: list[Adaptor]
    hooks: list[Hook]
    scales: list[plt_util.Scale]

    def get_animation(self) -> AnimatedFieldPlot:
        steps = particle_util.get_available_particle_steps(self.prefix)

        loader = ParticleLoader(self.prefix, list(self.axis_variables), steps)
        source = compile_source(loader, self.adaptors)
        data = source.get_data()

        anim = get_plot(data, scales=self.scales)

        for hook in self.hooks:
            anim.add_hook(hook)

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
        choices=plt_util.SCALES,
        nargs="+",
        default=[],
        dest="scales",
        help="linear or logarithmic scale for dependent variable and axes, in that order",
    )

    for custom_arg in CUSTOM_ARGS:
        custom_arg.add_to(parent)

    subparsers.add_parser("prt", parents=[parent])
