import argparse
from pathlib import Path

from lib.data.adaptor import Adaptor
from lib.plotting.hook import Hook


class Args(argparse.Namespace):
    prefix: str
    variable: str | None
    adaptors: list[Adaptor]
    hooks: list[Hook]
    show: bool
    save: Path | None
    save_format: str | None
    save_dpi: float | None
    dask_graph: bool
