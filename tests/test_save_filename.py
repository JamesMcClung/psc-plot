import pytest

from lib.data.compile import compile_source
from lib.parsing.parse import get_parsed_args


def _stem(args_list: list[str]) -> str:
    args = get_parsed_args(args_list)
    compile_source(args.loader, args.adaptors)  # mutates args.adaptors: appends default Versus
    return args.get_save_file_stem()


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
    assert _stem(args_list) == expected_stem
