
'Find the maximum amount of nesting for an expression that can be parsed\nwithout causing a parse error.\n\nStarting at the INITIAL_NESTING_DEPTH, an expression containing n parenthesis\naround a 0 is generated then tested with both the C and Python parsers. We\ncontinue incrementing the number of parenthesis by 10 until both parsers have\nfailed. As soon as a single parser fails, we stop testing that parser.\n\nThe grammar file, initial nesting size, and amount by which the nested size is\nincremented on each success can be controlled by changing the GRAMMAR_FILE,\nINITIAL_NESTING_DEPTH, or NESTED_INCR_AMT variables.\n\nUsage: python -m scripts.find_max_nesting\n'
import sys
import ast
GRAMMAR_FILE = 'data/python.gram'
INITIAL_NESTING_DEPTH = 10
NESTED_INCR_AMT = 10
FAIL = '\x1b[91m'
ENDC = '\x1b[0m'

def check_nested_expr(nesting_depth):
    expr = f"{('(' * nesting_depth)}0{(')' * nesting_depth)}"
    try:
        ast.parse(expr)
        print(f'Nesting depth of {nesting_depth} is successful')
        return True
    except Exception as err:
        print(f'{FAIL}(Failed with nesting depth of {nesting_depth}{ENDC}')
        print(f'{FAIL}	{err}{ENDC}')
        return False

def main():
    print(f'Testing {GRAMMAR_FILE} starting at nesting depth of {INITIAL_NESTING_DEPTH}...')
    nesting_depth = INITIAL_NESTING_DEPTH
    succeeded = True
    while succeeded:
        expr = f"{('(' * nesting_depth)}0{(')' * nesting_depth)}"
        if succeeded:
            succeeded = check_nested_expr(nesting_depth)
        nesting_depth += NESTED_INCR_AMT
    sys.exit(1)
if (__name__ == '__main__'):
    main()
