from conftest import CONFIG_2D

from lib.profiling.environment import EnvironmentReport
from lib.profiling.profiler import FINISH, FRAME_RENDER, FRAME_UPDATE, PLOT_INIT, TOTAL, StageRecord
from lib.profiling.report import ProfileReport

GB = 2**30


def _report(stages: list[StageRecord]) -> ProfileReport:
    environment = EnvironmentReport.collect(CONFIG_2D, environ={})
    total = StageRecord(TOTAL, sum(s.wall for s in stages), sum(s.cpu for s in stages), max(s.peak_rss for s in stages))
    return ProfileReport(environment, stages, total)


def _row(text: str, label: str) -> str:
    [line] = [line for line in text.splitlines() if line.startswith(label)]
    return line


def test_rows_and_columns():
    text = _report([StageRecord("With (pfd)", 2.0, 1.0, 1 * GB), StageRecord(PLOT_INIT, 4.0, 8.0, 2 * GB)]).pipeline_text()
    assert text.splitlines()[0] == "== pipeline =="
    assert _row(text, "With (pfd)").split() == ["With", "(pfd)", "2.0s", "1.0s", "0.5", "1.0", "GB"]
    assert _row(text, "plot init").split() == ["plot", "init", "4.0s", "8.0s", "2.0", "2.0", "GB"]
    assert _row(text, "total").split() == ["total", "6.0s", "9.0s", "1.5", "2.0", "GB"]


def test_frame_stages_merge_with_counts():
    stages = [StageRecord(FRAME_UPDATE, 1.0, 2.0, GB), StageRecord(FRAME_RENDER, 0.1, 0.1, GB), StageRecord(FRAME_UPDATE, 3.0, 2.0, 3 * GB), StageRecord(FRAME_RENDER, 0.1, 0.1, GB), StageRecord(FINISH, 1.0, 1.0, GB)]
    text = _report(stages).pipeline_text()
    update = _row(text, "frame update ×2")
    assert update.split()[3:9] == ["4.0s", "4.0s", "1.0", "3.0", "GB", "(2.00s"]
    assert "max 3.00s" in update
    assert "frame render ×2" in text
    labels = [line.split("  ")[0] for line in text.splitlines()[2:]]
    assert labels == ["frame update ×2", "frame render ×2", "finish", "total"]


def test_plot_init_records_merge():
    text = _report([StageRecord(PLOT_INIT, 1.0, 1.0, GB), StageRecord(PLOT_INIT, 2.0, 2.0, GB)]).pipeline_text()
    assert _row(text, "plot init").split()[2] == "3.0s"


def test_adaptor_rows_are_never_merged():
    text = _report([StageRecord("Mag", 1.0, 1.0, GB), StageRecord("Mag", 2.0, 2.0, GB)]).pipeline_text()
    assert [line.split()[1] for line in text.splitlines() if line.startswith("Mag")] == ["1.0s", "2.0s"]


def test_short_stage_has_no_cores():
    text = _report([StageRecord("Versus", 0.01, 0.0, GB)]).pipeline_text()
    assert _row(text, "Versus").split()[3] == "-"


def test_format_text_has_both_blocks():
    text = _report([StageRecord("Versus", 1.0, 1.0, GB)]).format_text()
    assert text.index("== environment ==") < text.index("== pipeline ==")
