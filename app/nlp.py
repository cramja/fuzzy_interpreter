import textwrap
from typing import List
from typing import Optional
import subprocess as sp

import spacy
from spacy.language import Language
from spacy.tokens import Doc
from spacy.tokens import Span

# from https://github.com/clir/clearnlp-guidelines/blob/master/md/specifications/dependency_labels.md
POS = [
    ('ACL','clausal modifier of noun',''),
    ('ACOMP','adjectival complement','complements-adjectival complement: An adjectival complement (`acomp`) is an adjective phrase that modifies the head of a `VP|SINV|SQ`, that is usually a verb.'),
    ('ADVCL','adverbial clause modifier','adverbials-adverbial clause modifier: An adverbial clause modifier (`advcl`) is a clause that acts like an adverbial modifier.'),
    ('ADVMOD','adverbial modifier','adverbials-adverbial modifier: An adverbial modifier (`advmod`) is an adverb or an adverb phrase that modifies the meaning of another word.'),
    ('AGENT','agent','subjects-agent: An agent (`agent`) is the complement of a passive verb that is the surface subject of its active form.'),
    ('AMOD','adjectival modifier','nominals-adjectival modifier: An adjectival modifier (`amod`) is an adjective or an adjective phrase that modifies the meaning of another word, usually a noun.'),
    ('APPOS','appositional modifier','nominals-appositional modifier: An appositional modifier (`appos`) of an `NML|NP` is a noun phrase immediately preceded by another noun phrase, which gives additional information to its preceding noun phrase.'),
    ('ATTR','attribute','objects-attribute: An attribute (`attr`) is a noun phrase that is a non-VP predicate usually following a copula verb.'),
    ('AUX','auxiliary','auxiliaries-auxiliary: An auxiliary (`aux`) is an auxiliary or modal verb that gives further information about the main verb (e.g., tense, aspect).'),
    ('AUXPASS','auxiliary (passive)','auxiliaries-auxiliary (passive): A passive auxiliary (`auxpass`) is an auxiliary verb, be, become, or get, that modifies a passive verb.'),
    ('CASE','case marker','compund words-case marker: A case marker (`case`) is either a possessive marker, ...'),
    ('CC','coordinating conjunction','coordination-coordinating conjunction: A coordinating conjunction (`cc`) is a dependent of the leftmost conjunct in coordination.'),
    ('CCOMP','clausal complement','complements-clausal complement: A clausal complement (`ccomp`) is a clause with an internal subject that modifies the head of an `ADJP|ADVP|NML|NP|WHNP|VP|SINV|SQ`.'),
    ('COMPOUND','compound modifier','A noun compound modifier of an NP is any noun that serves to modify the head noun. (Note that in the current system for dependency extraction, all nouns modify the rightmost noun of the NP -- there is no intelligent noun compound analysis.  This is likely to be fixed once the Penn Treebank represents the branching structure of NPs.)'),
    ('CONJ','conjunct','coordination-conjunct: A conjunct (`conj`) is a dependent of the leftmost conjunct in coordination.'),
    ('CSUBJ','clausal subject','subjects-clausal subject: A clausal subject (`csubj`) is a clause in the subject position of an active verb.'),
    ('CSUBJPASS','clausal subject (passive)','subjects-clausal subject (passive): A clausal passive subject (`csubjpass`) is a clause in the subject position of a passive verb.'),
    ('DATIVE','dative','objects-dative: A dative (`dative`) is a nominal or prepositional object of dative-shifting verb.'),
    ('DEP','unclassified dependent','miscellaneous-unclassified dependent: An unclassified dependent (`dep`) is a dependent that does not satisfy conditions for any other dependency.'),
    ('DET','determiner','nominals-determiner: A determiner (`det`) is a word token whose pos tag is `DT|WDT|WP` that modifies the head of a noun phrase.'),
    ('DOBJ','direct object','objects-direct object: A direct object (`dobj`) is a noun phrase that is the accusative object of a (di)transitive verb.'),
    ('EXPL','expletive','subjects-expletive: An expletive (`expl`) is an existential there in the subject position.'),
    ('INTJ','interjection',''),
    ('MARK','marker','compund words-marker: A marker (`mark`) is either a subordinating conjunction (e.g., although, because, while) that introduces an adverbial clause modifier, or a subordinating conjunction, if, that, or whether, that introduces a clausal complement.'),
    ('META','meta modifier','miscellaneous-meta modifier: A meta modifier (`meta`) is code (1), embedded (2), or meta (3) information that is randomly inserted in a phrase ￼￼￼or clause.'),
    ('NEG','negation modifier','negation modifier: A negation modifier (`neg`) is an adverb that gives negative meaning to its head.'),
    ('NOUNMOD','modifier of nominal','nominals-modifier of nominal: A modifier of nominal (`nmod`) is any unclassified dependent that modifies the head of a noun phrase.'),
    ('NPMOD','noun phrase as adverbial modifier','noun phrase as adverbial modifier: An adverbial noun phrase modifier (`npmod`) is a noun phrase that acts like an adverbial modifier.'),
    ('NSUBJ','nominal subject','subjects-nominal subject: A nominal subject (`nsubj`) is a non-clausal constituent in the subject position of an active verb.'),
    ('NSUBJPASS','nominal subject (passive)','subjects-nominal subject (passive): A nominal passive subject (`nsubjpass`) is a non-clausal constituent in the subject position of a passive verb.'),
    ('NUMMOD','number modifier',''),
    ('OPRD','object predicate','objects-object predicate: An object predicate (`oprd`) is a non-VP predicate in a small clause that functions like the predicate of an object.'),
    ('PARATAXIS','parataxis',''),
    ('PCOMP','complement of preposition','This is used when the complement of a preposition is a clause or prepositional phrase (or occasionally, an adverbial phrase). The prepositional complement of a preposition is the head of a clause following the preposition, or the preposition head of the following PP.'),
    ('POBJ','object of preposition',''),
    ('POSS','possession modifier','nominals-possession modifier: A possession modifier (`poss`) is either a possessive determiner (PRP$) or a NML|NP|WHNP containing a possessive ending that modifies the head of a ADJP|NML|NP|QP|WHNP.'),
    ('PRECONJ','pre-correlative conjunction','coordination-pre-correlative conjunction: A pre-correlative conjunction (`preconj`) is the first part of a correlative conjunction that becomes a dependent of the first conjunct in coordination.'),
    ('PREDET','pre-determiner','nominals-pre-determiner: A predeterminer (`predet`) is a word token whose pos tag is PDT that modifies the head of a noun phrase.'),
    ('PREP','prepositional modifier','coordination-prepositional modifier: A prepositional modifier (`prep`) is any prepositional phrase that modifies the meaning of its head.'),
    ('PRT','particle','compund words-particle: A particle (`prt`) is a preposition in a phrasal verb that forms a verb-particle construction.'),
    ('PUNCT','punctuation','miscellaneous-punctuation: Any punctuation (`punct`) is assigned the dependency label PUNCT.'),
    ('QUANTMOD','modifier of quantifier',''),
    ('RELCL','relative clause modifier','nominals-relative clause modifier: A relative clause modifier (`relcl`) is a either relative clause or a reduced relative clause that modifies the head of an `NML|NP|WHNP`.'),
    ('ROOT','root','A root (`root`) is the root of a tree that does not depend on any node in the tree but the artificial root node.'),
    ('XCOMP','open clausal complement','complements-open clausal complement: An open clausal complement (`xcomp`) is a clause without an internal subject that modifies the head of an `ADJP|ADVP|VP|SINV|SQ`.')
]


class NLP:

    def __init__(self):
        self.nlp: Language = spacy.load("en_core_web_lg")
        self.details = {t[0]: t[2] for t in POS}

    def explain(self, name: str) -> str:
        return self.details.get(name.upper(), 'sorry, that doesn\'t exist in the database')

    def tokens(self, phrase: str) -> List[List[str]]:
        doc: Doc = self.nlp(phrase)
        table = [["text", "POS", "POS desc", "tag", "tag desc", "dep", "dep desc"]]
        def lookup(x):
            return "\n".join(textwrap.wrap(self.details.get(x, spacy.explain(x)), 60))
        for token in doc:
            table.append([token.text,token.pos_, lookup(token.pos_), token.tag_, lookup(token.tag_), token.dep_, lookup(token.dep_)])
        return table

    def nouns(self, phrase: str):
        doc: Doc = self.nlp(phrase)
        explain = []
        for chunk in doc.noun_chunks:
            explain.append(f"{chunk.text:30} {chunk.root.text:30} {chunk.root.dep_:30} {chunk.root.head.text:30}")
        return explain

    def graph(self, phrase: str, file_name: Optional[str] = None) -> str:
        doc: Doc = self.nlp(phrase)

        def ignore(token):
            return False
            #return token.text != "each" and (token.pos_ == "DET" or token.pos_ == "SPACE")

        digraph = ["""digraph G {
rankdir=LR;
ranksep=0;
edge[style=invis];
node[shape=none, width=0.3, height=0, margin=0.02];"""
        ]

        def filter_span(span: Span):
            return [token.i for token in span if not ignore(token)]

        def seq(lo, hi):
            if lo == hi:
                return None
            return "->".join(str(i) for i in range(lo, hi + 1) if not ignore(doc[i])) + ";"
        idx = 0
        for chunk in doc.noun_chunks:
            indexes = filter_span(chunk)
            if len(indexes) < 2:
                continue
            pre = seq(idx, indexes[0])
            if pre:
                digraph.append(pre)
            digraph.append(f"subgraph cluster_{idx} {{")
            digraph.append("->".join(map(str, indexes)) + ";")
            digraph.append("}")
            idx = indexes[-1]
        post = seq(idx, len(doc) - 1)
        if post:
            digraph.append(post)

        digraph.append("edge[style = solid, constraint = false];")

        for idx, token in enumerate(doc):
            if ignore(token): continue
            digraph.append(f"{token.i} [label=\"{token.text}\\n{token.pos_}\"];")
        for idx, token in enumerate(doc):
            if ignore(token): continue
            digraph.append(f"{token.i} -> {token.head.i} [label=\"{token.dep_}\"]")
        digraph.append("}")

        print("\n".join(digraph))

        file_name = "graph.png" if not file_name else file_name
        code = sp.run(["dot", "-Tpng", f"-o {file_name}"], input="\n".join(digraph), encoding='ascii')
        if code.returncode == 0:
            return f"saved to {file_name}"
        return "graph failed!"
