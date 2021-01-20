
'\nA demonstration of classes and their special methods in Python.\n'

class Vec():
    'A simple vector class.\n\n    Instances of the Vec class can be constructed from numbers\n\n    >>> a = Vec(1, 2, 3)\n    >>> b = Vec(3, 2, 1)\n\n    added\n    >>> a + b\n    Vec(4, 4, 4)\n\n    subtracted\n    >>> a - b\n    Vec(-2, 0, 2)\n\n    and multiplied by a scalar on the left\n    >>> 3.0 * a\n    Vec(3.0, 6.0, 9.0)\n\n    or on the right\n    >>> a * 3.0\n    Vec(3.0, 6.0, 9.0)\n    '

    def __init__(self, *v):
        self.v = list(v)

    @classmethod
    def fromlist(cls, v):
        if (not isinstance(v, list)):
            raise TypeError
        inst = cls()
        inst.v = v
        return inst

    def __repr__(self):
        args = ', '.join((repr(x) for x in self.v))
        return 'Vec({})'.format(args)

    def __len__(self):
        return len(self.v)

    def __getitem__(self, i):
        return self.v[i]

    def __add__(self, other):
        v = [(x + y) for (x, y) in zip(self.v, other.v)]
        return Vec.fromlist(v)

    def __sub__(self, other):
        v = [(x - y) for (x, y) in zip(self.v, other.v)]
        return Vec.fromlist(v)

    def __mul__(self, scalar):
        v = [(x * scalar) for x in self.v]
        return Vec.fromlist(v)
    __rmul__ = __mul__

def test():
    import doctest
    doctest.testmod()
test()
