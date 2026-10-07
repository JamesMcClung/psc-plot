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


def main():
    try:
        _main()
    except UsageError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


def _main():
    config = PscPlotConfig.from_env()
    configure_dask(config)

    args = parse_args()

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
