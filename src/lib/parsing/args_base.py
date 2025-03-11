import abc
import argparse
import typing

from .. import file_util
from ..animation import Animation

__all__ = ["add_arguments", "add_subparsers", "get_subparser_parent", "Args", "UnspecifiedArgs"]


class Args(argparse.Namespace, abc.ABC):
    prefix: file_util.Prefix
    show: bool
    save: bool
    _get_animation: typing.Callable[[typing.Self], Animation]

    def get_animation(self) -> Animation:
        return self._get_animation(self)

    @property
    @abc.abstractmethod
    def save_name(self) -> str: ...


class UnspecifiedArgs(Args):
    _subclass: type[typing.Self]

    def to_subclass(self) -> Args:
        return self._subclass(**self.__dict__)

    @property
    def save_name(self) -> str:
        return NotImplementedError("Call to_subclass first to obtain a concrete version of Args")


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("-s", "--save", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_false", dest="show")


def add_subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    subparsers = parser.add_subparsers(title="prefix", dest="prefix")
    return subparsers


def get_subparser_parent[TypedArgsSubclass: Args](
    get_animation: typing.Callable[[TypedArgsSubclass], Animation],
    subclass: type[TypedArgsSubclass],
) -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.set_defaults(_get_animation=get_animation, _subclass=subclass)
    return parent
