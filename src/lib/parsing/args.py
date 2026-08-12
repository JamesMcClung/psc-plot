import argparse

from lib.data.adaptor import Adaptor
from lib.parsing.parse_save import SaveSpec
from lib.plotting.hook import Hook


class Args(argparse.Namespace):
    prepath: str
    variable: str | None
    adaptors: list[Adaptor]
    hooks: list[Hook]
    show: bool
    save: SaveSpec | None
    save_dpi: float | None
    dask_graph: bool
