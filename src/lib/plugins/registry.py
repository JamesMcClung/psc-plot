from __future__ import annotations

import inspect
import typing
from argparse import ArgumentParser
from dataclasses import KW_ONLY, dataclass

from .plugin_base import PluginBp, PluginH5

__all__ = ["PLUGINS_BP", "PLUGINS_H5", "plugin_parser"]

PLUGINS_BP: list[ArgparsePluginAdder[PluginBp]] = []
PLUGINS_H5: list[ArgparsePluginAdder[PluginH5]] = []


@dataclass
class ArgparsePluginAdder[PluginType]:
    """Adds a plugin argument to an `argparse.ArgumentParser`"""

    name_or_flags: tuple[str]
    help: str
    _: KW_ONLY  # fields below this sentinel are keyword-only
    const: PluginType | None = None
    type: typing.Callable[[str], PluginType] | None = None
    metavar: str | tuple[str] | None = None

    def __post_init__(self):
        # exactly 1 must be not None
        assert [self.type, self.const].count(None) == 1

    def add_to(self, parser: ArgumentParser):
        parser.set_defaults(plugins=[])

        if self.type is not None:
            parser.add_argument(*self.name_or_flags, dest="plugins", help=self.help, action="append", type=self.type, metavar=self.metavar)
        elif self.const is not None:
            parser.add_argument(*self.name_or_flags, dest="plugins", help=self.help, action="append_const", const=self.const)


def plugin_parser(
    *name_or_flags: str,
    metavar: str | tuple[str] | None,
    help: str | None,
):
    def plugin_parser_inner[PluginType](parse_func: typing.Callable[[str], PluginType]):
        kwargs = ArgparsePluginAdder(name_or_flags, help, type=parse_func, metavar=metavar)
        plugin_type = inspect.signature(parse_func).return_annotation

        if issubclass(plugin_type, PluginBp):
            PLUGINS_BP.append(kwargs)

        if issubclass(plugin_type, PluginH5):
            PLUGINS_H5.append(kwargs)

        return parse_func

    return plugin_parser_inner


def register_const_plugin[PluginType](
    *name_or_flags: str,
    help: str | None,
    const: PluginType,
):
    kwargs = ArgparsePluginAdder(name_or_flags, help, const=const)

    if isinstance(const, PluginBp):
        PLUGINS_BP.append(kwargs)

    if isinstance(const, PluginH5):
        PLUGINS_H5.append(kwargs)
