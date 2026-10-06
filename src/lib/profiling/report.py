from dataclasses import dataclass, field

from lib.profiling.environment import EnvironmentReport
from lib.profiling.profiler import FRAME_RENDER, FRAME_UPDATE, PLOT_INIT, StageRecord
from lib.profiling.units import format_bytes

# Stages recorded more than once per run, merged into one row each. Adaptor stages are never merged: two `--mag`s are two rows.
_MERGED = (PLOT_INIT, FRAME_UPDATE, FRAME_RENDER)
_FRAME_LABELS = {FRAME_UPDATE: "frame update", FRAME_RENDER: "frame render"}
_LABEL_WIDTH = 28
_MIN_WALL_FOR_CORES = 0.05


@dataclass
class _Row:
    name: str
    wall: float = 0.0
    cpu: float = 0.0
    peak_rss: int = 0
    walls: list[float] = field(default_factory=list)

    def add(self, record: StageRecord):
        self.wall += record.wall
        self.cpu += record.cpu
        self.peak_rss = max(self.peak_rss, record.peak_rss)
        self.walls.append(record.wall)

    def format(self) -> str:
        label = self.name
        extra = ""
        if self.name in _FRAME_LABELS:
            count = len(self.walls)
            label = f"{_FRAME_LABELS[self.name]} ×{count}"
            extra = f"   ({self.wall / count:.2f}s each, max {max(self.walls):.2f}s)"
        cores = f"{self.cpu / self.wall:.1f}" if self.wall >= _MIN_WALL_FOR_CORES else "-"
        return f"{label:<{_LABEL_WIDTH}}{self.wall:>9.1f}s{self.cpu:>9.1f}s{cores:>7}{format_bytes(self.peak_rss):>11}{extra}"


@dataclass(frozen=True)
class ProfileReport:
    environment: EnvironmentReport
    stages: list[StageRecord]
    total: StageRecord

    def _rows(self) -> list[_Row]:
        rows: list[_Row] = []
        merged: dict[str, _Row] = {}
        for record in self.stages:
            if record.name in merged:
                merged[record.name].add(record)
                continue
            row = _Row(record.name)
            row.add(record)
            rows.append(row)
            if record.name in _MERGED:
                merged[record.name] = row
        total = _Row(self.total.name)
        total.add(self.total)
        return [*rows, total]

    def pipeline_text(self) -> str:
        header = f"{'stage':<{_LABEL_WIDTH}}{'wall':>10}{'cpu':>10}{'cores':>7}{'peak rss':>11}"
        return "\n".join(["== pipeline ==", header, *(row.format() for row in self._rows())])

    def format_text(self) -> str:
        return self.environment.format_text() + "\n\n" + self.pipeline_text()
