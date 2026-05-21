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
        (["pfd", "hx_fc"], "pfd-hx_fc-vs_y,z;time=t"),
        (["pfd", "hx_fc", "--nan0"], "pfd-hx_fc-nan0-vs_y,z;time=t"),
        (["pfd", "hx_fc", "--scale", "log"], "pfd-hx_fc-vs_y,z;time=t-scale_log"),
    ],
)
def test_save_file_stem(args_list, expected_stem):
    assert _stem(args_list) == expected_stem
