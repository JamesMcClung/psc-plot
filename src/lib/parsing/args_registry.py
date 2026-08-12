from __future__ import annotations

import typing
from argparse import Action, ArgumentParser, ArgumentTypeError
from dataclasses import dataclass
from typing import Any, Callable

CUSTOM_ARGS: list[ArgparseArgAdder] = []


def _normalize_values(values: Any) -> list[Any]:
    if values is None:
        return []
    if isinstance(values, str):
        return [values]
    return list(values)


def _combine(parser: ArgumentParser, action: Action, combiner: typing.Callable[[list[Any]], Any], values: list[Any]) -> Any:
    # argparse only turns ArgumentTypeError into a clean error message inside its own
    # `type=` conversion (_get_value). One raised here, inside an Action, would escape
    # as an uncaught traceback, so route it through parser.error ourselves.
    try:
        return combiner(values)
    except ArgumentTypeError as e:
        parser.error(f"argument {'/'.join(reversed(action.option_strings))}: {e}")


def get_combine_args_action(combiner: typing.Callable[[list[Any]], Any]) -> Action:
    class CombineArgs(Action):
        def __call__(self, parser, namespace, values, option_string=None):
            combined_value = _combine(parser, self, combiner, _normalize_values(values))

            items = getattr(namespace, self.dest, [])
            items.append(combined_value)
            setattr(namespace, self.dest, items)

    return CombineArgs


def get_store_combined_args_action(combiner: typing.Callable[[list[Any]], Any]) -> Action:
    """Like get_combine_args_action, but stores the combined value instead of appending
    it to a list — for single-instance args such as --save. Paired with nargs="*" and
    default=None, this distinguishes "flag absent" (None) from "flag with no args"."""

    class StoreCombinedArgs(Action):
        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, _combine(parser, self, combiner, _normalize_values(values)))

    return StoreCombinedArgs


type ArgparseNArgs = int | typing.Literal["+", "*", "?"] | None
type NArgs = ArgparseNArgs | typing.Literal["just one"]


@dataclass(kw_only=True)
class ArgparseArgAdder[ArgType]:
    """Adds an argument to an `argparse.ArgumentParser`"""

    flags: list[str]
    help: str
    dest: str
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
                # When one of my parsers specifies nargs=None, it means the parser maps one
                # command-line argument to a single arg instance. However, since it is common
                # to chain multiple instances of an arg together, it is convenient to be able
                # to write e.g. "--fourier x y" as a shorthand for "--fourier x --fourier y".
                # Therefore, the nargs that argparse receives is "+", with the "extend" action.
                parser.add_argument(*self.flags, dest=self.dest, help=self.help, action="extend", type=self.type, metavar=self.metavar, nargs="+")
            elif self.nargs == "just one":
                # Don't allow the above shorthand
                parser.add_argument(*self.flags, dest=self.dest, help=self.help, action="append", type=self.type, metavar=self.metavar, nargs=None)
            elif self.nargs == "?":
                # special handling for const
                parser.add_argument(*self.flags, dest=self.dest, help=self.help, action="append", type=self.type, metavar=self.metavar, nargs="?", const=self.type(None))
            else:
                # On the other hand, if a parser specifies a non-None nargs, it means the
                # parser maps that many command-line arguments to a single arg instance. This
                # actually requires a custom action, as argparse only supports one-to-one mappings
                # between command-line arguments and stored values of the given type.
                action = get_combine_args_action(self.type)
                parser.add_argument(*self.flags, dest=self.dest, help=self.help, action=action, metavar=self.metavar, nargs=self.nargs)
        elif self.const is not None:
            parser.add_argument(*self.flags, dest=self.dest, help=self.help, action="append_const", const=self.const)


def _ensure_list[T](x: T | list[T]) -> list[T]:
    return x if isinstance(x, list) else [x]


def arg_parser(
    *,
    flags: str | list[str],
    metavar: str | tuple[str] | None,
    help: str | None,
    dest: str,
    nargs: NArgs = None,
):
    def arg_parser_inner[ArgType](parse_func: Callable[[str | list[str]], ArgType]):
        CUSTOM_ARGS.append(ArgparseArgAdder(flags=_ensure_list(flags), help=help, dest=dest, type=parse_func, metavar=metavar, nargs=nargs))
        return parse_func

    return arg_parser_inner


def const_arg(
    *,
    flags: str | list[str],
    help: str | None,
    dest: str,
):
    def const_inner[ArgType](const_type: Callable[[], ArgType]):
        CUSTOM_ARGS.append(ArgparseArgAdder(flags=_ensure_list(flags), help=help, dest=dest, const=const_type()))
        return const_type

    return const_inner
