import sys

import matplotlib

from lib.config import PscPlotConfig
from lib.parsing.parse import parse_args
from lib.profiling.environment import EnvironmentReport
from lib.profiling.profiler import Profiler
from lib.profiling.report import ProfileReport
from lib.profiling.sampler import ProcessTreeSampler
from lib.run.compile import compile_run
from lib.run.dask_setup import configure_dask
from lib.run.usage_error import UsageError
from lib.suggest.suggest import suggest_config


def main():
    try:
        _main()
    except UsageError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


_SUGGEST_CONFIG_FLAG = "--suggest-config"


def _without_suggest_config(argv: list[str]) -> list[str]:
    # argparse accepts unambiguous abbreviations, e.g. --suggest
    return [arg for arg in argv if not (len(arg) > 2 and _SUGGEST_CONFIG_FLAG.startswith(arg))]


def _main():
    config = PscPlotConfig.from_env()
    args = parse_args()

    if args.suggest_config:
        # before configure_dask: a distributed cluster here would hold the cores the trials are timing
        if args.save is not None:
            raise UsageError("--suggest-config never saves")
        suggestion = suggest_config(_without_suggest_config(sys.argv[1:]), bool(args.adaptors), config, EnvironmentReport.collect(config))
        if suggestion.measurement is not None:
            print("\n".join(suggestion.format_table()), file=sys.stderr)
        print(suggestion.format_yaml(), end="")
        return

    configure_dask(config)

    if args.profile:
        # never show a window; see compile_run
        matplotlib.use("Agg")

    run = compile_run(args, config)

    if not args.profile:
        run.execute()
        return

    # collected after dask setup, so a distributed cluster's workers already exist
    environment = EnvironmentReport.collect(config)
    if not args.adaptors:
        print(environment.format_text())
        return

    with ProcessTreeSampler() as sampler:
        profiler = Profiler(sampler)
        with profiler.run():
            run.execute()

    print()
    print(ProfileReport(environment, profiler.records, profiler.total).format_text())
