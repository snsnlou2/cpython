
from collections import deque
import unittest
from test.support import NEVER_EQ

class base_set():

    def __init__(self, el):
        self.el = el

class myset(base_set):

    def __contains__(self, el):
        return (self.el == el)

class seq(base_set):

    def __getitem__(self, n):
        return [self.el][n]

class TestContains(unittest.TestCase):

    def test_common_tests(self):
        a = base_set(1)
        b = myset(1)
        c = seq(1)
        self.assertIn(1, b)
        self.assertNotIn(0, b)
        self.assertIn(1, c)
        self.assertNotIn(0, c)
        self.assertRaises(TypeError, (lambda : (1 in a)))
        self.assertRaises(TypeError, (lambda : (1 not in a)))
        self.assertIn('c', 'abc')
        self.assertNotIn('d', 'abc')
        self.assertIn('', '')
        self.assertIn('', 'abc')
        self.assertRaises(TypeError, (lambda : (None in 'abc')))

    def test_builtin_sequence_types(self):
        a = range(10)
        for i in a:
            self.assertIn(i, a)
        self.assertNotIn(16, a)
        self.assertNotIn(a, a)
        a = tuple(a)
        for i in a:
            self.assertIn(i, a)
        self.assertNotIn(16, a)
        self.assertNotIn(a, a)

        class Deviant1():
            'Behaves strangely when compared\n\n            This class is designed to make sure that the contains code\n            works when the list is modified during the check.\n            '
            aList = list(range(15))

            def __eq__(self, other):
                if (other == 12):
                    self.aList.remove(12)
                    self.aList.remove(13)
                    self.aList.remove(14)
                return 0
        self.assertNotIn(Deviant1(), Deviant1.aList)

    def test_nonreflexive(self):
        values = (float('nan'), 1, None, 'abc', NEVER_EQ)
        constructors = (list, tuple, dict.fromkeys, set, frozenset, deque)
        for constructor in constructors:
            container = constructor(values)
            for elem in container:
                self.assertIn(elem, container)
            self.assertTrue((container == constructor(values)))
            self.assertTrue((container == container))

    def test_block_fallback(self):

        class ByContains(object):

            def __contains__(self, other):
                return False
        c = ByContains()

        class BlockContains(ByContains):
            "Is not a container\n\n            This class is a perfectly good iterable (as tested by\n            list(bc)), as well as inheriting from a perfectly good\n            container, but __contains__ = None prevents the usual\n            fallback to iteration in the container protocol. That\n            is, normally, 0 in bc would fall back to the equivalent\n            of any(x==0 for x in bc), but here it's blocked from\n            doing so.\n            "

            def __iter__(self):
                while False:
                    (yield None)
            __contains__ = None
        bc = BlockContains()
        self.assertFalse((0 in c))
        self.assertFalse((0 in list(bc)))
        self.assertRaises(TypeError, (lambda : (0 in bc)))
if (__name__ == '__main__'):
    unittest.main()
