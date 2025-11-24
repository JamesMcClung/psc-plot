import argparse
import typing

from .. import field_util, plt_util
from ..animation import Animation, FieldAnimation
from ..animation.field_animation import FieldAnimation1d
from ..data.adaptors import ADAPTORS, Adaptor, Pipeline
from ..data.adaptors.field_adaptors.versus import Versus
from ..data.field_loader import FieldLoader
from ..data.source import DataSourceWithPipeline
from ..file_util import FIELD_PREFIXES
from . import args_base
from .fit import Fit

__all__ = ["add_field_subparsers", "FieldArgs"]

type Scale = typing.Literal["linear", "log", "loglog"]
SCALES: list[Scale] = list(Scale.__value__.__args__)


class FieldArgs(args_base.ArgsTyped):
    variable: str
    scales: list[plt_util.Scale]
    adaptors: list[Adaptor]
    fits: list[Fit]  # 1d only
    show_t0: bool  # 1d only

    def get_animation(self) -> Animation:
        steps = field_util.get_available_field_steps(self.prefix)

        spatial_dims = ["y", "z"]
        time_dim: str = "t"
        for adaptor in self.adaptors:
            if isinstance(adaptor, Versus):
                spatial_dims = adaptor.spatial_dims
                time_dim = adaptor.time_dim
                break
        else:
            self.adaptors.append(Versus(spatial_dims, time_dim))

        loader = FieldLoader(self.prefix, self.variable)
        pipeline = Pipeline(*self.adaptors)
        source = DataSourceWithPipeline(loader, pipeline)

        if time_dim:
            AnimationType = FieldAnimation.get_animation_type(spatial_dims)
            anim = AnimationType(steps, source, self.scales)
        else:
            # TODO use an argparse exception type
            raise Exception("non-animated plots not supported yet")

        if isinstance(anim, FieldAnimation1d):
            anim.add_fits(self.fits)
            anim.show_t0 = self.show_t0
        elif self.fits:
            # TODO use an argparse exception type
            raise Exception("fits not supported on higher-dimensional data")
        elif self.show_t0:
            # TODO use an argparse exception type
            raise Exception("show t=0 not supported on higher-dimensional data")

        return anim


def add_field_subparsers(subparsers: argparse._SubParsersAction):
    parent = args_base.get_subparser_parent(FieldArgs)
    parent.add_argument("variable", type=str, help="the variable to plot")

    for adaptor_adder in ADAPTORS:
        adaptor_adder.add_to(parent)

    parent.add_argument(
        "--scale",
        choices=plt_util.SCALES,
        nargs="+",
        default=[],
        dest="scales",
        help="linear or logarithmic scale for dependent variable and axes, in that order (default: linear)",
    )

    parent.add_argument(
        "--fit",
        action="extend",
        dest="fits",
        default=[],
        nargs="+",
        type=Fit,
        help="fit the data",  # TODO decide what fit should be able to do
        metavar="fit",  # TODO decide a string format to be parsed
    )

    parent.add_argument(
        "--show-t0",
        action="store_true",
        default=False,
        help="(1d only) always show the curve at t=0 for comparison",
    )

    # may have to unroll this loop later when e.g. different prefixes have different derived variables
    for field_prefix in FIELD_PREFIXES:
        subparsers.add_parser(field_prefix, parents=[parent])
