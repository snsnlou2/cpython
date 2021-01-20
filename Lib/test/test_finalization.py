
'\nTests for object finalization semantics, as outlined in PEP 442.\n'
import contextlib
import gc
import unittest
import weakref
try:
    from _testcapi import with_tp_del
except ImportError:

    def with_tp_del(cls):

        class C(object):

            def __new__(cls, *args, **kwargs):
                raise TypeError('requires _testcapi.with_tp_del')
        return C
from test import support

class NonGCSimpleBase():
    '\n    The base class for all the objects under test, equipped with various\n    testing features.\n    '
    survivors = []
    del_calls = []
    tp_del_calls = []
    errors = []
    _cleaning = False
    __slots__ = ()

    @classmethod
    def _cleanup(cls):
        cls.survivors.clear()
        cls.errors.clear()
        gc.garbage.clear()
        gc.collect()
        cls.del_calls.clear()
        cls.tp_del_calls.clear()

    @classmethod
    @contextlib.contextmanager
    def test(cls):
        '\n        A context manager to use around all finalization tests.\n        '
        with support.disable_gc():
            cls.del_calls.clear()
            cls.tp_del_calls.clear()
            NonGCSimpleBase._cleaning = False
            try:
                (yield)
                if cls.errors:
                    raise cls.errors[0]
            finally:
                NonGCSimpleBase._cleaning = True
                cls._cleanup()

    def check_sanity(self):
        '\n        Check the object is sane (non-broken).\n        '

    def __del__(self):
        '\n        PEP 442 finalizer.  Record that this was called, check the\n        object is in a sane state, and invoke a side effect.\n        '
        try:
            if (not self._cleaning):
                self.del_calls.append(id(self))
                self.check_sanity()
                self.side_effect()
        except Exception as e:
            self.errors.append(e)

    def side_effect(self):
        '\n        A side effect called on destruction.\n        '

class SimpleBase(NonGCSimpleBase):

    def __init__(self):
        self.id_ = id(self)

    def check_sanity(self):
        assert (self.id_ == id(self))

class NonGC(NonGCSimpleBase):
    __slots__ = ()

class NonGCResurrector(NonGCSimpleBase):
    __slots__ = ()

    def side_effect(self):
        '\n        Resurrect self by storing self in a class-wide list.\n        '
        self.survivors.append(self)

class Simple(SimpleBase):
    pass

class SimpleResurrector(NonGCResurrector, SimpleBase):
    pass

class TestBase():

    def setUp(self):
        self.old_garbage = gc.garbage[:]
        gc.garbage[:] = []

    def tearDown(self):
        try:
            self.assertEqual(gc.garbage, [])
        finally:
            del self.old_garbage
            gc.collect()

    def assert_del_calls(self, ids):
        self.assertEqual(sorted(SimpleBase.del_calls), sorted(ids))

    def assert_tp_del_calls(self, ids):
        self.assertEqual(sorted(SimpleBase.tp_del_calls), sorted(ids))

    def assert_survivors(self, ids):
        self.assertEqual(sorted((id(x) for x in SimpleBase.survivors)), sorted(ids))

    def assert_garbage(self, ids):
        self.assertEqual(sorted((id(x) for x in gc.garbage)), sorted(ids))

    def clear_survivors(self):
        SimpleBase.survivors.clear()

class SimpleFinalizationTest(TestBase, unittest.TestCase):
    '\n    Test finalization without refcycles.\n    '

    def test_simple(self):
        with SimpleBase.test():
            s = Simple()
            ids = [id(s)]
            wr = weakref.ref(s)
            del s
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_survivors([])
            self.assertIs(wr(), None)
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_survivors([])

    def test_simple_resurrect(self):
        with SimpleBase.test():
            s = SimpleResurrector()
            ids = [id(s)]
            wr = weakref.ref(s)
            del s
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_survivors(ids)
            self.assertIsNot(wr(), None)
            self.clear_survivors()
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_survivors([])
        self.assertIs(wr(), None)

    def test_non_gc(self):
        with SimpleBase.test():
            s = NonGC()
            self.assertFalse(gc.is_tracked(s))
            ids = [id(s)]
            del s
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_survivors([])
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_survivors([])

    def test_non_gc_resurrect(self):
        with SimpleBase.test():
            s = NonGCResurrector()
            self.assertFalse(gc.is_tracked(s))
            ids = [id(s)]
            del s
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_survivors(ids)
            self.clear_survivors()
            gc.collect()
            self.assert_del_calls((ids * 2))
            self.assert_survivors(ids)

class SelfCycleBase():

    def __init__(self):
        super().__init__()
        self.ref = self

    def check_sanity(self):
        super().check_sanity()
        assert (self.ref is self)

class SimpleSelfCycle(SelfCycleBase, Simple):
    pass

class SelfCycleResurrector(SelfCycleBase, SimpleResurrector):
    pass

class SuicidalSelfCycle(SelfCycleBase, Simple):

    def side_effect(self):
        '\n        Explicitly break the reference cycle.\n        '
        self.ref = None

class SelfCycleFinalizationTest(TestBase, unittest.TestCase):
    '\n    Test finalization of an object having a single cyclic reference to\n    itself.\n    '

    def test_simple(self):
        with SimpleBase.test():
            s = SimpleSelfCycle()
            ids = [id(s)]
            wr = weakref.ref(s)
            del s
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_survivors([])
            self.assertIs(wr(), None)
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_survivors([])

    def test_simple_resurrect(self):
        with SimpleBase.test():
            s = SelfCycleResurrector()
            ids = [id(s)]
            wr = weakref.ref(s)
            del s
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_survivors(ids)
            self.assertIs(wr(), None)
            self.clear_survivors()
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_survivors([])
            self.assertIs(wr(), None)

    def test_simple_suicide(self):
        with SimpleBase.test():
            s = SuicidalSelfCycle()
            ids = [id(s)]
            wr = weakref.ref(s)
            del s
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_survivors([])
            self.assertIs(wr(), None)
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_survivors([])
            self.assertIs(wr(), None)

class ChainedBase():

    def chain(self, left):
        self.suicided = False
        self.left = left
        left.right = self

    def check_sanity(self):
        super().check_sanity()
        if self.suicided:
            assert (self.left is None)
            assert (self.right is None)
        else:
            left = self.left
            if left.suicided:
                assert (left.right is None)
            else:
                assert (left.right is self)
            right = self.right
            if right.suicided:
                assert (right.left is None)
            else:
                assert (right.left is self)

class SimpleChained(ChainedBase, Simple):
    pass

class ChainedResurrector(ChainedBase, SimpleResurrector):
    pass

class SuicidalChained(ChainedBase, Simple):

    def side_effect(self):
        '\n        Explicitly break the reference cycle.\n        '
        self.suicided = True
        self.left = None
        self.right = None

class CycleChainFinalizationTest(TestBase, unittest.TestCase):
    "\n    Test finalization of a cyclic chain.  These tests are similar in\n    spirit to the self-cycle tests above, but the collectable object\n    graph isn't trivial anymore.\n    "

    def build_chain(self, classes):
        nodes = [cls() for cls in classes]
        for i in range(len(nodes)):
            nodes[i].chain(nodes[(i - 1)])
        return nodes

    def check_non_resurrecting_chain(self, classes):
        N = len(classes)
        with SimpleBase.test():
            nodes = self.build_chain(classes)
            ids = [id(s) for s in nodes]
            wrs = [weakref.ref(s) for s in nodes]
            del nodes
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_survivors([])
            self.assertEqual([wr() for wr in wrs], ([None] * N))
            gc.collect()
            self.assert_del_calls(ids)

    def check_resurrecting_chain(self, classes):
        N = len(classes)
        with SimpleBase.test():
            nodes = self.build_chain(classes)
            N = len(nodes)
            ids = [id(s) for s in nodes]
            survivor_ids = [id(s) for s in nodes if isinstance(s, SimpleResurrector)]
            wrs = [weakref.ref(s) for s in nodes]
            del nodes
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_survivors(survivor_ids)
            self.assertEqual([wr() for wr in wrs], ([None] * N))
            self.clear_survivors()
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_survivors([])

    def test_homogenous(self):
        self.check_non_resurrecting_chain(([SimpleChained] * 3))

    def test_homogenous_resurrect(self):
        self.check_resurrecting_chain(([ChainedResurrector] * 3))

    def test_homogenous_suicidal(self):
        self.check_non_resurrecting_chain(([SuicidalChained] * 3))

    def test_heterogenous_suicidal_one(self):
        self.check_non_resurrecting_chain(([SuicidalChained, SimpleChained] * 2))

    def test_heterogenous_suicidal_two(self):
        self.check_non_resurrecting_chain((([SuicidalChained] * 2) + ([SimpleChained] * 2)))

    def test_heterogenous_resurrect_one(self):
        self.check_resurrecting_chain(([ChainedResurrector, SimpleChained] * 2))

    def test_heterogenous_resurrect_two(self):
        self.check_resurrecting_chain(([ChainedResurrector, SimpleChained, SuicidalChained] * 2))

    def test_heterogenous_resurrect_three(self):
        self.check_resurrecting_chain(((([ChainedResurrector] * 2) + ([SimpleChained] * 2)) + ([SuicidalChained] * 2)))

class LegacyBase(SimpleBase):

    def __del__(self):
        try:
            if (not self._cleaning):
                self.del_calls.append(id(self))
                self.check_sanity()
        except Exception as e:
            self.errors.append(e)

    def __tp_del__(self):
        '\n        Legacy (pre-PEP 442) finalizer, mapped to a tp_del slot.\n        '
        try:
            if (not self._cleaning):
                self.tp_del_calls.append(id(self))
                self.check_sanity()
                self.side_effect()
        except Exception as e:
            self.errors.append(e)

@with_tp_del
class Legacy(LegacyBase):
    pass

@with_tp_del
class LegacyResurrector(LegacyBase):

    def side_effect(self):
        '\n        Resurrect self by storing self in a class-wide list.\n        '
        self.survivors.append(self)

@with_tp_del
class LegacySelfCycle(SelfCycleBase, LegacyBase):
    pass

@support.cpython_only
class LegacyFinalizationTest(TestBase, unittest.TestCase):
    '\n    Test finalization of objects with a tp_del.\n    '

    def tearDown(self):
        gc.garbage.clear()
        gc.collect()
        super().tearDown()

    def test_legacy(self):
        with SimpleBase.test():
            s = Legacy()
            ids = [id(s)]
            wr = weakref.ref(s)
            del s
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_tp_del_calls(ids)
            self.assert_survivors([])
            self.assertIs(wr(), None)
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_tp_del_calls(ids)

    def test_legacy_resurrect(self):
        with SimpleBase.test():
            s = LegacyResurrector()
            ids = [id(s)]
            wr = weakref.ref(s)
            del s
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_tp_del_calls(ids)
            self.assert_survivors(ids)
            self.assertIs(wr(), None)
            self.clear_survivors()
            gc.collect()
            self.assert_del_calls(ids)
            self.assert_tp_del_calls((ids * 2))
            self.assert_survivors(ids)
        self.assertIs(wr(), None)

    def test_legacy_self_cycle(self):
        with SimpleBase.test():
            s = LegacySelfCycle()
            ids = [id(s)]
            wr = weakref.ref(s)
            del s
            gc.collect()
            self.assert_del_calls([])
            self.assert_tp_del_calls([])
            self.assert_survivors([])
            self.assert_garbage(ids)
            self.assertIsNot(wr(), None)
            gc.garbage[0].ref = None
        self.assert_garbage([])
        self.assertIs(wr(), None)
if (__name__ == '__main__'):
    unittest.main()
