from lib.config import PscPlotConfig
from lib.data.data_with_attrs import FullList
from lib.data.loader import load

_LOG = """\
some preamble
**** Step 1 / 3, Code Time 0.00795495, Wall Time 0.148515
***** Push particles...
[0] INFO at advecting.hxx:153 (hold): Step 7 is not a step line
**** Step 2 / 3, Code Time 0.0159099, Wall Time 0.156549
**** Step 3 / 3, Code Time 2.38649e-02, Wall Time 1.64579e-01
*** Finished
"""


def test_log_loader_parses_step_lines(tmp_path):
    (tmp_path / "run").mkdir()
    (tmp_path / "run" / "log.txt").write_text(_LOG)

    data = load(PscPlotConfig.create_minimal(data_root=tmp_path), "run/log")

    assert isinstance(data, FullList)
    assert data.data["step"].tolist() == [1, 2, 3]
    assert data.data["code_time"].tolist() == [0.00795495, 0.0159099, 0.0238649]
    assert data.data["wall_time"].tolist() == [0.148515, 0.156549, 0.164579]
    assert data.metadata.var_infos["wall_time"].unit.latex == r"\text{s}"
