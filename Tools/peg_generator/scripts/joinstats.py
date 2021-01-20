
'Produce a report about the most-memoable types.\n\nReads a list of statistics from stdin.  Each line must be two numbers,\nbeing a type and a count.  We then read some other files and produce a\nlist sorted by most frequent type.\n\nThere should also be something to recognize left-recursive rules.\n'
import os
import re
import sys
from typing import Dict
reporoot = os.path.dirname(os.path.dirname(__file__))
parse_c = os.path.join(reporoot, 'peg_extension', 'parse.c')

class TypeMapper():
    'State used to map types to names.'

    def __init__(self, filename):
        self.table: Dict[(int, str)] = {}
        with open(filename) as f:
            for line in f:
                match = re.match('#define (\\w+)_type (\\d+)', line)
                if match:
                    (name, type) = match.groups()
                    if ('left' in line.lower()):
                        name += ' // Left-recursive'
                    self.table[int(type)] = name

    def lookup(self, type):
        return self.table.get(type, str(type))

def main():
    mapper = TypeMapper(parse_c)
    table = []
    filename = sys.argv[1]
    with open(filename) as f:
        for (lineno, line) in enumerate(f, 1):
            line = line.strip()
            if ((not line) or line.startswith('#')):
                continue
            parts = line.split()
            if (len(parts) < 2):
                print(f'{lineno}: bad input ({line!r})')
                continue
            try:
                (type, count) = map(int, parts[:2])
            except ValueError as err:
                print(f'{lineno}: non-integer input ({line!r})')
                continue
            table.append((type, count))
    table.sort(key=(lambda values: (- values[1])))
    for (type, count) in table:
        print(f'{type:4d} {count:9d} {mapper.lookup(type)}')
if (__name__ == '__main__'):
    main()
