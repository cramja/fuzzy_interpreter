import datetime
import random
from abc import ABC
from abc import abstractmethod
from typing import List, Tuple
from typing import Mapping
from typing import Optional
from typing import Union

from lark import Lark
from lark import Transformer


class MarkupStr:
    """
    Marked up String.
    label = (start_inc,end_inc,LABEL)
    """

    def __init__(self, text: str, labels: Optional[List[Tuple[int, int, str]]] = None):
        self.text = text
        self.labels = labels if labels is not None else []

    @staticmethod
    def single(text: str, label: str):
        return MarkupStr(text, [(0, len(text), label)])

    def append(self, other: Optional['MarkupStr'], delim=" ") -> 'MarkupStr':
        if other is None:
            return self
        new_text = self.text + delim + other.text
        offset = len(self.text) + len(delim)
        labels = self.labels.copy()
        for label in other.labels:
            labels.append((offset + label[0], offset + label[1], label[2]))
        return MarkupStr(new_text, labels)

    def __str__(self) -> str:
        return f"'{self.text}' @{self.labels}"


class G(ABC):  # Generator
    def __init__(self, val=None):
        self._val = val

    def generate(self) -> Optional[MarkupStr]:
        v = self._generate()
        if isinstance(v, MarkupStr):
            return v
        elif isinstance(v, str):
            return MarkupStr(v)
        else:
            return None

    @abstractmethod
    def _generate(self) -> Union[MarkupStr, str, None]:
        pass

    def __repr__(self):
        return f"{self.__class__.__name__.lower()}({'' if self._val is None else self._val})"


class Lit(G):
    def _generate(self):
        return self._val


class Ref(G):
    def __init__(self, val, ref_defs: Mapping[str, G]):
        super().__init__(val)
        self._defs = ref_defs

    def _generate(self):
        if self._val not in self._defs:
            return self._val
        return MarkupStr.single(self._defs[self._val].generate().text, self._val)


class Choice(G):
    def __init__(self, *args):
        super().__init__()
        if len(args) == 1 and isinstance(args[0], list):
            self._val = args[0]
        else:
            self._val = list(args)

    # val = List[G]
    def _generate(self):
        return random.choice(self._val).generate()


class Opt(G):

    # val = any G
    def _generate(self) -> Union[MarkupStr, str, None]:
        if random.random() < 0.5:
            return self._val.generate()
        return None


class Seq(G):
    # val = List(G)
    def _generate(self):
        itr = iter(self._val)
        reduction = next(itr).generate()
        for g in itr:
            reduction = reduction.append(g.generate())
        return reduction


class _GeneratorTransformer(Transformer):

    def __init__(self, ref_defs=None):
        super().__init__()
        self._ref_defs = {} if ref_defs is None else ref_defs

    def start(self, seq):
        return seq[0]

    def sequence(self, words):
        return Seq(words) if len(words) > 1 else words[0]

    def choice(self, words):
        return Choice(words)

    def opt_word(self, base_word):
        return Opt(base_word[0])

    def req_word(self, base_word):
        return base_word[0]

    def word_base(self, word):
        return word[0]

    def ref(self, val):
        return Ref(val[0].value, self._ref_defs)

    def literal_string(self, val):
        return Lit(val[0].value)

    def escaped_literal_string(self, val):
        return Lit(val[0].value[1:-1])


class DateGen(G):
    _low = int(datetime.datetime(year=2000, month=1, day=1).timestamp())
    _hi = int(datetime.datetime(year=2021, month=1, day=1).timestamp())
    _fmts = ['%d %m %y', '%b %d %Y', '%B %d %Y %H:%M:%S', '%m-%d-%y']

    def _generate(self):
        return datetime.datetime.utcfromtimestamp(
            random.randint(DateGen._low, DateGen._hi)
        ).strftime(random.choice(DateGen._fmts))


def choice(*args) -> Choice:
    return Choice(list(map(lambda x: Lit(x) if isinstance(x, str) else x, args)))


def default_generators():
    return {
        "PREAMBLE": choice('show me', 'compute', 'calculate', 'get'),
        "AGGREGATION": choice('average', 'mean', 'median', 'sum',
                              "max", "maximum", "greatest", "largest",
                              "min", "minimum", "least", "smallest"),
        "PERIOD": choice('day', 'week', 'month', 'quarter', 'year'),
        "PERIODLY": choice('daily', 'weekly', 'monthly', 'annual', 'quarterly', 'yearly'),
        "DATE": DateGen()
    }


def parser(generators={}) -> Lark:
    """Generates a parser using the simple string generation format.
    Args:
        generators: map of REF to an instance of a G which can be referred to using its REF in parsed grammars.
    Returns:
        Lark parser with transformer which returns an instance of G for generating MarkupStrs
    Examples
        >>> gen: G = parser({"NAME":choice("alice","bob")}).parse("{hello, 'guten tag!'} NAME")
        >>> s = gen.generate()  # s will be something like "guten tag! bob"
    """
    grammar = """
    start: sequence

    sequence: word+

    word: word_base "?" -> opt_word
      | word_base -> req_word
      
    word_base: REF -> ref
      | literal
      | choice

    choice: "{" sequence ("," sequence)+ "}"

    literal: /[a-z][a-z ]*[a-z]/ -> literal_string 
      | ESCAPED_STRING           -> escaped_literal_string

    REF: /[A-Z_]+/

    _STRING_INNER: /.*?/
    _STRING_ESC_INNER: _STRING_INNER /(?<!\\\\)(\\\\\\\\)*?/ 
    ESCAPED_STRING: "'" _STRING_ESC_INNER "'"

    %import common.WS
    %ignore WS
    """

    g = {k: v for k, v in default_generators().items()}
    for k, v in generators.items():
        g[k] = v
    return Lark(grammar, parser='lalr', transformer=_GeneratorTransformer(g))
