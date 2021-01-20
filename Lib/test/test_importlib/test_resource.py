
import sys
import unittest
from . import data01
from . import zipdata01, zipdata02
from . import util
from importlib import resources, import_module

class ResourceTests():

    def test_is_resource_good_path(self):
        self.assertTrue(resources.is_resource(self.data, 'binary.file'))

    def test_is_resource_missing(self):
        self.assertFalse(resources.is_resource(self.data, 'not-a-file'))

    def test_is_resource_subresource_directory(self):
        self.assertFalse(resources.is_resource(self.data, 'subdirectory'))

    def test_contents(self):
        contents = set(resources.contents(self.data))
        contents.discard('__pycache__')
        contents.discard('__init__.pyc')
        contents.discard('__init__.pyo')
        self.assertEqual(contents, {'__init__.py', 'subdirectory', 'utf-8.file', 'binary.file', 'utf-16.file'})

class ResourceDiskTests(ResourceTests, unittest.TestCase):

    def setUp(self):
        self.data = data01

class ResourceZipTests(ResourceTests, util.ZipSetup, unittest.TestCase):
    pass

class ResourceLoaderTests(unittest.TestCase):

    def test_resource_contents(self):
        package = util.create_package(file=data01, path=data01.__file__, contents=['A', 'B', 'C'])
        self.assertEqual(set(resources.contents(package)), {'A', 'B', 'C'})

    def test_resource_is_resource(self):
        package = util.create_package(file=data01, path=data01.__file__, contents=['A', 'B', 'C', 'D/E', 'D/F'])
        self.assertTrue(resources.is_resource(package, 'B'))

    def test_resource_directory_is_not_resource(self):
        package = util.create_package(file=data01, path=data01.__file__, contents=['A', 'B', 'C', 'D/E', 'D/F'])
        self.assertFalse(resources.is_resource(package, 'D'))

    def test_resource_missing_is_not_resource(self):
        package = util.create_package(file=data01, path=data01.__file__, contents=['A', 'B', 'C', 'D/E', 'D/F'])
        self.assertFalse(resources.is_resource(package, 'Z'))

class ResourceCornerCaseTests(unittest.TestCase):

    def test_package_has_no_reader_fallback(self):
        module = util.create_package(file=data01, path=data01.__file__, contents=['A', 'B', 'C'])
        module.__loader__ = object()
        module.__file__ = '/path/which/shall/not/be/named'
        if (sys.version_info >= (3,)):
            module.__spec__.loader = module.__loader__
            module.__spec__.origin = module.__file__
        self.assertFalse(resources.is_resource(module, 'A'))

class ResourceFromZipsTest(util.ZipSetupBase, unittest.TestCase):
    ZIP_MODULE = zipdata02

    def test_unrelated_contents(self):
        self.assertEqual(set(resources.contents('ziptestdata.one')), {'__init__.py', 'resource1.txt'})
        self.assertEqual(set(resources.contents('ziptestdata.two')), {'__init__.py', 'resource2.txt'})

class SubdirectoryResourceFromZipsTest(util.ZipSetupBase, unittest.TestCase):
    ZIP_MODULE = zipdata01

    def test_is_submodule_resource(self):
        submodule = import_module('ziptestdata.subdirectory')
        self.assertTrue(resources.is_resource(submodule, 'binary.file'))

    def test_read_submodule_resource_by_name(self):
        self.assertTrue(resources.is_resource('ziptestdata.subdirectory', 'binary.file'))

    def test_submodule_contents(self):
        submodule = import_module('ziptestdata.subdirectory')
        self.assertEqual(set(resources.contents(submodule)), {'__init__.py', 'binary.file'})

    def test_submodule_contents_by_name(self):
        self.assertEqual(set(resources.contents('ziptestdata.subdirectory')), {'__init__.py', 'binary.file'})

class NamespaceTest(unittest.TestCase):

    def test_namespaces_cannot_have_resources(self):
        contents = resources.contents('test.test_importlib.data03.namespace')
        self.assertFalse(list(contents))
        self.assertFalse(resources.is_resource('test.test_importlib.data03.namespace', 'resource1.txt'))
        self.assertRaises(FileNotFoundError, resources.open_text, 'test.test_importlib.data03.namespace', 'resource1.txt')
        self.assertRaises(FileNotFoundError, resources.open_binary, 'test.test_importlib.data03.namespace', 'resource1.txt')
        self.assertRaises(FileNotFoundError, resources.read_text, 'test.test_importlib.data03.namespace', 'resource1.txt')
        self.assertRaises(FileNotFoundError, resources.read_binary, 'test.test_importlib.data03.namespace', 'resource1.txt')
if (__name__ == '__main__'):
    unittest.main()
