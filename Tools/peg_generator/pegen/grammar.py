
from __future__ import annotations
from abc import abstractmethod
from typing import AbstractSet, Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple, TYPE_CHECKING, Union
if TYPE_CHECKING:
    from pegen.parser_generator import ParserGenerator

class GrammarError(Exception):
    pass

class GrammarVisitor():

    def visit(self, node, *args, **kwargs):
        'Visit a node.'
        method = ('visit_' + node.__class__.__name__)
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, *args, **kwargs)

    def generic_visit(self, node, *args, **kwargs):
        'Called if no explicit visitor function exists for a node.'
        for value in node:
            if isinstance(value, list):
                for item in value:
                    self.visit(item, *args, **kwargs)
            else:
                self.visit(value, *args, **kwargs)

class Grammar():

    def __init__(self, rules, metas):
        self.rules = {rule.name: rule for rule in rules}
        self.metas = dict(metas)

    def __str__(self):
        return '\n'.join((str(rule) for (name, rule) in self.rules.items()))

    def __repr__(self):
        lines = ['Grammar(']
        lines.append('  [')
        for rule in self.rules.values():
            lines.append(f'    {repr(rule)},')
        lines.append('  ],')
        lines.append('  {repr(list(self.metas.items()))}')
        lines.append(')')
        return '\n'.join(lines)

    def __iter__(self):
        (yield from self.rules.values())
SIMPLE_STR = True

class Rule():

    def __init__(self, name, type, rhs, memo=None):
        self.name = name
        self.type = type
        self.rhs = rhs
        self.memo = bool(memo)
        self.visited = False
        self.nullable = False
        self.left_recursive = False
        self.leader = False

    def is_loop(self):
        return self.name.startswith('_loop')

    def is_gather(self):
        return self.name.startswith('_gather')

    def __str__(self):
        if (SIMPLE_STR or (self.type is None)):
            res = f'{self.name}: {self.rhs}'
        else:
            res = f'{self.name}[{self.type}]: {self.rhs}'
        if (len(res) < 88):
            return res
        lines = [(res.split(':')[0] + ':')]
        lines += [f'    | {alt}' for alt in self.rhs.alts]
        return '\n'.join(lines)

    def __repr__(self):
        return f'Rule({self.name!r}, {self.type!r}, {self.rhs!r})'

    def __iter__(self):
        (yield self.rhs)

    def nullable_visit(self, rules):
        if self.visited:
            return False
        self.visited = True
        self.nullable = self.rhs.nullable_visit(rules)
        return self.nullable

    def initial_names(self):
        return self.rhs.initial_names()

    def flatten(self):
        rhs = self.rhs
        if ((not self.is_loop()) and (len(rhs.alts) == 1) and (len(rhs.alts[0].items) == 1) and isinstance(rhs.alts[0].items[0].item, Group)):
            rhs = rhs.alts[0].items[0].item.rhs
        return rhs

    def collect_todo(self, gen):
        rhs = self.flatten()
        rhs.collect_todo(gen)

class Leaf():

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def __iter__(self):
        if False:
            (yield)

    @abstractmethod
    def nullable_visit(self, rules):
        raise NotImplementedError

    @abstractmethod
    def initial_names(self):
        raise NotImplementedError

class NameLeaf(Leaf):
    'The value is the name.'

    def __str__(self):
        if (self.value == 'ENDMARKER'):
            return '$'
        return super().__str__()

    def __repr__(self):
        return f'NameLeaf({self.value!r})'

    def nullable_visit(self, rules):
        if (self.value in rules):
            return rules[self.value].nullable_visit(rules)
        return False

    def initial_names(self):
        return {self.value}

class StringLeaf(Leaf):
    'The value is a string literal, including quotes.'

    def __repr__(self):
        return f'StringLeaf({self.value!r})'

    def nullable_visit(self, rules):
        return (not self.value)

    def initial_names(self):
        return set()

class Rhs():

    def __init__(self, alts):
        self.alts = alts
        self.memo: Optional[Tuple[(Optional[str], str)]] = None

    def __str__(self):
        return ' | '.join((str(alt) for alt in self.alts))

    def __repr__(self):
        return f'Rhs({self.alts!r})'

    def __iter__(self):
        (yield self.alts)

    def nullable_visit(self, rules):
        for alt in self.alts:
            if alt.nullable_visit(rules):
                return True
        return False

    def initial_names(self):
        names: Set[str] = set()
        for alt in self.alts:
            names |= alt.initial_names()
        return names

    def collect_todo(self, gen):
        for alt in self.alts:
            alt.collect_todo(gen)

class Alt():

    def __init__(self, items, *, icut=(- 1), action=None):
        self.items = items
        self.icut = icut
        self.action = action

    def __str__(self):
        core = ' '.join((str(item) for item in self.items))
        if ((not SIMPLE_STR) and self.action):
            return f'{core} {{ {self.action} }}'
        else:
            return core

    def __repr__(self):
        args = [repr(self.items)]
        if (self.icut >= 0):
            args.append(f'icut={self.icut}')
        if self.action:
            args.append(f'action={self.action!r}')
        return f"Alt({', '.join(args)})"

    def __iter__(self):
        (yield self.items)

    def nullable_visit(self, rules):
        for item in self.items:
            if (not item.nullable_visit(rules)):
                return False
        return True

    def initial_names(self):
        names: Set[str] = set()
        for item in self.items:
            names |= item.initial_names()
            if (not item.nullable):
                break
        return names

    def collect_todo(self, gen):
        for item in self.items:
            item.collect_todo(gen)

class NamedItem():

    def __init__(self, name, item):
        self.name = name
        self.item = item
        self.nullable = False

    def __str__(self):
        if ((not SIMPLE_STR) and self.name):
            return f'{self.name}={self.item}'
        else:
            return str(self.item)

    def __repr__(self):
        return f'NamedItem({self.name!r}, {self.item!r})'

    def __iter__(self):
        (yield self.item)

    def nullable_visit(self, rules):
        self.nullable = self.item.nullable_visit(rules)
        return self.nullable

    def initial_names(self):
        return self.item.initial_names()

    def collect_todo(self, gen):
        gen.callmakervisitor.visit(self.item)

class Lookahead():

    def __init__(self, node, sign):
        self.node = node
        self.sign = sign

    def __str__(self):
        return f'{self.sign}{self.node}'

    def __iter__(self):
        (yield self.node)

    def nullable_visit(self, rules):
        return True

    def initial_names(self):
        return set()

class PositiveLookahead(Lookahead):

    def __init__(self, node):
        super().__init__(node, '&')

    def __repr__(self):
        return f'PositiveLookahead({self.node!r})'

class NegativeLookahead(Lookahead):

    def __init__(self, node):
        super().__init__(node, '!')

    def __repr__(self):
        return f'NegativeLookahead({self.node!r})'

class Opt():

    def __init__(self, node):
        self.node = node

    def __str__(self):
        s = str(self.node)
        if (' ' in s):
            return f'[{s}]'
        else:
            return f'{s}?'

    def __repr__(self):
        return f'Opt({self.node!r})'

    def __iter__(self):
        (yield self.node)

    def nullable_visit(self, rules):
        return True

    def initial_names(self):
        return self.node.initial_names()

class Repeat():
    'Shared base class for x* and x+.'

    def __init__(self, node):
        self.node = node
        self.memo: Optional[Tuple[(Optional[str], str)]] = None

    @abstractmethod
    def nullable_visit(self, rules):
        raise NotImplementedError

    def __iter__(self):
        (yield self.node)

    def initial_names(self):
        return self.node.initial_names()

class Repeat0(Repeat):

    def __str__(self):
        s = str(self.node)
        if (' ' in s):
            return f'({s})*'
        else:
            return f'{s}*'

    def __repr__(self):
        return f'Repeat0({self.node!r})'

    def nullable_visit(self, rules):
        return True

class Repeat1(Repeat):

    def __str__(self):
        s = str(self.node)
        if (' ' in s):
            return f'({s})+'
        else:
            return f'{s}+'

    def __repr__(self):
        return f'Repeat1({self.node!r})'

    def nullable_visit(self, rules):
        return False

class Gather(Repeat):

    def __init__(self, separator, node):
        self.separator = separator
        self.node = node

    def __str__(self):
        return f'{self.separator!s}.{self.node!s}+'

    def __repr__(self):
        return f'Gather({self.separator!r}, {self.node!r})'

    def nullable_visit(self, rules):
        return False

class Group():

    def __init__(self, rhs):
        self.rhs = rhs

    def __str__(self):
        return f'({self.rhs})'

    def __repr__(self):
        return f'Group({self.rhs!r})'

    def __iter__(self):
        (yield self.rhs)

    def nullable_visit(self, rules):
        return self.rhs.nullable_visit(rules)

    def initial_names(self):
        return self.rhs.initial_names()

class Cut():

    def __init__(self):
        pass

    def __repr__(self):
        return f'Cut()'

    def __str__(self):
        return f'~'

    def __iter__(self):
        if False:
            (yield)

    def __eq__(self, other):
        if (not isinstance(other, Cut)):
            return NotImplemented
        return True

    def nullable_visit(self, rules):
        return True

    def initial_names(self):
        return set()
Plain = Union[(Leaf, Group)]
Item = Union[(Plain, Opt, Repeat, Lookahead, Rhs, Cut)]
RuleName = Tuple[(str, str)]
MetaTuple = Tuple[(str, Optional[str])]
MetaList = List[MetaTuple]
RuleList = List[Rule]
NamedItemList = List[NamedItem]
LookaheadOrCut = Union[(Lookahead, Cut)]
