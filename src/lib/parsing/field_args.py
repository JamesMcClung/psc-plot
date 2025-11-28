import argparse
import typing

from lib.data.compile import compile_source
from lib.plotting.get_plot import get_plot

from .. import field_util
from ..data.adaptors import ADAPTORS, Adaptor
from ..data.field_loader import FieldLoader
from ..file_util import FIELD_PREFIXES
from ..plotting import plt_util
from ..plotting.animated_field_plot import AnimatedFieldPlot, FieldAnimation1d
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

    def get_animation(self) -> AnimatedFieldPlot:
        steps = field_util.get_available_field_steps(self.prefix)

        loader = FieldLoader(self.prefix, self.variable, steps)
        source = compile_source(loader, self.adaptors)
        data = source.get_data()

        anim = get_plot(data, scales=self.scales)

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
