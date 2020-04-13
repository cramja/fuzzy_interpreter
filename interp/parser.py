from typing import Generator
from typing import List
from typing import Mapping
from typing import Optional
from typing import Tuple
from typing import Union

from lark import Lark
from lark import Tree

GRAMMAR = r"""
    start: target? method "with"? args? assignment?

    target: "using" id ","

    // method names aren't usually very long
    method: id~1..4

    assignment: "as" id

    args: literal_list "and" literal_map
        | literal_list
        | literal_map

    literal_list: literal ("," literal)*

    literal_map: id literal ("," id literal)*

    id: CNAME

    literal: NUMBER -> number
        | QUOTED_STRING -> string
        | UNQUOTED_STRING -> naked_string
        | CNAME -> id

    UNQUOTED_STRING: /[a-z0-9.\/:\-]+/i
    QUOTED_STRING: /("(?!"").*?(?<!\\)(\\\\)*?"|'(?!'').*?(?<!\\)(\\\\)*?')/i

    COMMENT: /#.*/

    %import common.CNAME
    %import common.SIGNED_NUMBER -> NUMBER
    %import common.WS
    %ignore WS
    %ignore COMMENT
"""


class Id:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, Id) and other.value == self.value

    def __str__(self):
        return self.value

    def __repr__(self):
        return f"id({self.value})"


LitReturn = Union[Id, str, float]
Args = Tuple[Optional[List[LitReturn]], Optional[Mapping[str, LitReturn]]]


class Expression:
    def __init__(self, method, args, target=None, assignment=None):
        self.method: str = method
        self.args: Args = args
        self.target = target
        self.assignment = assignment

    def __repr__(self):
        return f"{'' if not self.assignment else self.assignment + ' = '}" \
               f"{self.target + '.' if self.target else ''}{self.method}({self.args})"


def visit_start(node: Tree) -> Generator[Expression, None, None]:
    if node.data == "_ambig":
        for child in node.children:
            for exp in visit_start(child):
                yield exp
    else:
        # pattern = target? (method args?)+ assignment

        target = visit_target(node.children[0])
        assignment = visit_assignment(node.children[-1])
        idx = 1 if target else 0
        idx_term = len(node.children) if not assignment else len(node.children) - 1
        while idx < idx_term:
            method = visit_method(node.children[idx])
            if idx < len(node.children) - 1 and node.children[idx + 1].data == "args":
                for arg in visit_args(node.children[idx + 1]):
                    yield Expression(method, arg, target=target, assignment=assignment)
                idx += 2
            else:
                yield Expression(method, (None, None), target=target, assignment=assignment)
                idx += 1


def visit_assignment(node: Tree) -> Optional[str]:
    if node.data != "assignment":
        return None
    if len(node.children) == 0:
        return None
    return node.children[0].children[0].value


def visit_target(node: Tree) -> Optional[str]:
    if node.data != "target":
        return None
    if len(node.children) == 0:
        return None
    return node.children[0].children[0].value


def visit_method(node: Tree) -> str:
    return "_".join([x.children[0].value for x in node.children])


def visit_args(node: Tree) -> Generator[
    Tuple[Optional[List[LitReturn]], Optional[Mapping[str, LitReturn]]], None, None]:
    if node.data == "_ambig":
        for child in node.children:
            yield from visit_args(child)
    elif len(node.children) == 2:
        for list_arg in visit_literal_list(node.children[0]):
            for map_arg in visit_literal_map(node.children[1]):
                yield list_arg, map_arg
    elif node.children[0].data == "literal_list":
        for list_arg in visit_literal_list(node.children[0]):
            yield list_arg, None
    elif node.children[0].data == "literal_map":
        for map_arg in visit_literal_map(node.children[0]):
            yield None, map_arg
    else:
        raise Exception("unrecognized argument pattern")


def visit_literal_map(node: Tree) -> Generator[Mapping[str, LitReturn], None, None]:
    def combine(k, v, m):
        new_map = {k_: v_ for k_, v_ in m.items()}
        new_map[k] = v
        return new_map

    def dfs(idx):
        if idx < len(node.children) - 2:
            for potential_child_literals in dfs(idx + 2):
                for potential_value in visit_literal(node.children[idx + 1]):
                    yield combine(node.children[idx].children[0].value, potential_value, potential_child_literals)
        elif idx == len(node.children) - 2:
            for potential_value in visit_literal(node.children[idx + 1]):
                yield {node.children[idx].children[0].value: potential_value}

    for potential_maps in dfs(0):
        yield potential_maps


def visit_literal_list(node: Tree) -> Generator[List[LitReturn], None, None]:
    def dfs(idx) -> Generator[List[LitReturn], None, None]:
        if idx < len(node.children) - 1:
            for potential_child_literals in dfs(idx + 1):
                for potential_literal in visit_literal(node.children[idx]):
                    yield [potential_literal] + potential_child_literals
        elif idx == len(node.children) - 1:
            for potential_literal in visit_literal(node.children[idx]):
                yield [potential_literal]

    yield from dfs(0)


def visit_literal(node: Tree) -> Generator[LitReturn, None, None]:
    if node.data == '_ambig':
        for child in node.children:
            yield from visit_literal(child)
    else:
        if node.data == 'number':
            yield float(node.children[0].value)
        elif node.data == 'naked_string':
            yield node.children[0].value
        elif node.data == 'string':
            yield node.children[0].value[1:-1]
        elif node.data == 'id':
            yield Id(node.children[0].value)


class Parser:

    def __init__(self):
        self._parser = Lark(GRAMMAR, ambiguity='explicit')

    def parse(self, statement) -> Generator[Expression, None,None]:
        tree = self._parser.parse(statement)
        yield from visit_start(tree)