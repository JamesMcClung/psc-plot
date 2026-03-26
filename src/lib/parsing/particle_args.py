import argparse

from lib.data.adaptor import Adaptor
from lib.data.compile import compile_source
from lib.parsing.args_registry import CUSTOM_ARGS
from lib.plotting.get_plot import get_plot
from lib.plotting.hook import Hook

from .. import particle_util
from ..data.particle_loader import ParticleLoader
from ..plotting.animated_field_plot import AnimatedFieldPlot
from . import args_base

__all__ = ["add_particle_subparsers", "ParticleArgs"]


class ParticleArgs(args_base.ArgsTyped):
    adaptors: list[Adaptor]
    hooks: list[Hook]

    def get_animation(self) -> AnimatedFieldPlot:
        steps = particle_util.get_available_particle_steps(self.prefix)

        loader = ParticleLoader(self.prefix, steps)
        source = compile_source(loader, self.adaptors)
        data = source.get_data()

        anim = get_plot(data)

        for hook in self.hooks:
            anim.add_hook(hook)

        return anim


def add_particle_subparsers(subparsers: argparse._SubParsersAction):
    parent = args_base.get_subparser_parent(ParticleArgs)

    for custom_arg in CUSTOM_ARGS:
        custom_arg.add_to(parent)

    subparsers.add_parser("prt", parents=[parent])
