from dataclasses import dataclass

from lib import file_util
from lib.config import PscPlotConfig
from lib.data.adaptor import Adaptor
from lib.data.data_world import DataWorld
from lib.plotting.get_plot import get_plot
from lib.plotting.hook import Hook
from lib.plotting.plot import Plot
from lib.profiling.profiler import PLOT_INIT, profile_stage


def _stage_name(adaptor: Adaptor) -> str:
    """The adaptor's class name, plus its name fragments; the CLI text isn't kept after parsing."""
    name = type(adaptor).__name__
    if fragments := adaptor.get_name_fragments():
        name += f" ({'-'.join(fragments)})"
    return name


@dataclass(frozen=True)
class Pipeline:
    config: PscPlotConfig
    adaptors: list[Adaptor]
    """Starts with the implicit `With` of the positional args, and includes a `Versus`."""
    hooks: list[Hook]

    def name_fragments(self) -> list[str]:
        return [frag for adaptor in self.adaptors for frag in adaptor.get_name_fragments()] + [frag for hook in self.hooks for frag in hook.get_name_fragments()]

    def get_save_file_stem(self) -> str:
        stem = "-".join(self.name_fragments())
        stem = file_util.sanitize_stem(stem)
        return stem

    def run_world(self) -> DataWorld:
        world = DataWorld(config=self.config)
        for adaptor in self.adaptors:
            with profile_stage(_stage_name(adaptor)):
                world = adaptor.apply_world(world)
        return world

    def run_plot(self) -> Plot:
        world = self.run_world()
        with profile_stage(PLOT_INIT):
            plot = get_plot(world)
            for hook in self.hooks:
                plot.add_hook(hook)
        return plot
