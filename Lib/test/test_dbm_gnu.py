
from test import support
from test.support import import_helper
gdbm = import_helper.import_module('dbm.gnu')
import unittest
import os
from test.support.os_helper import TESTFN, TESTFN_NONASCII, unlink
filename = TESTFN

class TestGdbm(unittest.TestCase):

    @staticmethod
    def setUpClass():
        if support.verbose:
            try:
                from _gdbm import _GDBM_VERSION as version
            except ImportError:
                pass
            else:
                print(f'gdbm version: {version}')

    def setUp(self):
        self.g = None

    def tearDown(self):
        if (self.g is not None):
            self.g.close()
        unlink(filename)

    def test_key_methods(self):
        self.g = gdbm.open(filename, 'c')
        self.assertEqual(self.g.keys(), [])
        self.g['a'] = 'b'
        self.g['12345678910'] = '019237410982340912840198242'
        self.g[b'bytes'] = b'data'
        key_set = set(self.g.keys())
        self.assertEqual(key_set, set([b'a', b'bytes', b'12345678910']))
        self.assertIn('a', self.g)
        self.assertIn(b'a', self.g)
        self.assertEqual(self.g[b'bytes'], b'data')
        key = self.g.firstkey()
        while key:
            self.assertIn(key, key_set)
            key_set.remove(key)
            key = self.g.nextkey(key)
        self.assertEqual(self.g.get(b'a'), b'b')
        self.assertIsNone(self.g.get(b'xxx'))
        self.assertEqual(self.g.get(b'xxx', b'foo'), b'foo')
        with self.assertRaises(KeyError):
            self.g['xxx']
        self.assertEqual(self.g.setdefault(b'xxx', b'foo'), b'foo')
        self.assertEqual(self.g[b'xxx'], b'foo')

    def test_error_conditions(self):
        unlink(filename)
        self.assertRaises(gdbm.error, gdbm.open, filename, 'r')
        self.g = gdbm.open(filename, 'c')
        self.g.close()
        self.assertRaises(gdbm.error, (lambda : self.g['a']))
        self.assertRaises(gdbm.error, (lambda : gdbm.open(filename, 'rx').close()))

    def test_flags(self):
        all = set(gdbm.open_flags)
        modes = (all - set('fsu'))
        for mode in sorted(modes):
            self.g = gdbm.open(filename, mode)
            self.g.close()
        flags = (all - set('crwn'))
        for mode in modes:
            for flag in flags:
                self.g = gdbm.open(filename, (mode + flag))
                self.g.close()

    def test_reorganize(self):
        self.g = gdbm.open(filename, 'c')
        size0 = os.path.getsize(filename)
        value_size = max(size0, 10000)
        self.g['x'] = ('x' * value_size)
        size1 = os.path.getsize(filename)
        self.assertGreater(size1, size0)
        del self.g['x']
        self.assertEqual(os.path.getsize(filename), size1)
        self.g.reorganize()
        size2 = os.path.getsize(filename)
        self.assertLess(size2, size1)
        self.assertGreaterEqual(size2, size0)

    def test_context_manager(self):
        with gdbm.open(filename, 'c') as db:
            db['gdbm context manager'] = 'context manager'
        with gdbm.open(filename, 'r') as db:
            self.assertEqual(list(db.keys()), [b'gdbm context manager'])
        with self.assertRaises(gdbm.error) as cm:
            db.keys()
        self.assertEqual(str(cm.exception), 'GDBM object has already been closed')

    def test_bytes(self):
        with gdbm.open(filename, 'c') as db:
            db[b'bytes key \xbd'] = b'bytes value \xbd'
        with gdbm.open(filename, 'r') as db:
            self.assertEqual(list(db.keys()), [b'bytes key \xbd'])
            self.assertTrue((b'bytes key \xbd' in db))
            self.assertEqual(db[b'bytes key \xbd'], b'bytes value \xbd')

    def test_unicode(self):
        with gdbm.open(filename, 'c') as db:
            db['Unicode key 🐍'] = 'Unicode value 🐍'
        with gdbm.open(filename, 'r') as db:
            self.assertEqual(list(db.keys()), ['Unicode key 🐍'.encode()])
            self.assertTrue(('Unicode key 🐍'.encode() in db))
            self.assertTrue(('Unicode key 🐍' in db))
            self.assertEqual(db['Unicode key 🐍'.encode()], 'Unicode value 🐍'.encode())
            self.assertEqual(db['Unicode key 🐍'], 'Unicode value 🐍'.encode())

    def test_write_readonly_file(self):
        with gdbm.open(filename, 'c') as db:
            db[b'bytes key'] = b'bytes value'
        with gdbm.open(filename, 'r') as db:
            with self.assertRaises(gdbm.error):
                del db[b'not exist key']
            with self.assertRaises(gdbm.error):
                del db[b'bytes key']
            with self.assertRaises(gdbm.error):
                db[b'not exist key'] = b'not exist value'

    @unittest.skipUnless(TESTFN_NONASCII, 'requires OS support of non-ASCII encodings')
    def test_nonascii_filename(self):
        filename = TESTFN_NONASCII
        self.addCleanup(unlink, filename)
        with gdbm.open(filename, 'c') as db:
            db[b'key'] = b'value'
        self.assertTrue(os.path.exists(filename))
        with gdbm.open(filename, 'r') as db:
            self.assertEqual(list(db.keys()), [b'key'])
            self.assertTrue((b'key' in db))
            self.assertEqual(db[b'key'], b'value')

    def test_nonexisting_file(self):
        nonexisting_file = 'nonexisting-file'
        with self.assertRaises(gdbm.error) as cm:
            gdbm.open(nonexisting_file)
        self.assertIn(nonexisting_file, str(cm.exception))
        self.assertEqual(cm.exception.filename, nonexisting_file)
if (__name__ == '__main__'):
    unittest.main()
