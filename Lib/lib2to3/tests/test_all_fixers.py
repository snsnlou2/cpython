
'Tests that run all fixer modules over an input stream.\n\nThis has been broken out into its own test module because of its\nrunning time.\n'
import unittest
import test.support
from . import support

@test.support.requires_resource('cpu')
class Test_all(support.TestCase):

    def setUp(self):
        self.refactor = support.get_refactorer()

    def test_all_project_files(self):
        for filepath in support.all_project_files():
            self.refactor.refactor_file(filepath)
if (__name__ == '__main__'):
    unittest.main()
