
" Convert a grammar into a dot-file suitable for use with GraphViz\n\n    For example:\n        Generate the GraphViz file:\n        # scripts/grammar_grapher.py data/python.gram > python.gv\n\n        Then generate the graph...\n\n        # twopi python.gv -Tpng > python_twopi.png\n\n        or\n\n        # dot python.gv -Tpng > python_dot.png\n\n        NOTE: The _dot_ and _twopi_ tools seem to produce the most useful results.\n              The _circo_ tool is the worst of the bunch. Don't even bother.\n"
import argparse
import sys
from typing import Any, List
sys.path.insert(0, '.')
from pegen.build import build_parser
from pegen.grammar import Alt, Cut, Grammar, Group, Leaf, Lookahead, Rule, NameLeaf, NamedItem, Opt, Repeat, Rhs
argparser = argparse.ArgumentParser(prog='graph_grammar', description='Graph a grammar tree')
argparser.add_argument('-s', '--start', choices=['exec', 'eval', 'single'], default='exec', help="Choose the grammar's start rule (exec, eval or single)")
argparser.add_argument('grammar_file', help='The grammar file to graph')

def references_for_item(item):
    if isinstance(item, Alt):
        return [_ref for _item in item.items for _ref in references_for_item(_item)]
    elif isinstance(item, Cut):
        return []
    elif isinstance(item, Group):
        return references_for_item(item.rhs)
    elif isinstance(item, Lookahead):
        return references_for_item(item.node)
    elif isinstance(item, NamedItem):
        return references_for_item(item.item)
    elif isinstance(item, NameLeaf):
        if (item.value == 'ENDMARKER'):
            return []
        return [item.value]
    elif isinstance(item, Leaf):
        return []
    elif isinstance(item, Opt):
        return references_for_item(item.node)
    elif isinstance(item, Repeat):
        return references_for_item(item.node)
    elif isinstance(item, Rhs):
        return [_ref for alt in item.alts for _ref in references_for_item(alt)]
    elif isinstance(item, Rule):
        return references_for_item(item.rhs)
    else:
        raise RuntimeError(f'Unknown item: {type(item)}')

def main():
    args = argparser.parse_args()
    try:
        (grammar, parser, tokenizer) = build_parser(args.grammar_file)
    except Exception as err:
        print('ERROR: Failed to parse grammar file', file=sys.stderr)
        sys.exit(1)
    references = {}
    for (name, rule) in grammar.rules.items():
        references[name] = set(references_for_item(rule))
    root_node = {'exec': 'file', 'eval': 'eval', 'single': 'interactive'}[args.start]
    print('digraph g1 {')
    print('\toverlap="scale";')
    print(f'	root="{root_node}";')
    print(f'	{root_node} [color=green, shape=circle];')
    for (name, refs) in references.items():
        for ref in refs:
            print(f'	{name} -> {ref};')
    print('}')
if (__name__ == '__main__'):
    main()
