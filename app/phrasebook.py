import datetime
import json
import random
import re
from abc import ABC
from abc import abstractmethod
from re import Pattern
from typing import Dict
from typing import Iterable
from typing import List
from typing import Mapping
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Union

import spacy
import pandas as pd
from lark import Lark
from lark import Transformer
from spacy.language import Language
from spacy.scorer import Scorer
from spacy.util import compounding


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


class G(ABC): # Generator
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
    # val = List[G]
    def _generate(self):
        return random.choice(self._val).generate()


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

    def word(self, word):
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
        "DATE_GROUP": choice('daily', 'weekly', 'monthly', 'annual', 'quarterly', 'yearly'),
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

    word: REF -> ref
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


def clean_column(col) -> Set[str]:
    def filter_pattern(vals: Set[str], patterns: List[Pattern]):
        for pattern in patterns:
            vals = set(filter(lambda x: not pattern.search(x), vals))
        return vals
    data_filters = [re.compile(p) for p in [r'^\s*$', 'do not use', 'tbd',
                                            'test', 'test .*', '(new|demo) company',
                                            'practice']]
    return filter_pattern(set(v.lower() for v in col), data_filters)


def train_model(phrasebook: List[MarkupStr], validation_ratio) -> Language:
    training_data = []
    training_labels = set()
    for phrase in phrasebook:
        training_data.append((phrase.text, {'entities': phrase.labels},))
        for label in phrase.labels:
            training_labels.add(label[2])
    total_data = len(training_data)
    random.shuffle(training_data)
    validation_size = int(validation_ratio * total_data)
    validation_data = training_data[0: validation_size]
    training_data = training_data[validation_size:]

    nlp: Language = spacy.blank("en")  # spacy.load("en_core_web_sm")
    ner = nlp.create_pipe("ner")
    for label in training_labels:
        ner.add_label(label)
    nlp.add_pipe(ner, name='custom_ner')

    # Start the training
    nlp.begin_training()

    # Loop for 10 iterations
    for itn in range(5):
        # reshuffle the training data
        random.shuffle(training_data)
        losses = {}
        sizes=compounding(1.0, 4.0, 1.001)

        # Batch the examples and iterate over them
        for batch in spacy.util.minibatch(training_data, size=sizes):
            texts, annotations = zip(*batch)
            nlp.update(texts, annotations, losses=losses, drop=0.5)

    scorer: Scorer = nlp.evaluate(validation_data)
    print(json.dumps(scorer.ents_per_type))

    return nlp


class PhrasebookApp:
    def __init__(self):
        self._df: Optional[pd.DataFrame] = None
        self._vocabs: Dict[str, Set[str]] = {}
        self._statements: Dict[str, G] = {}
        self._nlp: Optional[Language] = None

    def _require_df(self):
        if self._df is None:
            raise Exception("there's no data loaded in. use 'load csv' to load a csv in")

    def _require_nlp(self):
        if self._nlp is None:
            raise Exception("there's no recognizer trained, use 'train' after adding some statements")

    def load_csv(self, filename):
        self._df = pd.read_csv(filename)

    def list_columns(self):
        self._require_df()
        return list(sorted(self._df.columns))

    def add_vocab(self, column, label: str):
        self._require_df()
        existing = self._vocabs.get(label, set())
        existing.update(clean_column(self._df[column]))
        self._vocabs[label] = set(existing)

    def sample_vocab(self, label, size=10) -> List[str]:
        if label not in self._vocabs:
            raise Exception(f"vocab {label} is not an option, use: {[x for x in self._vocabs.keys()]}")
        return random.sample(self._vocabs[label], size)

    def clear_statements(self):
        self._statements.clear()

    def list_statements(self):
        return list(self._statements.keys())

    def add_statement(self, statement):
        self._statements[statement] = parser({k: choice(*v) for k, v in self._vocabs.items()}).parse(statement)

    def sample_statements(self, prefix=None, size=10):
        if not self._statements:
            return "there are no statements"
        candidates = []
        if prefix:
            for statement in self._statements.keys():
                if statement.startswith(prefix):
                    candidates.append(self._statements[statement])
        else:
            candidates.extend(self._statements.values())
        if not candidates:
            return "no there were no statements matching your prefix"
        return [random.choice(candidates).generate().text for _ in range(size)]

    def train(self, max_per_statement=100):
        phrases = []
        for idx, generator in enumerate(self._statements.values()):
            seen = []
            dup_streak = 0
            while dup_streak < 3 and len(seen) < max_per_statement:
                p: MarkupStr = generator.generate()
                if p.text in seen:
                    dup_streak += 1
                else:
                    phrases.append(p)
                    dup_streak = 0
                    seen.append(p.text)
        self._nlp = train_model(phrases, validation_ratio=0.05)
        return f"trained named entity recognizer"

    def save(self, path):
        self._nlp.to_disk(path)
        return f"ok, saved to {path}"

    def test(self, phrase):
        doc: spacy.language.Doc = self._nlp(phrase)
        if not doc.ents:
            return "I didn't find any entities"
        else:
            return {e: e.label_ for e in doc.ents}
