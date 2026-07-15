import pytest
from conftest import CONFIG_2D

from lib.data.compile import compile_plot_node
from lib.parsing.parse import parse_args


@pytest.mark.parametrize(
    "args_list, expected_stem",
    [
        (["pfd", "hx_fc"], "pfd-hx_fc-v_y,z"),
        (["pfd", "hx_fc", "--nan0"], "pfd-hx_fc-nan0-v_y,z"),
        (["pfd", "hx_fc", "--scale", "log"], "pfd-hx_fc-v_y,z-scale_log"),
        (["pfd", "hx_fc", "-v", "y", "z", "time="], "pfd-hx_fc-v_y,z;time="),
    ],
)
def test_save_file_stem(args_list, expected_stem):
    actual_stem = compile_plot_node(parse_args(args_list), CONFIG_2D).get_save_file_stem()
    assert actual_stem == expected_stem
