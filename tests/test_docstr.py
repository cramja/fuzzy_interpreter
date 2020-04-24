from lark import Lark

from interp.docstr import TreeIndenter
from interp.docstr import GRAMMAR


def parser(start="start"):
    return Lark(GRAMMAR, debug=True, start=start, parser='lalr', postlex=TreeIndenter())


def test_body():
    p = parser()
    doc_str = """line one
Note:
    line one
line one
"""
    print(p.parse(doc_str).pretty())


def test_section():
    p = parser("section")
    doc_str = """Head:
    line 1
    line 2
    val a: some value
        some continuation
    val b: some value
    line 1
"""
    print(p.parse(doc_str).pretty())

def test_section_body():
    p = parser("section_body")
    section_body_1 = """first line
second line
"""
    print(p.parse(section_body_1).pretty())

    section_body_2 = """first line
second line
val x: desc x
    desc x
val x: desc x
    desc x
"""
    print(p.parse(section_body_2).pretty())

    section_body_3 = """first line
second line

val 1: desc 1
    desc 2

val 2: desc 1
    desc 2
post script
first line
second line
"""
    print(p.parse(section_body_3).pretty())


def test_name_comment():
    p = parser("name_comment")
    tree = p.parse("""name(some val): line one
    line two
""")
    print(tree.pretty())
