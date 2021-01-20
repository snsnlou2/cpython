
"Fixer that changes 'a ,b' into 'a, b'.\n\nThis also changes '{a :b}' into '{a: b}', but does not touch other\nuses of colons.  It does not touch other uses of whitespace.\n\n"
from .. import pytree
from ..pgen2 import token
from .. import fixer_base

class FixWsComma(fixer_base.BaseFix):
    explicit = True
    PATTERN = "\n    any<(not(',') any)+ ',' ((not(',') any)+ ',')* [not(',') any]>\n    "
    COMMA = pytree.Leaf(token.COMMA, ',')
    COLON = pytree.Leaf(token.COLON, ':')
    SEPS = (COMMA, COLON)

    def transform(self, node, results):
        new = node.clone()
        comma = False
        for child in new.children:
            if (child in self.SEPS):
                prefix = child.prefix
                if (prefix.isspace() and ('\n' not in prefix)):
                    child.prefix = ''
                comma = True
            else:
                if comma:
                    prefix = child.prefix
                    if (not prefix):
                        child.prefix = ' '
                comma = False
        return new
