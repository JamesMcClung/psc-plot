import argparse
import typing

from lib.data.adaptor import Adaptor
from lib.data.compile import compile_source
from lib.parsing.args_registry import CUSTOM_ARGS
from lib.plotting.get_plot import get_plot
from lib.plotting.hook import Hook
from lib.plotting.plot import Plot

from .. import field_util
from ..data.field_loader import FieldLoader
from ..file_util import FIELD_PREFIXES
from . import args_base

__all__ = ["add_field_subparsers", "FieldArgs"]

type Scale = typing.Literal["linear", "log", "loglog"]
SCALES: list[Scale] = list(Scale.__value__.__args__)


class FieldArgs(args_base.ArgsTyped):
    variable: str
    adaptors: list[Adaptor]
    hooks: list[Hook]

    def get_animation(self) -> Plot:
        steps = field_util.get_available_field_steps(self.prefix)

        loader = FieldLoader(self.prefix, self.variable, steps)
        source = compile_source(loader, self.adaptors)
        data = source.get_data()

        anim = get_plot(data)

        for hook in self.hooks:
            anim.add_hook(hook)

        return anim


def add_field_subparsers(subparsers: argparse._SubParsersAction):
    parent = args_base.get_subparser_parent(FieldArgs)
    parent.add_argument("variable", type=str, help="the variable to plot")

    for custom_arg in CUSTOM_ARGS:
        custom_arg.add_to(parent)

    # may have to unroll this loop later when e.g. different prefixes have different derived variables
    for field_prefix in FIELD_PREFIXES:
        subparsers.add_parser(field_prefix, parents=[parent])
