import argparse

from lib.data.adaptor import Adaptor
from lib.parsing.parse_save import SaveSpec
from lib.plotting.hook import Hook
from lib.plotting.layout.options import FigSizeSpec


class Args(argparse.Namespace):
    adaptors: list[Adaptor]
    hooks: list[Hook]
    show: bool
    save: SaveSpec | None
    figsize: FigSizeSpec
    dpi: float
    dask_graph: bool
    profile: bool
    suggest_config: bool
