import json
import random
import re
from re import Pattern
from typing import Dict
from typing import List
from typing import Optional
from typing import Set

import pandas as pd
import spacy
from spacy.language import Language
from spacy.scorer import Scorer
from spacy.util import compounding

from fuzzy.nlp.gen import MarkupStr, G, parser, choice


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
        # self._df: Optional[pd.DataFrame] = None
        self._vocabs: Dict[str, Set[str]] = {}
        self._statements: Dict[str, G] = {}
        self._nlp: Optional[Language] = None


    def _require_nlp(self):
        if self._nlp is None:
            raise Exception("there's no recognizer trained, use 'train' after adding some statements")

    def load_csv(self, filename):
        return pd.read_csv(filename)

    def list_columns(self, df: pd.DataFrame):
        # self._require_df()
        return list(sorted(df.columns))

    def add_vocab(self, label, *words):
        _words = self._vocabs.get(label, set())
        _words.update(words)
        self._vocabs[label] = _words

    def remove_vocab(self, label):
        del self._vocabs[label]

    def extract_vocab(self, column, label: str, reference=None):
        self._require_df()
        if reference is None:
            reference = label
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
