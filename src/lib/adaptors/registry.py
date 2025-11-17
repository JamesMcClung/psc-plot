from __future__ import annotations

import inspect
import typing
from argparse import Action, ArgumentParser
from dataclasses import KW_ONLY, dataclass
from typing import Any

import pandas as pd
import xarray as xr

from .adaptor import Adaptor

__all__ = ["FIELD_ADAPTORS", "PARTICLE_ADAPTORS", "adaptor_parser"]

FIELD_ADAPTORS: list[ArgparseAdaptorAdder[Adaptor[xr.DataArray]]] = []
PARTICLE_ADAPTORS: list[ArgparseAdaptorAdder[Adaptor[pd.DataFrame]]] = []


def get_combine_args_action(combiner: typing.Callable[[list[Any]], Any]) -> Action:
    class CombineArgs(Action):
        def __call__(self, parser, namespace, values, option_string=None):
            if values is None:
                values = []
            elif isinstance(values, str):
                values = [values]
            else:
                values = list(values)

            combined_value = combiner(values)

            items = getattr(namespace, self.dest, [])
            items.append(combined_value)
            setattr(namespace, self.dest, items)

    return CombineArgs


type ArgparseNArgs = int | typing.Literal["+", "*"] | None


@dataclass
class ArgparseAdaptorAdder[AdaptorType]:
    """Adds an adaptor argument to an `argparse.ArgumentParser`"""

    name_or_flags: tuple[str]
    help: str
    _: KW_ONLY  # fields below this sentinel are keyword-only
    const: AdaptorType | None = None
    type: typing.Callable[[str], AdaptorType] | None = None
    metavar: str | tuple[str] | None = None
    nargs: ArgparseNArgs = None

    def __post_init__(self):
        # exactly 1 must be not None
        assert [self.type, self.const].count(None) == 1

    def add_to(self, parser: ArgumentParser):
        parser.set_defaults(adaptors=[])

        if self.type is not None:
            if self.nargs is None:
                # In argparse, nargs=None usually means "consume one command-line argument"
                # (and type-convert it with the given type, then pass that to the given action).
                # When an adaptor parser specifies nargs=None, it means the parser maps a single
                # command-line argument to a single adaptor instance. However, since it is common
                # to chain multiple instances of an adaptor together, it is convenient to be able
                # to write e.g. "--fourier x y" as a shorthand for "--fourier x --fourier y".
                # Therefore, the nargs that argparse receives is "+", with the "extend" action.
                parser.add_argument(*self.name_or_flags, dest="adaptors", help=self.help, action="extend", type=self.type, metavar=self.metavar, nargs="+")
            else:
                # On the other hand, if an adaptor parser specifies a non-None nargs, it means the
                # parser maps that many command-line arguments to a single adaptor instance. This
                # actually requires a custom action, as argparse only supports one-to-one mappings
                # between command-line arguments and stored values of the given type.
                action = get_combine_args_action(self.type)
                parser.add_argument(*self.name_or_flags, dest="adaptors", help=self.help, action=action, metavar=self.metavar, nargs=self.nargs)
        elif self.const is not None:
            parser.add_argument(*self.name_or_flags, dest="adaptors", help=self.help, action="append_const", const=self.const)


def adaptor_parser(
    *name_or_flags: str,
    metavar: str | tuple[str] | None,
    help: str | None,
    nargs: ArgparseNArgs = None,
):
    def adaptor_parser_inner[AdaptorType](parse_func: typing.Callable[[str | list[str]], AdaptorType]):
        kwargs = ArgparseAdaptorAdder(name_or_flags, help, type=parse_func, metavar=metavar, nargs=nargs)
        AdaptorType: type[Adaptor] = inspect.signature(parse_func).return_annotation
        data_param_type = AdaptorType.get_data_type()

        if data_param_type is xr.DataArray:
            FIELD_ADAPTORS.append(kwargs)

        if data_param_type is pd.DataFrame:
            PARTICLE_ADAPTORS.append(kwargs)

        return parse_func

    return adaptor_parser_inner


def register_const_adaptor[Data](
    *name_or_flags: str,
    help: str | None,
    const: Adaptor[Data],
):
    kwargs = ArgparseAdaptorAdder(name_or_flags, help, const=const)

    if const.get_data_type() is xr.DataArray:
        FIELD_ADAPTORS.append(kwargs)

    if const.get_data_type() is pd.DataFrame:
        PARTICLE_ADAPTORS.append(kwargs)
