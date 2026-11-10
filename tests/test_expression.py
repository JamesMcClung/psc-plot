"""Tests for the shared expression grammar and evaluators (`lib.data.expression`)."""

import pytest

from lib.data.expression import EXPRESSION_PARSER, BoundEvaluator, evaluate, split_assignment, variable_names


def test_split_assignment():
    key, expr = split_assignment(EXPRESSION_PARSER.parse("f=a*y+b"))
    assert key == "f"
    assert variable_names(expr) == {"a", "y", "b"}


def test_variable_names_excludes_scoped():
    assert variable_names(EXPRESSION_PARSER.parse("f=a*pfd::hx_fc")) == {"a"}


def test_bound_evaluator():
    _, expr = split_assignment(EXPRESSION_PARSER.parse("f=a*y^2+1"))
    assert evaluate(BoundEvaluator({"a": 3.0, "y": 2.0}), expr) == 13.0


def test_bound_evaluator_unknown_name():
    _, expr = split_assignment(EXPRESSION_PARSER.parse("f=q"))
    with pytest.raises(ValueError, match="unknown name 'q'"):
        evaluate(BoundEvaluator({}), expr)


def test_bound_evaluator_rejects_scoped():
    _, expr = split_assignment(EXPRESSION_PARSER.parse("f=pfd::q"))
    with pytest.raises(ValueError, match="prepath::key"):
        evaluate(BoundEvaluator({}), expr)
