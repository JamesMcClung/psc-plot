import sys

from lib.config import PscPlotConfig
from lib.data.adaptor import Adaptor
from lib.data.adaptors.versus import Versus
from lib.data.loader import get_loader
from lib.data.node import AdaptorNode, DaskGraphNode, DataProcessingNode, PlotNode, RootNode, SavePlotNode, ShowPlotNode
from lib.parsing.args import Args


def _with_versus(adaptors: list[Adaptor]) -> list[Adaptor]:
    adaptors = adaptors.copy()
    for adaptor in adaptors:
        if isinstance(adaptor, Versus):
            break
    else:
        adaptors.append(Versus(["y", "z"], time_dim_rule="guess", color_dim=None))
    return adaptors


def compile_data_node(args: Args, config: PscPlotConfig):
    node = RootNode(config)

    node = AdaptorNode(node, get_loader(config.data_dir, args.prefix, args.variable))

    for adaptor in _with_versus(args.adaptors):
        node = AdaptorNode(node, adaptor)

    return node


def compile_plot_node(args: Args, config: PscPlotConfig) -> PlotNode:
    node = compile_data_node(args, config)

    node = PlotNode(node, args.hooks)

    return node


def compile_action_nodes(args: Args, config: PscPlotConfig) -> list[DataProcessingNode[None]]:
    plot_node = compile_plot_node(args, config)
    action_nodes = []

    if args.dask_graph:
        action_nodes.append(DaskGraphNode(plot_node.input_node, save_dir=args.save, show=args.show))
        return action_nodes

    if args.show:
        action_nodes.append(ShowPlotNode(plot_node))

    if args.save is None and args.save_format:
        print("error: --save-format requires --save", file=sys.stderr)
        sys.exit(1)

    if args.save_format == "mp4" and not config.ffmpeg_bin:
        print("error: --save-format mp4 requires ffmpeg", file=sys.stderr)
        sys.exit(1)

    if args.save is not None:
        action_nodes.append(
            SavePlotNode(
                plot_node,
                save_dir=args.save,
                save_format=args.save_format,
                save_dpi=args.save_dpi,
            )
        )

    return action_nodes
