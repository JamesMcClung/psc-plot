import argparse
import typing

from .. import field_util
from ..adaptors import FIELD_PLUGINS, FieldAdaptor
from ..adaptors.field_adaptors.versus import Versus
from ..animation import Animation, FieldAnimation
from ..file_util import FIELD_PREFIXES
from . import args_base

__all__ = ["add_field_subparsers", "FieldArgs"]

type Scale = typing.Literal["linear", "log", "loglog"]
SCALES: list[Scale] = list(Scale.__value__.__args__)


class FieldArgs(args_base.ArgsTyped):
    variable: str
    scale: Scale
    plugins: list[FieldAdaptor]

    def get_animation(self) -> Animation:
        steps = field_util.get_available_field_steps(self.prefix)

        versus_dims = ["y", "z"]
        for plugin in self.plugins:
            if isinstance(plugin, Versus):
                versus_dims = plugin.dim_names
                break
        else:
            self.plugins.append(Versus(versus_dims))

        anim = FieldAnimation.get_animation(steps, self.prefix, self.variable, self.plugins, versus_dims)

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

    for plugin_adder in FIELD_PLUGINS:
        plugin_adder.add_to(parent)

    parent.add_argument(
        "--scale",
        choices=SCALES,
        default="linear",
        help="use this scale",
    )

    # may have to unroll this loop later when e.g. different prefixes have different derived variables
    for field_prefix in FIELD_PREFIXES:
        subparsers.add_parser(field_prefix, parents=[parent])
