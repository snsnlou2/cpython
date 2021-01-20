
import unittest
from importlib import resources
from . import data01
from . import util

class CommonTests(util.CommonResourceTests, unittest.TestCase):

    def execute(self, package, path):
        with resources.path(package, path):
            pass

class PathTests():

    def test_reading(self):
        with resources.path(self.data, 'utf-8.file') as path:
            self.assertTrue(path.name.endswith('utf-8.file'), repr(path))
            with path.open('r', encoding='utf-8') as file:
                text = file.read()
            self.assertEqual('Hello, UTF-8 world!\n', text)

class PathDiskTests(PathTests, unittest.TestCase):
    data = data01

    def test_natural_path(self):
        '\n        Guarantee the internal implementation detail that\n        file-system-backed resources do not get the tempdir\n        treatment.\n        '
        with resources.path(self.data, 'utf-8.file') as path:
            assert ('data' in str(path))

class PathZipTests(PathTests, util.ZipSetup, unittest.TestCase):

    def test_remove_in_context_manager(self):
        with resources.path(self.data, 'utf-8.file') as path:
            path.unlink()
if (__name__ == '__main__'):
    unittest.main()
