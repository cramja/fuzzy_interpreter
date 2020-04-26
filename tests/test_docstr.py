from interp.docstr import parse_doc_string


def test_doc_str():
    ds = parse_doc_string(parse_doc_string.__doc__)
    assert ds.head.startswith("Parses a doc string")
    assert len(ds.args) == 2

