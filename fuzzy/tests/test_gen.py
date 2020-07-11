from fuzzy.app.phrasebook import parser
from fuzzy.app.phrasebook import MarkupStr
from fuzzy.app.phrasebook import choice
from fuzzy.nlp.gen import Choice, Lit


def test_generate_with_function():
    p = parser({"NAME": choice("alice", "bob")})
    markup: MarkupStr = p.parse("{hello,welcome} NAME").generate()
    assert markup.labels[0][2] == "NAME"
    assert "alice" in markup.text or "bob" in markup.text


def test_choice_ctor():
    args = ["x", "y", "z"]
    vargs = Choice(*args)  # changes type to tuple
    list_args = Choice(list(map(lambda x: Lit(x), args)))

    assert len(vargs._val) == len(list_args._val)
    assert isinstance(vargs._val[0], Lit)
    assert isinstance(list_args._val[0], Lit)


def test_choice_with_opt():
    p = parser({"NAME": choice("alice", "bob")})
    text = p.parse("hello NAME?").generate().text
    assert text in ('hello alice', 'hello bob', 'hello')


def test_markup_str():
    ms1 = MarkupStr("xxx", [])
    ms2 = MarkupStr("xxx", [(0,3,'x')])
    assert ms1 == ms2