import argparse
import typing

from .. import field_util
from ..adaptors import FIELD_ADAPTORS, FieldAdaptor, FieldPipeline
from ..adaptors.field_adaptors.versus import Versus
from ..animation import Animation, FieldAnimation
from ..animation.field_animation import FieldAnimation1d
from ..file_util import FIELD_PREFIXES
from . import args_base
from .fit import Fit

__all__ = ["add_field_subparsers", "FieldArgs"]

type Scale = typing.Literal["linear", "log", "loglog"]
SCALES: list[Scale] = list(Scale.__value__.__args__)


class FieldArgs(args_base.ArgsTyped):
    variable: str
    scale: Scale
    adaptors: list[FieldAdaptor]
    fits: list[Fit]  # 1d only
    show_t0: bool  # 1d only

    def get_animation(self) -> Animation:
        steps = field_util.get_available_field_steps(self.prefix)

        versus_dims = ["y", "z"]
        for adaptor in self.adaptors:
            if isinstance(adaptor, Versus):
                versus_dims = adaptor.dim_names
                break
        else:
            self.adaptors.append(Versus(versus_dims))

        pipeline = FieldPipeline(*self.adaptors)

        anim = FieldAnimation.get_animation(steps, self.prefix, self.variable, pipeline, versus_dims)

        if isinstance(anim, FieldAnimation1d):
            anim.add_fits(self.fits)
            anim.show_t0 = self.show_t0
        elif self.fits:
            # TODO use an argparse exception type
            raise Exception("fits not supported on higher-dimensional data")
        elif self.show_t0:
            # TODO use an argparse exception type
            raise Exception("show t=0 not supported on higher-dimensional data")

        if self.scale == "linear":
            anim.set_scale("linear", "linear")
        elif self.scale == "log":
            anim.set_scale("linear", "log")
        elif self.scale == "loglog":
            anim.set_scale("log", "log")

        return anim


def add_field_subparsers(subparsers: argparse._SubParsersAction):
    parent = args_base.get_subparser_parent(FieldArgs)
    parent.add_argument("variable", type=str, help="the variable to plot")

    for adaptor_adder in FIELD_ADAPTORS:
        adaptor_adder.add_to(parent)

    parent.add_argument(
        "--scale",
        choices=SCALES,
        default="linear",
        help="use this scale",
    )

    parent.add_argument(
        "--fit",
        action="extend",
        dest="fits",
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
