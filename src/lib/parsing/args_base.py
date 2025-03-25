from __future__ import annotations

import abc
import argparse

from .. import file_util
from ..animation import Animation

__all__ = ["add_common_arguments", "add_subparsers", "get_subparser_parent", "TypedArgs", "UntypedArgs"]


class TypedArgs(argparse.Namespace, abc.ABC):
    prefix: file_util.Prefix
    show: bool
    save: bool

    @abc.abstractmethod
    def get_animation(self) -> Animation: ...

    @property
    @abc.abstractmethod
    def save_name(self) -> str: ...


class UntypedArgs(argparse.Namespace):
    _typed_args: type[TypedArgs]

    def to_typed(self) -> TypedArgs:
        return self._typed_args(**self.__dict__)


def add_common_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("-s", "--save", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_false", dest="show")


def add_subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    subparsers = parser.add_subparsers(title="prefix", dest="prefix", required=True)
    return subparsers


def get_subparser_parent(typed_args: type[TypedArgs]) -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.set_defaults(_typed_args=typed_args)
    add_common_arguments(parent)
    return parent
