import argparse
import typing


def fail_format(arg: str, format: str):
    raise argparse.ArgumentTypeError(f"Expected value of form '{format}'; got '{arg}'")


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
