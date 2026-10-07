import sys
from dataclasses import dataclass

from lib.config import PscPlotConfig
from lib.data.actions import DaskGraph, PlotAction, RenderPlot, SavePlot, ShowPlot
from lib.data.adaptor import Adaptor
from lib.data.adaptors.versus import Versus
from lib.data.pipeline import PlotPipeline
from lib.parsing.args import Args
from lib.parsing.parse_save import SaveSpec


def _with_versus(adaptors: list[Adaptor]) -> list[Adaptor]:
    adaptors = adaptors.copy()
    for adaptor in adaptors:
        if isinstance(adaptor, Versus):
            break
    else:
        adaptors.append(Versus(["y", "z"], time_dim_rule="guess", color_dim=None))
    return adaptors


def compile_plot_pipeline(args: Args, config: PscPlotConfig) -> PlotPipeline:
    return PlotPipeline(config, _with_versus(args.adaptors), args.hooks)


@dataclass(frozen=True)
class CompiledRun:
    pipeline: PlotPipeline
    plot_actions: list[PlotAction]
    dask_graph: DaskGraph | None
    """When set, `plot_actions` is empty."""

    def execute(self) -> None:
        if self.dask_graph is not None:
            self.dask_graph.run(self.pipeline.run_world())
            return
        if not self.plot_actions:
            return  # e.g. -q without -s; don't load anything
        plot = self.pipeline.run_plot()
        for action in self.plot_actions:
            action.run(plot)


def compile_run(args: Args, config: PscPlotConfig) -> CompiledRun:
    pipeline = compile_plot_pipeline(args, config)

    if args.profile and args.dask_graph:
        print("error: --profile and --dask-graph are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    if args.dask_graph:
        return CompiledRun(pipeline, [], DaskGraph(save=args.save or SaveSpec(), show=args.show, default_stem=pipeline.get_save_file_stem()))

    plot_actions = []

    # a shown figure blocks on the user (and an animation loops forever), so --profile never shows
    if args.show and not args.profile:
        plot_actions.append(ShowPlot())

    if args.save is not None:
        if args.save.format == "mp4" and not config.ffmpeg_bin:
            print("error: format=mp4 requires ffmpeg", file=sys.stderr)
            sys.exit(1)

        plot_actions.append(SavePlot(save=args.save, save_dpi=args.save_dpi, default_stem=pipeline.get_save_file_stem()))
    elif args.profile:
        plot_actions.append(RenderPlot())

    return CompiledRun(pipeline, plot_actions, None)
