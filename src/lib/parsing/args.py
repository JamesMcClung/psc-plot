import argparse
from pathlib import Path

from lib.data.adaptor import Adaptor
from lib.data.compile import compile_source
from lib.data.data_source import DataSource
from lib.data.data_with_attrs import DataWithAttrs
from lib.plotting.get_plot import get_plot
from lib.plotting.hook import Hook
from lib.plotting.plot import Plot


class Args(argparse.Namespace):
    prefix: str
    loader: DataSource
    variable: str | None
    adaptors: list[Adaptor]
    hooks: list[Hook]
    show: bool
    save: Path | None
    save_format: str | None
    dask_graph: bool

    def get_data(self) -> DataWithAttrs:
        source = compile_source(self.loader, self.adaptors)
        return source.get_data()

    def get_animation(self) -> Plot:
        data = self.get_data()

        plot = get_plot(data)

        for hook in self.hooks:
            plot.add_hook(hook)

        return plot

    def get_save_file_stem(self) -> str:
        sources = [self.loader, *self.adaptors, *self.hooks]
        fragments = [frag for src in sources for frag in src.get_name_fragments()]
        return "-".join(fragments)
