
from collections import namedtuple
import shlex
import os
import re
from ..common import util, info
CONTINUATION = ('\\' + os.linesep)
IDENTIFIER = '(?:\\w*[a-zA-Z]\\w*)'
IDENTIFIER_RE = re.compile((('^' + IDENTIFIER) + '$'))

def _coerce_str(value):
    if (not value):
        return ''
    return str(value).strip()
DIRECTIVE_START = '\n    (?:\n      ^ \\s*\n      [#] \\s*\n      )'
DIRECTIVE_TEXT = '\n    (?:\n      (?: \\s+ ( .*\\S ) )?\n      \\s* $\n      )'
DIRECTIVE = f'''
    (?:
      {DIRECTIVE_START}
      (
        include |
        error | warning |
        pragma |
        define | undef |
        if | ifdef | ifndef | elseif | else | endif |
        __FILE__ | __LINE__ | __DATE __ | __TIME__ | __TIMESTAMP__
        )
      {DIRECTIVE_TEXT}
      )'''
DIRECTIVE_RE = re.compile(DIRECTIVE, re.VERBOSE)
DEFINE = f'''
    (?:
      {DIRECTIVE_START} define \s+
      (?:
        ( \w*[a-zA-Z]\w* )
        (?: \s* [(] ([^)]*) [)] )?
        )
      {DIRECTIVE_TEXT}
      )'''
DEFINE_RE = re.compile(DEFINE, re.VERBOSE)

def parse_directive(line):
    'Return the appropriate directive for the given line.'
    line = line.strip()
    if line.startswith('#'):
        line = line[1:].lstrip()
        line = ('#' + line)
    directive = line
    while ('  ' in directive):
        directive = directive.replace('  ', ' ')
    return _parse_directive(directive)

def _parse_directive(line):
    m = DEFINE_RE.match(line)
    if m:
        (name, args, text) = m.groups()
        if args:
            args = [a.strip() for a in args.split(',')]
            return Macro(name, args, text)
        else:
            return Constant(name, text)
    m = DIRECTIVE_RE.match(line)
    if (not m):
        raise ValueError(f'unsupported directive {line!r}')
    (kind, text) = m.groups()
    if (not text):
        if (kind not in ('else', 'endif')):
            raise ValueError(f'missing text in directive {line!r}')
    elif (kind in ('else', 'endif', 'define')):
        raise ValueError(f'unexpected text in directive {line!r}')
    if (kind == 'include'):
        directive = Include(text)
    elif (kind in IfDirective.KINDS):
        directive = IfDirective(kind, text)
    else:
        directive = OtherDirective(kind, text)
    directive.validate()
    return directive

class PreprocessorDirective(util._NTBase):
    'The base class for directives.'
    __slots__ = ()
    KINDS = frozenset(['include', 'pragma', 'error', 'warning', 'define', 'undef', 'if', 'ifdef', 'ifndef', 'elseif', 'else', 'endif', '__FILE__', '__DATE__', '__LINE__', '__TIME__', '__TIMESTAMP__'])

    @property
    def text(self):
        return (' '.join((v for v in self[1:] if (v and v.strip()))) or None)

    def validate(self):
        'Fail if the object is invalid (i.e. init with bad data).'
        super().validate()
        if (not self.kind):
            raise TypeError('missing kind')
        elif (self.kind not in self.KINDS):
            raise ValueError

class Constant(PreprocessorDirective, namedtuple('Constant', 'kind name value')):
    'A single "constant" directive ("define").'
    __slots__ = ()

    def __new__(cls, name, value=None):
        self = super().__new__(cls, 'define', name=(_coerce_str(name) or None), value=(_coerce_str(value) or None))
        return self

    def validate(self):
        'Fail if the object is invalid (i.e. init with bad data).'
        super().validate()
        if (not self.name):
            raise TypeError('missing name')
        elif (not IDENTIFIER_RE.match(self.name)):
            raise ValueError(f'name must be identifier, got {self.name!r}')

class Macro(PreprocessorDirective, namedtuple('Macro', 'kind name args body')):
    'A single "macro" directive ("define").'
    __slots__ = ()

    def __new__(cls, name, args, body=None):
        if isinstance(args, str):
            args = [v.strip() for v in args.split(',')]
        if args:
            args = tuple(((_coerce_str(a) or None) for a in args))
        self = super().__new__(cls, kind='define', name=(_coerce_str(name) or None), args=(args if args else ()), body=(_coerce_str(body) or None))
        return self

    @property
    def text(self):
        if self.body:
            return f"{self.name}({', '.join(self.args)}) {self.body}"
        else:
            return f"{self.name}({', '.join(self.args)})"

    def validate(self):
        'Fail if the object is invalid (i.e. init with bad data).'
        super().validate()
        if (not self.name):
            raise TypeError('missing name')
        elif (not IDENTIFIER_RE.match(self.name)):
            raise ValueError(f'name must be identifier, got {self.name!r}')
        for arg in self.args:
            if (not arg):
                raise ValueError(f'missing arg in {self.args}')
            elif (not IDENTIFIER_RE.match(arg)):
                raise ValueError(f'arg must be identifier, got {arg!r}')

class IfDirective(PreprocessorDirective, namedtuple('IfDirective', 'kind condition')):
    'A single conditional directive (e.g. "if", "ifdef").\n\n    This only includes directives that actually provide conditions.  The\n    related directives "else" and "endif" are covered by OtherDirective\n    instead.\n    '
    __slots__ = ()
    KINDS = frozenset(['if', 'ifdef', 'ifndef', 'elseif'])

    @classmethod
    def _condition_from_raw(cls, raw, kind):
        condition = _coerce_str(raw)
        if (not condition):
            return None
        if (kind == 'ifdef'):
            condition = f'defined({condition})'
        elif (kind == 'ifndef'):
            condition = f'! defined({condition})'
        return condition

    def __new__(cls, kind, condition):
        kind = _coerce_str(kind)
        self = super().__new__(cls, kind=(kind or None), condition=cls._condition_from_raw(condition, kind))
        return self

    @property
    def text(self):
        if (self.kind == 'ifdef'):
            return self.condition[8:(- 1)]
        elif (self.kind == 'ifndef'):
            return self.condition[10:(- 1)]
        else:
            return self.condition

    def validate(self):
        'Fail if the object is invalid (i.e. init with bad data).'
        super().validate()
        if (not self.condition):
            raise TypeError('missing condition')

class Include(PreprocessorDirective, namedtuple('Include', 'kind file')):
    'A single "include" directive.\n\n    Supported "file" values are either follow the bracket style\n    (<stdio>) or double quotes ("spam.h").\n    '
    __slots__ = ()

    def __new__(cls, file):
        self = super().__new__(cls, kind='include', file=(_coerce_str(file) or None))
        return self

    def validate(self):
        'Fail if the object is invalid (i.e. init with bad data).'
        super().validate()
        if (not self.file):
            raise TypeError('missing file')

class OtherDirective(PreprocessorDirective, namedtuple('OtherDirective', 'kind text')):
    'A single directive not covered by another class.\n\n    This includes the "else", "endif", and "undef" directives, which are\n    otherwise inherently related to the directives covered by the\n    Constant, Macro, and IfCondition classes.\n\n    Note that all directives must have a text value, except for "else"\n    and "endif" (which must have no text).\n    '
    __slots__ = ()
    KINDS = ((PreprocessorDirective.KINDS - {'include', 'define'}) - IfDirective.KINDS)

    def __new__(cls, kind, text):
        self = super().__new__(cls, kind=(_coerce_str(kind) or None), text=(_coerce_str(text) or None))
        return self

    def validate(self):
        'Fail if the object is invalid (i.e. init with bad data).'
        super().validate()
        if self.text:
            if (self.kind in ('else', 'endif')):
                raise ValueError('unexpected text in directive')
        elif (self.kind not in ('else', 'endif')):
            raise TypeError('missing text')

def _recompute_conditions(directive, ifstack):
    if (directive.kind in ('if', 'ifdef', 'ifndef')):
        ifstack.append(([], directive.condition))
    elif (directive.kind == 'elseif'):
        if ifstack:
            (negated, active) = ifstack.pop()
            if active:
                negated.append(active)
        else:
            negated = []
        ifstack.append((negated, directive.condition))
    elif (directive.kind == 'else'):
        if ifstack:
            (negated, active) = ifstack.pop()
            if active:
                negated.append(active)
            ifstack.append((negated, None))
    elif (directive.kind == 'endif'):
        if ifstack:
            ifstack.pop()
    conditions = []
    for (negated, active) in ifstack:
        for condition in negated:
            conditions.append(f'! ({condition})')
        if active:
            conditions.append(active)
    return tuple(conditions)

def _iter_clean_lines(lines):
    lines = iter(enumerate(lines, 1))
    for (lno, line) in lines:
        while line.endswith(CONTINUATION):
            try:
                (lno, _line) = next(lines)
            except StopIteration:
                break
            line = ((line[:(- len(CONTINUATION))] + ' ') + _line)
        after = line
        line = ''
        while True:
            (before, begin, remainder) = after.partition('/*')
            if ('//' in before):
                (before, _, _) = before.partition('//')
                line += (before + ' ')
                break
            line += before
            if (not begin):
                break
            line += ' '
            (_, end, after) = remainder.partition('*/')
            while (not end):
                try:
                    (lno, remainder) = next(lines)
                except StopIteration:
                    raise Exception('unterminated comment')
                (_, end, after) = remainder.partition('*/')
        (yield (lno, line))

def iter_lines(lines, *, _iter_clean_lines=_iter_clean_lines, _parse_directive=_parse_directive, _recompute_conditions=_recompute_conditions):
    'Yield (lno, line, directive, active conditions) for each given line.\n\n    This is effectively a subset of the operations taking place in\n    translation phases 2-4 from the C99 spec (ISO/IEC 9899:TC2); see\n    section 5.1.1.2.  Line continuations are removed and comments\n    replaced with a single space.  (In both cases "lno" will be the last\n    line involved.)  Otherwise each line is returned as-is.\n\n    "lno" is the (1-indexed) line number for the line.\n\n    "directive" will be a PreprocessorDirective or None, depending on\n    whether or not there is a directive on the line.\n\n    "active conditions" is the set of preprocessor conditions (e.g.\n    "defined()") under which the current line of code will be included\n    in compilation.  That set is derived from every conditional\n    directive block (e.g. "if defined()", "ifdef", "else") containing\n    that line.  That includes nested directives.  Note that the\n    current line does not affect the active conditions for iteself.\n    It only impacts subsequent lines.  That applies to directives\n    that close blocks (e.g. "endif") just as much as conditional\n    directvies.  Also note that "else" and "elseif" directives\n    update the active conditions (for later lines), rather than\n    adding to them.\n    '
    ifstack = []
    conditions = ()
    for (lno, line) in _iter_clean_lines(lines):
        stripped = line.strip()
        if (not stripped.startswith('#')):
            (yield (lno, line, None, conditions))
            continue
        directive = ('#' + stripped[1:].lstrip())
        while ('  ' in directive):
            directive = directive.replace('  ', ' ')
        directive = _parse_directive(directive)
        (yield (lno, line, directive, conditions))
        if (directive.kind in ('else', 'endif')):
            conditions = _recompute_conditions(directive, ifstack)
        elif isinstance(directive, IfDirective):
            conditions = _recompute_conditions(directive, ifstack)

def _gcc(filename, *, _get_argv=(lambda : _get_gcc_argv()), _run=util.run_cmd):
    argv = _get_argv()
    argv.extend(['-E', filename])
    output = _run(argv)
    return output

def _get_gcc_argv(*, _open=open, _run=util.run_cmd):
    with _open('/tmp/print.mk', 'w') as tmpfile:
        tmpfile.write('print-%:\n')
        tmpfile.write('\t@echo $($*)\n')
    argv = ['/usr/bin/make', '-f', 'Makefile', '-f', '/tmp/print.mk', 'print-CC', 'print-PY_CORE_CFLAGS']
    output = _run(argv)
    (gcc, cflags) = output.strip().splitlines()
    argv = shlex.split(gcc.strip())
    cflags = shlex.split(cflags.strip())
    return (argv + cflags)

def run(filename, *, _gcc=_gcc):
    'Return the text of the given file after running the preprocessor.'
    return _gcc(filename)
