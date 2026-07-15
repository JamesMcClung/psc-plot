from lib.data.adaptor import Adaptor
from lib.data.adaptors.versus import Versus
from lib.data.node import AdaptorNode, LoaderNode, PlotNode
from lib.parsing.args import Args


def _with_versus(adaptors: list[Adaptor]) -> list[Adaptor]:
    adaptors = adaptors.copy()
    for adaptor in adaptors:
        if isinstance(adaptor, Versus):
            break
    else:
        adaptors.append(Versus(["y", "z"], time_dim_rule="guess", color_dim=None))
    return adaptors


def compile_args(args: Args) -> PlotNode:
    node = LoaderNode(args.loader)

    for adaptor in _with_versus(args.adaptors):
        node = AdaptorNode(node, adaptor)

    node = PlotNode(node, args.hooks)

    return node
