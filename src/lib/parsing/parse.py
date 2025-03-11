import argparse

from . import args_base, args_bp, args_h5

__all__ = ["get_parsed_args"]


def _get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="psc-plot")
    args_base.add_arguments(parser)
    subparsers = args_base.add_subparsers(parser)

    args_bp.add_subparsers_bp(subparsers)
    args_h5.add_subparsers_h5(subparsers)

    return parser


def get_parsed_args() -> args_base.TypedArgs:
    parser = _get_parser()
    args = parser.parse_args(namespace=args_base.UntypedArgs()).to_typed()
    return args
