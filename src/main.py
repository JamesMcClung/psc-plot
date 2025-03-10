import argparse
import typing
import numpy as np

from lib import bp_util, h5_util, file_util
from lib.animation import H5Animation, BpAnimation


class TypedArgs(argparse.Namespace):
    prefix: file_util.Prefix
    variable: str
    _handler: typing.Callable[[typing.Self], None]

    def handle(self):
        self._handler(self)


def handle_bp(args: TypedArgs):
    steps = bp_util.get_available_steps_bp(args.prefix)

    anim = BpAnimation(steps, args.prefix, args.variable)
    anim.show()


def handle_h5(args: TypedArgs):
    steps = h5_util.get_available_steps_h5(args.prefix)

    x_edges = np.linspace(0, 500, 1000, endpoint=True)
    y_edges = np.linspace(0, 20, 40, endpoint=True)

    anim = H5Animation(steps, args.prefix, ("y", "z"), (x_edges, y_edges))
    anim.show()


parser_bp = argparse.ArgumentParser(add_help=False)
parser_bp.add_argument("-v", "--variable")
parser_bp.set_defaults(_handler=handle_bp)

parser_h5 = argparse.ArgumentParser(add_help=False)
parser_h5.set_defaults(_handler=handle_h5)

parser = argparse.ArgumentParser("psc-plot")
subparsers = parser.add_subparsers(title="prefix", dest="prefix")

subparser_pfd = subparsers.add_parser("pfd", parents=[parser_bp])

subparser_pfd_moments = subparsers.add_parser("pfd_moments", parents=[parser_bp])

subparser_prt = subparsers.add_parser("prt", parents=[parser_h5])

args = parser.parse_args(namespace=TypedArgs())
args.handle()
