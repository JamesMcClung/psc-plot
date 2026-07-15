import sys
import warnings

from lib.config import CONFIG
from lib.data.adaptor import Adaptor
from lib.data.adaptors.versus import Versus
from lib.data.adaptors.with_ import With
from lib.data.node import AdaptorNode, DaskGraphNode, DataProcessingNode, PlotNode, RootNode, SavePlotNode, ShowPlotNode
from lib.parsing.args import Args
from lib.plotting.plot import SaveFormat


def _with_versus(adaptors: list[Adaptor]) -> list[Adaptor]:
    adaptors = adaptors.copy()
    for adaptor in adaptors:
        if isinstance(adaptor, Versus):
            break
    else:
        adaptors.append(Versus(["y", "z"], time_dim_rule="guess", color_dim=None))
    return adaptors


def _resolve_save_format(args: Args) -> SaveFormat | None:
    if args.save is None:
        if args.save_format is not None:
            print("error: --save-format requires --save", file=sys.stderr)
            sys.exit(1)
        return None

    if args.save_format == "mp4":
        if not CONFIG.ffmpeg_bin:
            print("error: --save-format mp4 requires ffmpeg", file=sys.stderr)
            sys.exit(1)
        return "mp4"

    if args.save_format == "gif":
        return "gif"

    # save_format is None: try mp4, fall back to gif
    if CONFIG.ffmpeg_bin:
        return "mp4"

    message = "ffmpeg not found; will save animations as gif instead of mp4"
    warnings.warn(message)
    return "gif"


def compile_plot_node(args: Args) -> PlotNode:
    node = RootNode()

    node = AdaptorNode(node, With(args.prefix, args.variable))

    for adaptor in _with_versus(args.adaptors):
        node = AdaptorNode(node, adaptor)

    node = PlotNode(node, args.hooks)

    return node


def compile_action_nodes(args: Args) -> list[DataProcessingNode[None]]:
    plot_node = compile_plot_node(args)
    action_nodes = []

    if args.dask_graph:
        action_nodes.append(DaskGraphNode(plot_node.input_node, save_dir=args.save, show=args.show))
        return action_nodes

    if args.show:
        action_nodes.append(ShowPlotNode(plot_node))

    if args.save is not None:
        action_nodes.append(
            SavePlotNode(
                plot_node,
                save_dir=args.save,
                save_format=_resolve_save_format(args),
                save_dpi=args.save_dpi,
            )
        )

    return action_nodes
