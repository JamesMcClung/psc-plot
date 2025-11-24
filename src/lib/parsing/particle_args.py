import argparse

from .. import particle_util, plt_util
from ..animation import Animation
from ..animation.field_animation import FieldAnimation
from ..data.adaptors import ADAPTORS, Adaptor, Pipeline
from ..data.adaptors.field_adaptors.versus import Versus
from ..data.particle_loader import ParticleLoader
from ..data.source import DataSourceWithPipeline
from ..derived_particle_variables import DERIVED_PARTICLE_VARIABLES
from ..particle_util import PRT_VARIABLES, PrtVariable
from . import args_base

__all__ = ["add_particle_subparsers", "ParticleArgs"]


class ParticleArgs(args_base.ArgsTyped):
    axis_variables: tuple[PrtVariable, PrtVariable]
    adaptors: list[Adaptor]
    scales: list[plt_util.Scale]

    def get_animation(self) -> Animation:
        steps = particle_util.get_available_particle_steps(self.prefix)

        spatial_dims = ["y", "z"]
        time_dim: str = "t"
        for adaptor in self.adaptors:
            if isinstance(adaptor, Versus):
                spatial_dims = adaptor.spatial_dims
                time_dim = adaptor.time_dim
                break
        else:
            self.adaptors.append(Versus(spatial_dims, time_dim))

        loader = ParticleLoader(self.prefix, list(self.axis_variables))
        pipeline = Pipeline(*self.adaptors)
        source = DataSourceWithPipeline(loader, pipeline)

        FieldAnimation.get_animation_type(spatial_dims)

        if time_dim:
            AnimationType = FieldAnimation.get_animation_type(spatial_dims)
            anim = AnimationType(steps, source, self.scales)
        else:
            # TODO use an argparse exception type
            raise Exception("non-animated plots not supported yet")

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

    for adaptor_adder in ADAPTORS:
        adaptor_adder.add_to(parent)

    subparsers.add_parser("prt", parents=[parent])
