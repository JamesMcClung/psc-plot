import argparse
from pathlib import Path

from lib.data.adaptor import Adaptor
from lib.data.compile import compile_source
from lib.data.loader_registry import LOADERS
from lib.plotting.get_plot import get_plot
from lib.plotting.hook import Hook
from lib.plotting.plot import Plot


class Args(argparse.Namespace):
    prefix: str
    variable: str | None
    adaptors: list[Adaptor]
    hooks: list[Hook]
    show: bool
    save: Path | None
    save_format: str | None

    def get_animation(self) -> Plot:
        loader = LOADERS[self.prefix](self.prefix, self.variable)

        source = compile_source(loader, self.adaptors)
        data = source.get_data()

        plot = get_plot(data)

        for hook in self.hooks:
            plot.add_hook(hook)

        return plot
