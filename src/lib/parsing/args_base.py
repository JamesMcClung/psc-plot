import argparse
import typing

from .. import file_util
from ..animation import Animation

__all__ = ["add_arguments", "add_subparsers", "get_subparser_parent", "TypedArgs"]


class TypedArgs(argparse.Namespace):
    prefix: file_util.Prefix
    show: bool
    save: bool
    _handler: typing.Callable[[typing.Self], Animation]
    _subclass: type[typing.Self]

    def handle(self) -> Animation:
        return self._handler(self._to_subclass())

    def _to_subclass(self) -> typing.Self:
        return self._subclass(**self.__dict__)

    @property
    def save_name(self) -> str:
        return NotImplementedError("This is only implemented for subclasses")


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("-s", "--save", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_false", dest="show")


def add_subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    subparsers = parser.add_subparsers(title="prefix", dest="prefix")
    print(subparsers.__class__)
    return subparsers


def get_subparser_parent[TypedArgsSubclass: TypedArgs](
    handler: typing.Callable[[TypedArgsSubclass], Animation],
    subclass: type[TypedArgsSubclass],
) -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.set_defaults(_handler=handler, _subclass=subclass)
    return parent
