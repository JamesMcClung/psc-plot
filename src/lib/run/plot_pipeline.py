from dataclasses import dataclass

from lib import file_util
from lib.config import PscPlotConfig
from lib.data.data_world import DataWorld
from lib.data.pipeline import Pipeline
from lib.plotting.get_plot import get_plot
from lib.plotting.hook import Hook
from lib.plotting.plot import Plot
from lib.profiling.profiler import PLOT_INIT, profile_stage


@dataclass(frozen=True)
class PlotPipeline:
    config: PscPlotConfig
    pipeline: Pipeline
    """Starts with the implicit `With` of the positional args, and includes a `Versus`."""
    hooks: tuple[Hook, ...]

    def get_save_file_stem(self) -> str:
        return file_util.stem_from_fragments(self.pipeline.get_name_fragments() + [frag for hook in self.hooks for frag in hook.get_name_fragments()])

    def run_world(self) -> DataWorld:
        return self.pipeline.run(DataWorld(config=self.config))

    def run_plot(self) -> Plot:
        world = self.run_world()
        with profile_stage(PLOT_INIT):
            plot = get_plot(world)
            for hook in self.hooks:
                plot.add_hook(hook)
        return plot
