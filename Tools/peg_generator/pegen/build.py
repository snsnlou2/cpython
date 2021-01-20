
import pathlib
import shutil
import tokenize
import sysconfig
import tempfile
import itertools
from typing import Optional, Tuple, List, IO, Set, Dict
from pegen.c_generator import CParserGenerator
from pegen.grammar import Grammar
from pegen.grammar_parser import GeneratedParser as GrammarParser
from pegen.parser import Parser
from pegen.parser_generator import ParserGenerator
from pegen.python_generator import PythonParserGenerator
from pegen.tokenizer import Tokenizer
MOD_DIR = pathlib.Path(__file__).resolve().parent
TokenDefinitions = Tuple[(Dict[(int, str)], Dict[(str, int)], Set[str])]

def get_extra_flags(compiler_flags, compiler_py_flags_nodist):
    flags = sysconfig.get_config_var(compiler_flags)
    py_flags_nodist = sysconfig.get_config_var(compiler_py_flags_nodist)
    if ((flags is None) or (py_flags_nodist is None)):
        return []
    return f'{flags} {py_flags_nodist}'.split()

def compile_c_extension(generated_source_path, build_dir=None, verbose=False, keep_asserts=True):
    'Compile the generated source for a parser generator into an extension module.\n\n    The extension module will be generated in the same directory as the provided path\n    for the generated source, with the same basename (in addition to extension module\n    metadata). For example, for the source mydir/parser.c the generated extension\n    in a darwin system with python 3.8 will be mydir/parser.cpython-38-darwin.so.\n\n    If *build_dir* is provided, that path will be used as the temporary build directory\n    of distutils (this is useful in case you want to use a temporary directory).\n    '
    import distutils.log
    from distutils.core import Distribution, Extension
    from distutils.command.clean import clean
    from distutils.command.build_ext import build_ext
    from distutils.tests.support import fixup_build_ext
    if verbose:
        distutils.log.set_verbosity(distutils.log.DEBUG)
    source_file_path = pathlib.Path(generated_source_path)
    extension_name = source_file_path.stem
    extra_compile_args = get_extra_flags('CFLAGS', 'PY_CFLAGS_NODIST')
    extra_link_args = get_extra_flags('LDFLAGS', 'PY_LDFLAGS_NODIST')
    if keep_asserts:
        extra_compile_args.append('-UNDEBUG')
    extension = [Extension(extension_name, sources=[str(((MOD_DIR.parent.parent.parent / 'Python') / 'Python-ast.c')), str(((MOD_DIR.parent.parent.parent / 'Python') / 'asdl.c')), str(((MOD_DIR.parent.parent.parent / 'Parser') / 'tokenizer.c')), str(((MOD_DIR.parent.parent.parent / 'Parser') / 'pegen.c')), str(((MOD_DIR.parent.parent.parent / 'Parser') / 'string_parser.c')), str(((MOD_DIR.parent / 'peg_extension') / 'peg_extension.c')), generated_source_path], include_dirs=[str(((MOD_DIR.parent.parent.parent / 'Include') / 'internal')), str((MOD_DIR.parent.parent.parent / 'Parser'))], extra_compile_args=extra_compile_args, extra_link_args=extra_link_args)]
    dist = Distribution({'name': extension_name, 'ext_modules': extension})
    cmd = build_ext(dist)
    fixup_build_ext(cmd)
    cmd.inplace = True
    if build_dir:
        cmd.build_temp = build_dir
        cmd.build_lib = build_dir
    cmd.ensure_finalized()
    cmd.run()
    extension_path = (source_file_path.parent / cmd.get_ext_filename(extension_name))
    shutil.move(cmd.get_ext_fullpath(extension_name), extension_path)
    cmd = clean(dist)
    cmd.finalize_options()
    cmd.run()
    return extension_path

def build_parser(grammar_file, verbose_tokenizer=False, verbose_parser=False):
    with open(grammar_file) as file:
        tokenizer = Tokenizer(tokenize.generate_tokens(file.readline), verbose=verbose_tokenizer)
        parser = GrammarParser(tokenizer, verbose=verbose_parser)
        grammar = parser.start()
        if (not grammar):
            raise parser.make_syntax_error(grammar_file)
    return (grammar, parser, tokenizer)

def generate_token_definitions(tokens):
    all_tokens = {}
    exact_tokens = {}
    non_exact_tokens = set()
    numbers = itertools.count(0)
    for line in tokens:
        line = line.strip()
        if ((not line) or line.startswith('#')):
            continue
        pieces = line.split()
        index = next(numbers)
        if (len(pieces) == 1):
            (token,) = pieces
            non_exact_tokens.add(token)
            all_tokens[index] = token
        elif (len(pieces) == 2):
            (token, op) = pieces
            exact_tokens[op.strip("'")] = index
            all_tokens[index] = token
        else:
            raise ValueError(f'Unexpected line found in Tokens file: {line}')
    return (all_tokens, exact_tokens, non_exact_tokens)

def build_c_generator(grammar, grammar_file, tokens_file, output_file, compile_extension=False, verbose_c_extension=False, keep_asserts_in_extension=True, skip_actions=False):
    with open(tokens_file, 'r') as tok_file:
        (all_tokens, exact_tok, non_exact_tok) = generate_token_definitions(tok_file)
    with open(output_file, 'w') as file:
        gen: ParserGenerator = CParserGenerator(grammar, all_tokens, exact_tok, non_exact_tok, file, skip_actions=skip_actions)
        gen.generate(grammar_file)
    if compile_extension:
        with tempfile.TemporaryDirectory() as build_dir:
            compile_c_extension(output_file, build_dir=build_dir, verbose=verbose_c_extension, keep_asserts=keep_asserts_in_extension)
    return gen

def build_python_generator(grammar, grammar_file, output_file, skip_actions=False):
    with open(output_file, 'w') as file:
        gen: ParserGenerator = PythonParserGenerator(grammar, file)
        gen.generate(grammar_file)
    return gen

def build_c_parser_and_generator(grammar_file, tokens_file, output_file, compile_extension=False, verbose_tokenizer=False, verbose_parser=False, verbose_c_extension=False, keep_asserts_in_extension=True, skip_actions=False):
    'Generate rules, C parser, tokenizer, parser generator for a given grammar\n\n    Args:\n        grammar_file (string): Path for the grammar file\n        tokens_file (string): Path for the tokens file\n        output_file (string): Path for the output file\n        compile_extension (bool, optional): Whether to compile the C extension.\n          Defaults to False.\n        verbose_tokenizer (bool, optional): Whether to display additional output\n          when generating the tokenizer. Defaults to False.\n        verbose_parser (bool, optional): Whether to display additional output\n          when generating the parser. Defaults to False.\n        verbose_c_extension (bool, optional): Whether to display additional\n          output when compiling the C extension . Defaults to False.\n        keep_asserts_in_extension (bool, optional): Whether to keep the assert statements\n          when compiling the extension module. Defaults to True.\n        skip_actions (bool, optional): Whether to pretend no rule has any actions.\n    '
    (grammar, parser, tokenizer) = build_parser(grammar_file, verbose_tokenizer, verbose_parser)
    gen = build_c_generator(grammar, grammar_file, tokens_file, output_file, compile_extension, verbose_c_extension, keep_asserts_in_extension, skip_actions=skip_actions)
    return (grammar, parser, tokenizer, gen)

def build_python_parser_and_generator(grammar_file, output_file, verbose_tokenizer=False, verbose_parser=False, skip_actions=False):
    'Generate rules, python parser, tokenizer, parser generator for a given grammar\n\n    Args:\n        grammar_file (string): Path for the grammar file\n        output_file (string): Path for the output file\n        verbose_tokenizer (bool, optional): Whether to display additional output\n          when generating the tokenizer. Defaults to False.\n        verbose_parser (bool, optional): Whether to display additional output\n          when generating the parser. Defaults to False.\n        skip_actions (bool, optional): Whether to pretend no rule has any actions.\n    '
    (grammar, parser, tokenizer) = build_parser(grammar_file, verbose_tokenizer, verbose_parser)
    gen = build_python_generator(grammar, grammar_file, output_file, skip_actions=skip_actions)
    return (grammar, parser, tokenizer, gen)
