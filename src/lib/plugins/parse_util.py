import argparse
import typing


def fail_format(arg: str, format: str):
    raise argparse.ArgumentTypeError(f"Expected value of form '{format}'; got '{arg}'")


def check_value[T](val: T, val_name: str, valid_options: typing.Container[T]):
    if val not in valid_options:
        raise argparse.ArgumentTypeError(f"Expected {val_name} to be one of {set(valid_options)}; got '{val}'")


def check_order[T](lower: T | None, upper: T | None, lower_name: str, upper_name: str):
    if upper is not None and lower is not None and upper <= lower:
        raise argparse.ArgumentTypeError(f"Expected {lower_name}<{upper_name}; got {lower_name}={lower}, {upper_name}={upper}")


def check_len(args: list, expected_len: int):
    if len(args) != expected_len:
        raise argparse.ArgumentTypeError(f"Expected {expected_len} args; got {args} ({args})")


def parse_number[T](num_arg: str, num_name: str, num_parser: typing.Callable[[str], T]) -> T:
    try:
        return num_parser(num_arg)
    except:
        if num_parser is int:
            num_type_desc = "an integer"
        elif num_parser is float:
            num_type_desc = "a float"
        else:
            raise ValueError(num_parser)

        raise argparse.ArgumentTypeError(f"Expected {num_name} to be {num_type_desc} or absent; got '{num_arg}'")


def parse_optional_number[T](num_arg: str, num_name: str, num_parser: typing.Callable[[str], T]) -> T | None:
    if num_arg == "":
        return None

    return parse_number(num_arg, num_name, num_parser)
