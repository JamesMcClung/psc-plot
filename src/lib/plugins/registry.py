from __future__ import annotations

from dataclasses import dataclass

from .plugin_base import Plugin, PluginBp, PluginH5

__all__ = ["PLUGINS_BP", "PLUGINS_H5", "plugin"]

PLUGINS_BP: dict[PluginBp, ArgparseKwargs] = {}
PLUGINS_H5: dict[PluginH5, ArgparseKwargs] = {}


@dataclass
class ArgparseKwargs:
    name_or_flags: tuple[str]
    metavar: str | tuple[str]
    help: str


def register_plugin(plugin_type: type[Plugin], kwargs: ArgparseKwargs):
    if issubclass(plugin_type, PluginBp):
        PLUGINS_BP[plugin_type] = kwargs

    if issubclass(plugin_type, PluginH5):
        PLUGINS_H5[plugin_type] = kwargs


def plugin(
    *name_or_flags: str,
    metavar: str | tuple[str] | None,
    help: str | None,
):
    def plugin_inner(plugin_type: type[Plugin]):
        register_plugin(plugin_type, ArgparseKwargs(name_or_flags, metavar, help))
        return plugin_type

    return plugin_inner
