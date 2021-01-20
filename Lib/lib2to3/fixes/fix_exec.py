
'Fixer for exec.\n\nThis converts usages of the exec statement into calls to a built-in\nexec() function.\n\nexec code in ns1, ns2 -> exec(code, ns1, ns2)\n'
from .. import fixer_base
from ..fixer_util import Comma, Name, Call

class FixExec(fixer_base.BaseFix):
    BM_compatible = True
    PATTERN = "\n    exec_stmt< 'exec' a=any 'in' b=any [',' c=any] >\n    |\n    exec_stmt< 'exec' (not atom<'(' [any] ')'>) a=any >\n    "

    def transform(self, node, results):
        assert results
        syms = self.syms
        a = results['a']
        b = results.get('b')
        c = results.get('c')
        args = [a.clone()]
        args[0].prefix = ''
        if (b is not None):
            args.extend([Comma(), b.clone()])
        if (c is not None):
            args.extend([Comma(), c.clone()])
        return Call(Name('exec'), args, prefix=node.prefix)
