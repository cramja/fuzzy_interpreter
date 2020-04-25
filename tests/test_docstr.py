from lark import Lark

from interp.docstr import TreeIndenter
from interp.docstr import GRAMMAR


def parser(start="start"):
    return Lark(GRAMMAR, debug=True, start=start, parser='lalr', postlex=TreeIndenter())


def test_doc_str():
    """
    This is a doc string.

    Args
        This is the Args section.
        foo: the first line about foo
            something else about foo

    Returns
        This is the note about what is returned

    This is the closing line about the function
    """
    p = parser()
    print(p.parse(test_doc_str.__doc__).pretty())


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
    section_body_line = "first line\n"
    print(p.parse(section_body_line).pretty())

    section_body_arg = """first line: line 1
    line 2
    line 3
"""
    print(p.parse(section_body_arg).pretty())


def test_arg():
    p = parser("arg")
    tree = p.parse("""name(some val): line one
    line two
""")
    print(tree.pretty())
