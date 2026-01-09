from __future__ import annotations

from functools import partial

from lib.parsing.args_registry import CUSTOM_ARGS, arg_parser, const_arg

from ..adaptor import Adaptor

__all__ = ["ADAPTORS", "adaptor_parser"]

ADAPTORS = CUSTOM_ARGS

adaptor_parser = partial(arg_parser, dest="adaptors")


def register_const_adaptor(
    *name_or_flags: str,
    help: str | None,
    const: Adaptor,
):
    const_arg(*name_or_flags, help=help, dest="adaptors")(const)
