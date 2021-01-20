
import re
import shlex
import subprocess
from ..common.info import UNKNOWN
from . import source
IDENTIFIER = '(?:[a-zA-z]|_+[a-zA-Z0-9]\\w*)'
TYPE_QUAL = '(?:const|volatile)'
VAR_TYPE_SPEC = '(?:\n        void |\n        (?:\n         (?:(?:un)?signed\\s+)?\n         (?:\n          char |\n          short |\n          int |\n          long |\n          long\\s+int |\n          long\\s+long\n          ) |\n         ) |\n        float |\n        double |\n        {IDENTIFIER} |\n        (?:struct|union)\\s+{IDENTIFIER}\n        )'
POINTER = f'''(?:
        (?:\s+const)?\s*[*]
        )'''
FUNC_START = f'''(?:
        (?:
          (?:
            extern |
            static |
            static\s+inline
           )\s+
         )?
        #(?:const\s+)?
        {VAR_TYPE_SPEC}
        )'''
GLOBAL_DECL_START_RE = re.compile(f'''
        ^
        (?:
            ({FUNC_START})
         )
        ''', re.VERBOSE)
LOCAL_VAR_START = f'''(?:
        (?:
          (?:
            register |
            static
           )\s+
         )?
        (?:
          (?:
            {TYPE_QUAL}
            (?:\s+{TYPE_QUAL})?
           )\s+
         )?
        {VAR_TYPE_SPEC}
        {POINTER}?
        )'''
LOCAL_STMT_START_RE = re.compile(f'''
        ^
        (?:
            ({LOCAL_VAR_START})
         )
        ''', re.VERBOSE)

def iter_global_declarations(lines):
    'Yield (decl, body) for each global declaration in the given lines.\n\n    For function definitions the header is reduced to one line and\n    the body is provided as-is.  For other compound declarations (e.g.\n    struct) the entire declaration is reduced to one line and "body"\n    is None.  Likewise for simple declarations (e.g. variables).\n\n    Declarations inside function bodies are ignored, though their text\n    is provided in the function body.\n    '
    lines = source.iter_clean_lines(lines)
    for line in lines:
        if (not GLOBAL_DECL_START_RE.match(line)):
            continue
        if line.endswith(';'):
            continue
        if (line.endswith('{') and ('(' not in line)):
            continue
        decl = line
        while ('{' not in line):
            try:
                line = next(lines)
            except StopIteration:
                return
            decl += (' ' + line)
        (body, end) = _extract_block(lines)
        if (end is None):
            return
        assert (end == '}')
        (yield (f'''{decl}
{body}
{end}''', body))

def iter_local_statements(lines):
    'Yield (lines, blocks) for each statement in the given lines.\n\n    For simple statements, "blocks" is None and the statement is reduced\n    to a single line.  For compound statements, "blocks" is a pair of\n    (header, body) for each block in the statement.  The headers are\n    reduced to a single line each, but the bpdies are provided as-is.\n    '
    lines = source.iter_clean_lines(lines)
    for line in lines:
        if (not LOCAL_STMT_START_RE.match(line)):
            continue
        stmt = line
        blocks = None
        if (not line.endswith(';')):
            continue
        (yield (stmt, blocks))

def _extract_block(lines):
    end = None
    depth = 1
    body = []
    for line in lines:
        depth += (line.count('{') - line.count('}'))
        if (depth == 0):
            end = line
            break
        body.append(line)
    return ('\n'.join(body), end)

def parse_func(stmt, body):
    'Return (name, signature) for the given function definition.'
    (header, _, end) = stmt.partition(body)
    assert (end.strip() == '}')
    assert header.strip().endswith('{')
    (header, _, _) = header.rpartition('{')
    signature = ' '.join(header.strip().splitlines())
    (_, _, name) = signature.split('(')[0].strip().rpartition(' ')
    assert name
    return (name, signature)

def _parse_var(stmt):
    'Return (name, vartype) for the given variable declaration.'
    stmt = stmt.rstrip(';')
    m = LOCAL_STMT_START_RE.match(stmt)
    assert m
    vartype = m.group(0)
    name = stmt[len(vartype):].partition('=')[0].strip()
    if name.startswith('('):
        (name, _, after) = name[1:].partition(')')
        assert after
        name = name.replace('*', '* ')
        (inside, _, name) = name.strip().rpartition(' ')
        vartype = f'{vartype} ({inside.strip()}){after}'
    else:
        name = name.replace('*', '* ')
        (before, _, name) = name.rpartition(' ')
        vartype = f'{vartype} {before}'
    vartype = vartype.strip()
    while ('  ' in vartype):
        vartype = vartype.replace('  ', ' ')
    return (name, vartype)

def extract_storage(decl, *, infunc=None):
    'Return (storage, vartype) based on the given declaration.\n\n    The default storage is "implicit" (or "local" if infunc is True).\n    '
    if (decl == UNKNOWN):
        return decl
    if decl.startswith('static '):
        return 'static'
    elif decl.startswith('extern '):
        return 'extern'
    elif re.match('.*\x08(static|extern)\x08', decl):
        raise NotImplementedError
    elif infunc:
        return 'local'
    else:
        return 'implicit'

def parse_compound(stmt, blocks):
    'Return (headers, bodies) for the given compound statement.'
    raise NotImplementedError

def iter_variables(filename, *, preprocessed=False, _iter_source_lines=source.iter_lines, _iter_global=iter_global_declarations, _iter_local=iter_local_statements, _parse_func=parse_func, _parse_var=_parse_var, _parse_compound=parse_compound):
    'Yield (funcname, name, vartype) for every variable in the given file.'
    if preprocessed:
        raise NotImplementedError
    lines = _iter_source_lines(filename)
    for (stmt, body) in _iter_global(lines):
        if (not body):
            (name, vartype) = _parse_var(stmt)
            if name:
                (yield (None, name, vartype))
        else:
            (funcname, _) = _parse_func(stmt, body)
            localvars = _iter_locals(body, _iter_statements=_iter_local, _parse_var=_parse_var, _parse_compound=_parse_compound)
            for (name, vartype) in localvars:
                (yield (funcname, name, vartype))

def _iter_locals(lines, *, _iter_statements=iter_local_statements, _parse_var=_parse_var, _parse_compound=parse_compound):
    compound = [lines]
    while compound:
        body = compound.pop(0)
        bodylines = body.splitlines()
        for (stmt, blocks) in _iter_statements(bodylines):
            if (not blocks):
                (name, vartype) = _parse_var(stmt)
                if name:
                    (yield (name, vartype))
            else:
                (headers, bodies) = _parse_compound(stmt, blocks)
                for header in headers:
                    for line in header:
                        (name, vartype) = _parse_var(line)
                        if name:
                            (yield (name, vartype))
                compound.extend(bodies)

def iter_all(filename, *, preprocessed=False):
    'Yield a Declaration for each one found.\n\n    If there are duplicates, due to preprocessor conditionals, then\n    they are checked to make sure they are the same.\n    '
    for (funcname, name, decl) in iter_variables(filename, preprocessed=preprocessed):
        (yield ('variable', funcname, name, decl))
