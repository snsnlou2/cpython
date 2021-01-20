
"Tests for distutils.\n\nThe tests for distutils are defined in the distutils.tests package;\nthe test_suite() function there returns a test suite that's ready to\nbe run.\n"
import distutils.tests
import test.support

def test_main():
    test.support.run_unittest(distutils.tests.test_suite())
    test.support.reap_children()

def load_tests(*_):
    return distutils.tests.test_suite()
if (__name__ == '__main__'):
    test_main()
