
import unittest
from .. import tool_imports_for_tests
with tool_imports_for_tests():
    pass

class SelfCheckTests(unittest.TestCase):

    @unittest.expectedFailure
    def test_known(self):
        raise NotImplementedError

    @unittest.expectedFailure
    def test_compare_nm_results(self):
        raise NotImplementedError

class DummySourceTests(unittest.TestCase):

    @unittest.expectedFailure
    def test_check(self):
        raise NotImplementedError

    @unittest.expectedFailure
    def test_show(self):
        raise NotImplementedError
