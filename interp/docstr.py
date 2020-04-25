from lark import Lark
from lark.indenter import Indenter

class TreeIndenter(Indenter):
    NL_type = '_NL'
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 4

GRAMMAR_=r"""
start: _NL _INDENT body* _DEDENT?
body: WORD ":" section_body
   | text_block+
   | _NL

section_body: _NL [ _INDENT text_block _DEDENT ]
text_block: (WORD+ _NL)+
WORD: /[A-Za-z0-9.,;'"`!@$%^&*()]+/

%import common.WS_INLINE
%declare _INDENT _DEDENT
%ignore WS_INLINE
_NL: /(\r?\n[\t ]*)+/
"""

GRAMMAR = r"""
start: (_NL | body)*

body: _INDENT statement* _DEDENT

statement: section | line

section: section_head _NL _INDENT section_body+ _DEDENT 
section_head: /[A-Z][a-z]+/ ":"
section_body: line
    | arg

arg: WORD+ ":" arg_desc
arg_desc: WORD* _NL [ _INDENT line* _DEDENT ]

line: WORD* _NL
WORD: /[A-Za-z0-9.,;'"`!@$%^&*()]+/

%import common.WS_INLINE
%declare _INDENT _DEDENT
%ignore WS_INLINE
_NL: /(\r?\n[\t ]*)+/
"""