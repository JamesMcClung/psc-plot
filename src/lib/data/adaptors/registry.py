from __future__ import annotations

from functools import partial

from lib.parsing.args_registry import arg_parser, const_arg

__all__ = ["const_adaptor", "adaptor_parser"]


adaptor_parser = partial(arg_parser, dest="adaptors")
const_adaptor = partial(const_arg, dest="adaptors")
