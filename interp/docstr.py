from lark import Lark
from lark.indenter import Indenter

class TreeIndenter(Indenter):
    NL_type = '_NL'
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 4


GRAMMAR = r"""
start: line* section+ line*
    | line*

section: head _INDENT section_body _DEDENT

section_body: line* 
    | line* name_comment+ line*

name_comment: name ":" comment

name: WORD+

comment: line [ _INDENT line+ _DEDENT ]

line: WORD* _NL

head: /[A-Z][a-z]+/ ":" _NL

WORD: /[A-Za-z0-9.,;'"`!@$%^&*()]+/

%import common.WS_INLINE
%declare _INDENT _DEDENT
%ignore WS_INLINE
_NL: /(\r?\n[\t ]*)+/
"""