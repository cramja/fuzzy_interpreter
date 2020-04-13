from lark import Lark

from interp.parser import GRAMMAR
from interp.parser import Id
from interp.parser import visit_args
from interp.parser import visit_literal
from interp.parser import visit_literal_list
from interp.parser import visit_literal_map
from interp.parser import visit_start


def test_literal_number():
    p = Lark(GRAMMAR, start="literal", ambiguity="explicit")
    tree = p.parse("123")
    resolved_literals = [x for x in visit_literal(tree)]
    assert len(resolved_literals) == 2
    assert 123.0 in resolved_literals
    assert "123" in resolved_literals


def test_literal_id():
    p = Lark(GRAMMAR, start="literal", ambiguity="explicit")
    tree = p.parse("abc")
    resolved_literals = [x for x in visit_literal(tree)]
    assert len(resolved_literals) == 2
    assert Id("abc") in resolved_literals
    assert "abc" in resolved_literals


def test_literal_string():
    p = Lark(GRAMMAR, start="literal", ambiguity="explicit")
    tree = p.parse("'hello {world}'")
    resolved_literals = [x for x in visit_literal(tree)]
    assert len(resolved_literals) == 1
    assert resolved_literals[0] == "hello {world}"


def test_literal_list():
    p = Lark(GRAMMAR, start="literal_list", ambiguity="explicit")
    tree = p.parse("123, abc")
    values = [x for x in visit_literal_list(tree)]
    assert len(values) == 4


def test_literal_map():
    p = Lark(GRAMMAR, start="literal_map", ambiguity="explicit")
    tree = p.parse("key value, key_ value_")
    values = [x for x in visit_literal_map(tree)]
    assert len(values) == 2
    assert set(map(lambda x: str(x["key"]), values)) == {"value"}


def test_args_just_list():
    p = Lark(GRAMMAR, start="args", ambiguity="explicit")
    tree = p.parse("123, abc, 'thc'")
    values = [x for x in visit_args(tree)]
    assert len(list(filter(lambda x: x[1] is None, values))) == 4
    assert len(list(filter(lambda x: x[1] is not None, values))) == 0


def test_args_just_map():
    p = Lark(GRAMMAR, start="args", ambiguity="explicit")
    tree = p.parse("abc 123, thc 420")
    values = [x for x in visit_args(tree)]
    assert len(list(filter(lambda x: x[1] is None, values))) == 0
    assert len(list(filter(lambda x: x[1] is not None, values))) == 4


def test_args_map_and_list():
    p = Lark(GRAMMAR, start="args", ambiguity="explicit")
    tree = p.parse("a and abc 123")
    values = [x for x in visit_args(tree)]
    assert len(list(filter(lambda x: x[1] is None, values))) == 0
    assert len(values) == 4


def test_expression():
    p = Lark(GRAMMAR, ambiguity="explicit")
    tree = p.parse("using foo, create example with 123 as x")
    values = [x for x in visit_start(tree)]
    for val in values:
        print(val)

