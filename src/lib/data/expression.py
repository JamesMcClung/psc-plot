"""The expression grammar shared by `--derive` and `--fit`, and evaluators for it.

An evaluator is a lark `Transformer` that turns a parsed expression into a value.
`ExpressionEvaluator` does the arithmetic; subclasses decide what a name means."""

from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
from lark import Lark, Tree
from lark.exceptions import VisitError
from lark.visitors import Transformer

_GRAMMAR = r"""
?start : assignment

assignment   : new_variable "=" expression
new_variable : CNAME

?expression : _expression_3

_expression_0 : "(" expression ")"
              | function_call
              | variable
              | scoped_variable
              | number
              | imaginary
_expression_1 : _expression_0
              | exponentiation
_expression_2 : _expression_1
              | multiplication
              | division
_expression_3 : _expression_2
              | addition
              | subtraction

exponentiation : _expression_1 "^" _expression_0
multiplication : _expression_2 "*" _expression_1
division       : _expression_2 "/" _expression_1
addition       : _expression_3 "+" _expression_2
subtraction    : _expression_3 "-" _expression_2

function_call   : CNAME "(" expression ")"
variable        : CNAME
scoped_variable : prepath "::" CNAME
number          : SIGNED_NUMBER
imaginary       : IMAGINARY

# a number immediately followed by `i`, e.g. `1i` or `-2.5e3i`; a bare `i` is a variable
IMAGINARY : SIGNED_NUMBER "i"

prepath : PREFIX
# DIR    : /[^\/]+/ TODO figure out a way to make dirs work; as is, the arbitrary chars are incompatible with math symbols, especially /
PREFIX : /[.\w\d]+/

%import common.SIGNED_NUMBER
%import common.CNAME
%import common.WS
%ignore WS
"""

EXPRESSION_PARSER = Lark(_GRAMMAR)

EXPRESSION_FUNCTIONS: dict[str, Callable] = {"log": np.log, "exp": np.exp}


def split_assignment(tree: Tree) -> tuple[str, Tree]:
    """Split a parsed `new_key=expression` into the new key and the expression's tree."""
    [new_variable, expression] = tree.children
    [tok] = new_variable.children
    return str(tok), expression


def variable_names(tree: Tree) -> set[str]:
    """The unscoped variable names used anywhere in `tree`."""
    return {str(subtree.children[0]) for subtree in tree.find_data("variable")}


def evaluate(evaluator: Transformer, tree: Tree) -> Any:
    try:
        return evaluator.transform(tree)
    except VisitError as e:
        # lark wraps errors raised in the callbacks (e.g. an unknown variable); surface the original
        raise e.orig_exc from e


# Must stay a plain `Transformer`, not `Transformer_InPlace`: parsed trees are reused,
# and the in-place variant overwrites them with the first evaluation's values.
class ExpressionEvaluator(Transformer):
    """Evaluates arithmetic; subclasses implement `variable` and `scoped_variable`."""

    def __init__(self):
        super().__init__(visit_tokens=True)

    def number(self, toks: list):
        [tok] = toks
        return float(tok)

    def imaginary(self, toks: list):
        [tok] = toks
        return complex(str(tok)[:-1] + "j")

    def new_variable(self, toks: list):
        [tok] = toks
        return str(tok)

    def function_call(self, toks: list):
        [name, arg] = toks
        name = str(name)
        if name not in EXPRESSION_FUNCTIONS:
            raise ValueError(f"unknown function '{name}'")
        return EXPRESSION_FUNCTIONS[name](arg)

    def prepath(self, toks: list):
        return "/".join(str(tok) for tok in toks)

    def addition(self, toks: list):
        [lhs, rhs] = toks
        return lhs + rhs

    def subtraction(self, toks: list):
        [lhs, rhs] = toks
        return lhs - rhs

    def multiplication(self, toks: list):
        [lhs, rhs] = toks
        return lhs * rhs

    def division(self, toks: list):
        [lhs, rhs] = toks
        return lhs / rhs

    def exponentiation(self, toks: list):
        [lhs, rhs] = toks
        return lhs**rhs


class BoundEvaluator(ExpressionEvaluator):
    """Resolves names from a fixed mapping."""

    def __init__(self, values: Mapping[str, Any]):
        self.values = values
        super().__init__()

    def variable(self, toks: list):
        name = str(toks[0])
        if name not in self.values:
            raise ValueError(f"unknown name '{name}' in expression")
        return self.values[name]

    def scoped_variable(self, toks: list):
        raise ValueError("prepath::key names aren't allowed here")
