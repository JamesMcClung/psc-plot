from __future__ import annotations

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

    @abc.abstractmethod
    def get_animation(self) -> Animation: ...

    @property
    @abc.abstractmethod
    def save_name(self) -> str: ...


class UnspecifiedArgs(argparse.Namespace):
    _subclass: type[typing.Self]

    def to_subclass(self) -> Args:
        return self._subclass(**self.__dict__)


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("-s", "--save", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_false", dest="show")


def add_subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    subparsers = parser.add_subparsers(title="prefix", dest="prefix")
    return subparsers


def get_subparser_parent[ArgsSubclass: Args](subclass: type[ArgsSubclass]) -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.set_defaults(_subclass=subclass)
    return parent
