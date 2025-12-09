def optional_num_to_str(num: int | float | None) -> str:
    if num is None:
        return ""
    return str(num)


def sel_to_frag(sel: int | float | slice) -> str:
    if isinstance(sel, slice):
        return f"{optional_num_to_str(sel.start)}:{optional_num_to_str(sel.stop)}"
    return str(sel)
