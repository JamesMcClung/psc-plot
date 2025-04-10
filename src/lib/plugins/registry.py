from __future__ import annotations

import typing
from dataclasses import dataclass

from .plugin_base import Plugin, PluginBp, PluginH5

__all__ = ["PLUGINS_BP", "PLUGINS_H5", "plugin"]

PLUGINS_BP: list[ArgparseKwargs[PluginBp]] = []
PLUGINS_H5: list[ArgparseKwargs[PluginH5]] = []


@dataclass
class ArgparseKwargs[PluginType]:
    """Args and kwargs of `argparse.add_argument`"""

    name_or_flags: tuple[str]
    metavar: str | tuple[str]
    help: str
    type: typing.Callable[[str], PluginType]


def plugin(
    *name_or_flags: str,
    metavar: str | tuple[str] | None,
    help: str | None,
):
    def plugin_inner(plugin_type: type[Plugin]):
        parse_func = getattr(plugin_type, "parse", None)
        if parse_func is None:
            message = f"Class `{plugin_type.__name__}` must define a `parse` class method with signature `str -> Self`"
            raise Exception(message)

        kwargs = ArgparseKwargs(name_or_flags, metavar, help, parse_func)

        if issubclass(plugin_type, PluginBp):
            PLUGINS_BP.append(kwargs)

        if issubclass(plugin_type, PluginH5):
            PLUGINS_H5.append(kwargs)

        return plugin_type

    return plugin_inner
