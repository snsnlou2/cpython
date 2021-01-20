
import argparse
import sys
import time
import token
import tokenize
import traceback
from abc import abstractmethod
from typing import Any, Callable, cast, Dict, Optional, Tuple, Type, TypeVar
from pegen.tokenizer import exact_token_types
from pegen.tokenizer import Mark
from pegen.tokenizer import Tokenizer
T = TypeVar('T')
P = TypeVar('P', bound='Parser')
F = TypeVar('F', bound=Callable[(..., Any)])

def logger(method):
    'For non-memoized functions that we want to be logged.\n\n    (In practice this is only non-leader left-recursive functions.)\n    '
    method_name = method.__name__

    def logger_wrapper(self: P, *args: object) -> T:
        if (not self._verbose):
            return method(self, *args)
        argsr = ','.join((repr(arg) for arg in args))
        fill = ('  ' * self._level)
        print(f'{fill}{method_name}({argsr}) .... (looking at {self.showpeek()})')
        self._level += 1
        tree = method(self, *args)
        self._level -= 1
        print(f'{fill}... {method_name}({argsr}) --> {tree!s:.200}')
        return tree
    logger_wrapper.__wrapped__ = method
    return cast(F, logger_wrapper)

def memoize(method):
    'Memoize a symbol method.'
    method_name = method.__name__

    def memoize_wrapper(self: P, *args: object) -> T:
        mark = self.mark()
        key = (mark, method_name, args)
        if ((key in self._cache) and (not self._verbose)):
            (tree, endmark) = self._cache[key]
            self.reset(endmark)
            return tree
        verbose = self._verbose
        argsr = ','.join((repr(arg) for arg in args))
        fill = ('  ' * self._level)
        if (key not in self._cache):
            if verbose:
                print(f'{fill}{method_name}({argsr}) ... (looking at {self.showpeek()})')
            self._level += 1
            tree = method(self, *args)
            self._level -= 1
            if verbose:
                print(f'{fill}... {method_name}({argsr}) -> {tree!s:.200}')
            endmark = self.mark()
            self._cache[key] = (tree, endmark)
        else:
            (tree, endmark) = self._cache[key]
            if verbose:
                print(f'{fill}{method_name}({argsr}) -> {tree!s:.200}')
            self.reset(endmark)
        return tree
    memoize_wrapper.__wrapped__ = method
    return cast(F, memoize_wrapper)

def memoize_left_rec(method):
    'Memoize a left-recursive symbol method.'
    method_name = method.__name__

    def memoize_left_rec_wrapper(self: P) -> Optional[T]:
        mark = self.mark()
        key = (mark, method_name, ())
        if ((key in self._cache) and (not self._verbose)):
            (tree, endmark) = self._cache[key]
            self.reset(endmark)
            return tree
        verbose = self._verbose
        fill = ('  ' * self._level)
        if (key not in self._cache):
            if verbose:
                print(f'{fill}{method_name} ... (looking at {self.showpeek()})')
            self._level += 1
            self._cache[key] = (None, mark)
            (lastresult, lastmark) = (None, mark)
            depth = 0
            if verbose:
                print(f'{fill}Recursive {method_name} at {mark} depth {depth}')
            while True:
                self.reset(mark)
                result = method(self)
                endmark = self.mark()
                depth += 1
                if verbose:
                    print(f'{fill}Recursive {method_name} at {mark} depth {depth}: {result!s:.200} to {endmark}')
                if (not result):
                    if verbose:
                        print(f'{fill}Fail with {lastresult!s:.200} to {lastmark}')
                    break
                if (endmark <= lastmark):
                    if verbose:
                        print(f'{fill}Bailing with {lastresult!s:.200} to {lastmark}')
                    break
                self._cache[key] = (lastresult, lastmark) = (result, endmark)
            self.reset(lastmark)
            tree = lastresult
            self._level -= 1
            if verbose:
                print(f'{fill}{method_name}() -> {tree!s:.200} [cached]')
            if tree:
                endmark = self.mark()
            else:
                endmark = mark
                self.reset(endmark)
            self._cache[key] = (tree, endmark)
        else:
            (tree, endmark) = self._cache[key]
            if verbose:
                print(f'{fill}{method_name}() -> {tree!s:.200} [fresh]')
            if tree:
                self.reset(endmark)
        return tree
    memoize_left_rec_wrapper.__wrapped__ = method
    return memoize_left_rec_wrapper

class Parser():
    'Parsing base class.'

    def __init__(self, tokenizer, *, verbose=False):
        self._tokenizer = tokenizer
        self._verbose = verbose
        self._level = 0
        self._cache: Dict[(Tuple[(Mark, str, Tuple[(Any, ...)])], Tuple[(Any, Mark)])] = {}
        self.mark = self._tokenizer.mark
        self.reset = self._tokenizer.reset

    @abstractmethod
    def start(self):
        pass

    def showpeek(self):
        tok = self._tokenizer.peek()
        return f'{tok.start[0]}.{tok.start[1]}: {token.tok_name[tok.type]}:{tok.string!r}'

    @memoize
    def name(self):
        tok = self._tokenizer.peek()
        if (tok.type == token.NAME):
            return self._tokenizer.getnext()
        return None

    @memoize
    def number(self):
        tok = self._tokenizer.peek()
        if (tok.type == token.NUMBER):
            return self._tokenizer.getnext()
        return None

    @memoize
    def string(self):
        tok = self._tokenizer.peek()
        if (tok.type == token.STRING):
            return self._tokenizer.getnext()
        return None

    @memoize
    def op(self):
        tok = self._tokenizer.peek()
        if (tok.type == token.OP):
            return self._tokenizer.getnext()
        return None

    @memoize
    def expect(self, type):
        tok = self._tokenizer.peek()
        if (tok.string == type):
            return self._tokenizer.getnext()
        if (type in exact_token_types):
            if (tok.type == exact_token_types[type]):
                return self._tokenizer.getnext()
        if (type in token.__dict__):
            if (tok.type == token.__dict__[type]):
                return self._tokenizer.getnext()
        if ((tok.type == token.OP) and (tok.string == type)):
            return self._tokenizer.getnext()
        return None

    def positive_lookahead(self, func, *args):
        mark = self.mark()
        ok = func(*args)
        self.reset(mark)
        return ok

    def negative_lookahead(self, func, *args):
        mark = self.mark()
        ok = func(*args)
        self.reset(mark)
        return (not ok)

    def make_syntax_error(self, filename='<unknown>'):
        tok = self._tokenizer.diagnose()
        return SyntaxError('pegen parse failure', (filename, tok.start[0], (1 + tok.start[1]), tok.line))

def simple_parser_main(parser_class):
    argparser = argparse.ArgumentParser()
    argparser.add_argument('-v', '--verbose', action='count', default=0, help='Print timing stats; repeat for more debug output')
    argparser.add_argument('-q', '--quiet', action='store_true', help="Don't print the parsed program")
    argparser.add_argument('filename', help="Input file ('-' to use stdin)")
    args = argparser.parse_args()
    verbose = args.verbose
    verbose_tokenizer = (verbose >= 3)
    verbose_parser = ((verbose == 2) or (verbose >= 4))
    t0 = time.time()
    filename = args.filename
    if ((filename == '') or (filename == '-')):
        filename = '<stdin>'
        file = sys.stdin
    else:
        file = open(args.filename)
    try:
        tokengen = tokenize.generate_tokens(file.readline)
        tokenizer = Tokenizer(tokengen, verbose=verbose_tokenizer)
        parser = parser_class(tokenizer, verbose=verbose_parser)
        tree = parser.start()
        try:
            if file.isatty():
                endpos = 0
            else:
                endpos = file.tell()
        except IOError:
            endpos = 0
    finally:
        if (file is not sys.stdin):
            file.close()
    t1 = time.time()
    if (not tree):
        err = parser.make_syntax_error(filename)
        traceback.print_exception(err.__class__, err, None)
        sys.exit(1)
    if (not args.quiet):
        print(tree)
    if verbose:
        dt = (t1 - t0)
        diag = tokenizer.diagnose()
        nlines = diag.end[0]
        if (diag.type == token.ENDMARKER):
            nlines -= 1
        print(f'Total time: {dt:.3f} sec; {nlines} lines', end='')
        if endpos:
            print(f' ({endpos} bytes)', end='')
        if dt:
            print(f'; {(nlines / dt):.0f} lines/sec')
        else:
            print()
        print('Caches sizes:')
        print(f'  token array : {len(tokenizer._tokens):10}')
        print(f'        cache : {len(parser._cache):10}')
