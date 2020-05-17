from fuzzy.app.phrasebook import parser
from fuzzy.app.phrasebook import MarkupStr
from fuzzy.app.phrasebook import choice
from fuzzy.nlp.gen import Choice


def test_generate_with_function():
    p = parser({"NAME": choice("alice", "bob")})
    markup: MarkupStr = p.parse("{hello,welcome} NAME").generate()
    assert markup.labels[0][2] == "NAME"
    assert "alice" in markup.text or "bob" in markup.text


def test_choice_ctor():
    args = ["x", "y", "z"]
    vargs = Choice(*args)  # changes type to tuple
    list_args = Choice(args)
    assert vargs._val == list_args._val


def test_choice_with_opt():
    p = parser({"NAME": choice("alice", "bob")})
    text = p.parse("hello NAME?").generate().text
    assert text in ('hello alice', 'hello bob', 'hello')