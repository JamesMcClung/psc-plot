from dataclasses import dataclass

from lib import file_util
from lib.config import PscPlotConfig
from lib.data.adaptor import Adaptor
from lib.data.adaptors.versus import Versus
from lib.data.pipeline import Pipeline
from lib.parsing.args import Args
from lib.parsing.parse_save import SaveSpec
from lib.run.actions import DaskGraph, PlotAction, RenderPlot, SavePlot, ShowPlot
from lib.run.plot_pipeline import PlotPipeline
from lib.run.usage_error import UsageError


def _with_versus(adaptors: list[Adaptor]) -> list[Adaptor]:
    adaptors = adaptors.copy()
    for adaptor in adaptors:
        if isinstance(adaptor, Versus):
            break
    else:
        adaptors.append(Versus(["y", "z"], time_dim_rule="guess", color_dim=None))
    return adaptors


def compile_plot_pipeline(args: Args, config: PscPlotConfig) -> PlotPipeline:
    return PlotPipeline(config, Pipeline(tuple(_with_versus(args.adaptors))), tuple(args.hooks))


@dataclass(frozen=True)
class PlotRun:
    plot_pipeline: PlotPipeline
    actions: tuple[PlotAction, ...]

    def execute(self) -> None:
        if not self.actions:
            return  # e.g. -q without -s; don't load anything
        plot = self.plot_pipeline.run_plot()
        for action in self.actions:
            action.run(plot)


@dataclass(frozen=True)
class DaskGraphRun:
    plot_pipeline: PlotPipeline
    dask_graph: DaskGraph

    def execute(self) -> None:
        self.dask_graph.run(self.plot_pipeline.run_world())


type CompiledRun = PlotRun | DaskGraphRun


def compile_run(args: Args, config: PscPlotConfig) -> CompiledRun:
    plot_pipeline = compile_plot_pipeline(args, config)

    if args.dask_graph:
        # hooks draw on the plot, which --dask-graph never builds, so they don't name the file
        default_stem = file_util.stem_from_fragments(plot_pipeline.pipeline.get_name_fragments())
        return DaskGraphRun(plot_pipeline, DaskGraph(save=args.save or SaveSpec(), show=args.show, default_stem=default_stem))

    plot_actions = []

    # a shown figure blocks on the user (and an animation loops forever), so --profile never shows
    if args.show and not args.profile:
        plot_actions.append(ShowPlot())

    if args.save is not None:
        if args.save.format == "mp4" and not config.ffmpeg_bin:
            raise UsageError("format=mp4 requires ffmpeg")

        plot_actions.append(SavePlot(save=args.save, save_dpi=args.save_dpi, default_stem=plot_pipeline.get_save_file_stem()))
    elif args.profile:
        plot_actions.append(RenderPlot())

    return PlotRun(plot_pipeline, tuple(plot_actions))
