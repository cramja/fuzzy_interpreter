from fuzzy.app.phrasebook import parser
from fuzzy.app.phrasebook import MarkupStr
from fuzzy.app.phrasebook import choice


def test_generate_with_function():
    p = parser({"NAME": choice("alice", "bob")})
    markup: MarkupStr = p.parse("{hello,welcome} NAME").generate()
    assert markup.labels[0][2] == "NAME"
    assert "alice" in markup.text or "bob" in markup.text
