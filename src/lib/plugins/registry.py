from __future__ import annotations

import inspect
import typing
from dataclasses import dataclass

from .plugin_base import PluginBp, PluginH5

__all__ = ["PLUGINS_BP", "PLUGINS_H5", "plugin_parser"]

PLUGINS_BP: list[ArgparseKwargs[PluginBp]] = []
PLUGINS_H5: list[ArgparseKwargs[PluginH5]] = []


@dataclass
class ArgparseKwargs[PluginType]:
    """Args and kwargs of `argparse.add_argument`"""

    name_or_flags: tuple[str]
    metavar: str | tuple[str]
    help: str
    type: typing.Callable[[str], PluginType]


def plugin_parser(
    *name_or_flags: str,
    metavar: str | tuple[str] | None,
    help: str | None,
):
    def plugin_parser_inner[PluginType](parse_func: typing.Callable[[str], PluginType]):
        kwargs = ArgparseKwargs(name_or_flags, metavar, help, parse_func)
        plugin_type = inspect.signature(parse_func).return_annotation

        if issubclass(plugin_type, PluginBp):
            PLUGINS_BP.append(kwargs)

        if issubclass(plugin_type, PluginH5):
            PLUGINS_H5.append(kwargs)

        return parse_func

    return plugin_parser_inner
