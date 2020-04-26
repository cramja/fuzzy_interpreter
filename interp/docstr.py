from collections import namedtuple
from typing import Optional

Token = namedtuple('Token', ['type', 'value'])
DocStr = namedtuple('DocStr', ['head', 'args'])


class LineReader:
    """
    Assumes spaces not tabs.
    """

    def __init__(self, s):
        self.lines = s.split("\n")
        self.idx = 0
        self._q = []

    def __iter__(self):
        self.idx = 0
        return self

    def __next__(self):
        """!
        RETURN: Token
        """
        if self._q:
            return self._q.pop()

        if self.idx < len(self.lines):
            line = self.lines[self.idx]
            if line.startswith("!"):
                self.idx += 1
                return self.__next__()

            if line == "":
                self.idx += 1
                return Token("LINE", "")

            stripped = line.strip()
            self.idx += 1
            if ":" in stripped:
                cidx = stripped.rindex(":")
                l = stripped[:cidx]
                if cidx + 1 < len(stripped):
                    self._q.append(Token("LINE", stripped[cidx + 1:].strip()))
                return Token("ARG", l)
            return Token("LINE", stripped)
        else:
            raise StopIteration


def parse_doc_string(line) -> Optional[DocStr]:
    """!
    Parses a doc string of a particular form. Namely, it must start with !.
    The next section is called the head and it is a series of lines that
    must not contain the colon character. The next section is called args, and
    it looks like

    arg name: This is an arg line. It contains information about the arg.
        It may continue and if so, it should be indented.

    another arg: This is another arg line. Note that all lines containing colons are
        treated as start to arg lines. I tried writing a formal grammar for these kinds
        of strings but realized (after an embarrassing number of hours) that the grammar
        is not lalr parsable so this simple scheme prevails.

    """
    lr = LineReader(line)
    head = []
    args = {}
    state = "HEAD"
    arg_name = None
    for token in lr:
        if state == "HEAD" and token.type == "LINE":
            head.append(token.value)
        elif state == "HEAD" and token.type == "ARG":
            state = "ARGS"
            arg_name = token.value
            args[arg_name] = []
        elif state == "ARGS" and token.type == "LINE":
            args[arg_name].append(token.value)
        elif state == "ARGS" and token.type == "ARG":
            arg_name = token.value
            args[arg_name] = []
    return DocStr(" ".join(head), {k: " ".join(v) for k, v in args.items()})
