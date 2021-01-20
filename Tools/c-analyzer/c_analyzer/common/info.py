
from collections import namedtuple
import re
from .util import classonly, _NTBase
UNKNOWN = '???'
NAME_RE = re.compile('^([a-zA-Z]|_\\w*[a-zA-Z]\\w*|[a-zA-Z]\\w*)$')

class ID(_NTBase, namedtuple('ID', 'filename funcname name')):
    'A unique ID for a single symbol or declaration.'
    __slots__ = ()

    @classonly
    def from_raw(cls, raw):
        if (not raw):
            return None
        if isinstance(raw, str):
            return cls(None, None, raw)
        try:
            (name,) = raw
            filename = None
        except ValueError:
            try:
                (filename, name) = raw
            except ValueError:
                return super().from_raw(raw)
        return cls(filename, None, name)

    def __new__(cls, filename, funcname, name):
        self = super().__new__(cls, filename=(str(filename) if filename else None), funcname=(str(funcname) if funcname else None), name=(str(name) if name else None))
        return self

    def validate(self):
        'Fail if the object is invalid (i.e. init with bad data).'
        if (not self.name):
            raise TypeError('missing name')
        elif (not NAME_RE.match(self.name)):
            raise ValueError(f'name must be an identifier, got {self.name!r}')
        if self.funcname:
            if (not self.filename):
                raise TypeError('missing filename')
            if ((not NAME_RE.match(self.funcname)) and (self.funcname != UNKNOWN)):
                raise ValueError(f'name must be an identifier, got {self.funcname!r}')

    @property
    def islocal(self):
        return (self.funcname is not None)

    def match(self, other, *, match_files=(lambda f1, f2: (f1 == f2))):
        'Return True if the two match.\n\n        At least one of the two must be completely valid (no UNKNOWN\n        anywhere).  Otherwise False is returned.  The remaining one\n        *may* have UNKNOWN for both funcname and filename.  It must\n        have a valid name though.\n\n        The caller is responsible for knowing which of the two is valid\n        (and which to use if both are valid).\n        '
        if (self.name is None):
            return False
        if (other.name != self.name):
            return False
        if (self.filename is None):
            return False
        if (other.filename is None):
            return False
        if (self.filename == UNKNOWN):
            if (other.funcname == UNKNOWN):
                return False
            elif (self.funcname != UNKNOWN):
                raise NotImplementedError
            else:
                return True
        elif (other.filename == UNKNOWN):
            if (self.funcname == UNKNOWN):
                return False
            elif (other.funcname != UNKNOWN):
                raise NotImplementedError
            else:
                return True
        elif (not match_files(self.filename, other.filename)):
            return False
        if (self.funcname == UNKNOWN):
            if (other.funcname == UNKNOWN):
                return False
            else:
                return (other.funcname is not None)
        elif (other.funcname == UNKNOWN):
            if (self.funcname == UNKNOWN):
                return False
            else:
                return (self.funcname is not None)
        elif (self.funcname == other.funcname):
            return True
        return False
