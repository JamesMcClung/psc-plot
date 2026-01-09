from __future__ import annotations

import typing
from argparse import Action, ArgumentParser
from dataclasses import KW_ONLY, dataclass
from typing import Any

CUSTOM_ARGS: list[ArgparseArgAdder] = []


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
type NArgs = ArgparseNArgs | typing.Literal["just one"]


@dataclass
class ArgparseArgAdder[ArgType]:
    """Adds an argument to an `argparse.ArgumentParser`"""

    name_or_flags: tuple[str]
    help: str
    dest: str
    _: KW_ONLY  # fields below this sentinel are keyword-only
    const: ArgType | None = None
    type: typing.Callable[[str], ArgType] | None = None
    metavar: str | tuple[str] | None = None
    nargs: NArgs = None

    def __post_init__(self):
        # exactly 1 must be not None
        assert [self.type, self.const].count(None) == 1

    def add_to(self, parser: ArgumentParser):
        parser.set_defaults(**{self.dest: []})

        if self.type is not None:
            if self.nargs is None:
                # In argparse, nargs=None usually means "consume one command-line argument"
                # (and type-convert it with the given type, then pass that to the given action).
                # When a parser specifies nargs=None, it means the parser maps a single
                # command-line argument to a single arg instance. However, since it is common
                # to chain multiple instances of an arg together, it is convenient to be able
                # to write e.g. "--fourier x y" as a shorthand for "--fourier x --fourier y".
                # Therefore, the nargs that argparse receives is "+", with the "extend" action.
                parser.add_argument(*self.name_or_flags, dest=self.dest, help=self.help, action="extend", type=self.type, metavar=self.metavar, nargs="+")
            elif self.nargs == "just one":
                # Don't allow the above shorthand
                parser.add_argument(*self.name_or_flags, dest=self.dest, help=self.help, action="append", type=self.type, metavar=self.metavar, nargs=None)
            else:
                # On the other hand, if an parser specifies a non-None nargs, it means the
                # parser maps that many command-line arguments to a single arg instance. This
                # actually requires a custom action, as argparse only supports one-to-one mappings
                # between command-line arguments and stored values of the given type.
                action = get_combine_args_action(self.type)
                parser.add_argument(*self.name_or_flags, dest=self.dest, help=self.help, action=action, metavar=self.metavar, nargs=self.nargs)
        elif self.const is not None:
            parser.add_argument(*self.name_or_flags, dest=self.dest, help=self.help, action="append_const", const=self.const)


def arg_parser(
    *name_or_flags: str,
    metavar: str | tuple[str] | None,
    help: str | None,
    dest: str,
    nargs: NArgs = None,
):
    def arg_parser_inner[ArgType](parse_func: typing.Callable[[str | list[str]], ArgType]):
        CUSTOM_ARGS.append(ArgparseArgAdder(name_or_flags, help, dest, type=parse_func, metavar=metavar, nargs=nargs))
        return parse_func

    return arg_parser_inner


def const_arg(
    *name_or_flags: str,
    help: str | None,
    dest: str,
):
    def const_inner[ArgType](const_type: typing.Callable[[], ArgType]):
        CUSTOM_ARGS.append(ArgparseArgAdder(name_or_flags, help, dest, const=const_type()))
        return const_type

    return const_inner
