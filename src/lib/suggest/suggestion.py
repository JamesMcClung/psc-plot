import datetime
from dataclasses import dataclass

from lib.config import PscPlotConfig, format_config_value
from lib.profiling.units import format_bytes, format_cores
from lib.profiling.worker_count import WorkerCount
from lib.suggest.trial import TrialFailure, TrialResult, TrialRun

_DATA_DIR_KEY = "PSC_PLOT_DATA_DIR"
_DASK_SCHEDULER_KEY = "PSC_PLOT_DASK_SCHEDULER"
_DASK_NUM_WORKERS_KEY = "PSC_PLOT_DASK_NUM_WORKERS"


@dataclass(frozen=True)
class Measurement:
    command: str
    frames_rendered: int
    frames_total: int
    trials: dict[str, TrialResult]


def fastest(trials: dict[str, TrialResult]) -> str | None:
    """The scheduler whose trial projects the least wall time for the whole animation, or None if every trial failed."""
    runs = {scheduler: result for scheduler, result in trials.items() if isinstance(result, TrialRun)}
    return min(runs, key=lambda scheduler: runs[scheduler].projected_wall, default=None)


@dataclass(frozen=True)
class ConfigSuggestion:
    host: str
    date: datetime.date
    workers: WorkerCount
    scheduler: str
    config: PscPlotConfig
    measurement: Measurement | None

    def format_table(self) -> list[str]:
        assert self.measurement is not None
        lines = [f"  {'scheduler':<12}{'wall':>9}{'projected':>11}{'cpu':>9}{'cores':>7}{'peak rss':>10}"]
        for scheduler, result in self.measurement.trials.items():
            mark = "*" if scheduler == self.scheduler else " "
            if isinstance(result, TrialFailure):
                # one line, since format_yaml comments out each table line and a stray line would become config
                reason = " ".join(part.strip() for part in result.reason.splitlines())
                lines.append(f"{mark} {scheduler:<12}failed: {reason}")
                continue
            total = result.total
            lines.append(f"{mark} {scheduler:<12}{total.wall:>8.1f}s{result.projected_wall:>10.1f}s{total.cpu:>8.1f}s{format_cores(total.cpu, total.wall):>7}{format_bytes(total.peak_rss):>10}")
        return lines

    def format_yaml(self) -> str:
        lines = [f"# psc-plot --suggest-config on {self.host}, {self.date.isoformat()}"]
        if self.measurement is None:
            lines.append("# an environment-based guess; to measure, rerun with a representative pipeline: psc-plot <prepath> [var] [adaptors...] --suggest-config")
            scheduler_comment = "environment-based guess"
        else:
            measurement = self.measurement
            lines.append(f"# measured: {measurement.command}  ({measurement.frames_rendered} of {measurement.frames_total} frames, after a warm-up run)")
            if measurement.frames_total > measurement.frames_rendered > 1:
                lines.append(f"# projected: all {measurement.frames_total} frames, each unrendered one at the mean wall of frames 2-{measurement.frames_rendered}")
            lines.extend(f"# {line}" for line in self.format_table())
            scheduler_comment = f"least projected wall of {len(measurement.trials)} trials"

        values = self.config.to_mapping() | {_DATA_DIR_KEY: ".", _DASK_SCHEDULER_KEY: self.scheduler, _DASK_NUM_WORKERS_KEY: self.workers.yaml_value()}
        comments = {
            _DATA_DIR_KEY: "set per job: export PSC_PLOT_DATA_DIR=...",
            _DASK_SCHEDULER_KEY: scheduler_comment,
            _DASK_NUM_WORKERS_KEY: self.workers.comment(),
        }
        for key, value in values.items():
            line = f"{key}: {format_config_value(value)}"
            if key in comments:
                line += f"  # {comments[key]}"
            lines.append(line)
        return "\n".join(lines) + "\n"
