
import unittest
import os
import socket
import sys
from test.support import socket_helper
from test.support.import_helper import import_fresh_module
from test.support.os_helper import TESTFN
c_stat = import_fresh_module('stat', fresh=['_stat'])
py_stat = import_fresh_module('stat', blocked=['_stat'])

class TestFilemode():
    statmod = None
    file_flags = {'SF_APPEND', 'SF_ARCHIVED', 'SF_IMMUTABLE', 'SF_NOUNLINK', 'SF_SNAPSHOT', 'UF_APPEND', 'UF_COMPRESSED', 'UF_HIDDEN', 'UF_IMMUTABLE', 'UF_NODUMP', 'UF_NOUNLINK', 'UF_OPAQUE'}
    formats = {'S_IFBLK', 'S_IFCHR', 'S_IFDIR', 'S_IFIFO', 'S_IFLNK', 'S_IFREG', 'S_IFSOCK', 'S_IFDOOR', 'S_IFPORT', 'S_IFWHT'}
    format_funcs = {'S_ISBLK', 'S_ISCHR', 'S_ISDIR', 'S_ISFIFO', 'S_ISLNK', 'S_ISREG', 'S_ISSOCK', 'S_ISDOOR', 'S_ISPORT', 'S_ISWHT'}
    stat_struct = {'ST_MODE': 0, 'ST_INO': 1, 'ST_DEV': 2, 'ST_NLINK': 3, 'ST_UID': 4, 'ST_GID': 5, 'ST_SIZE': 6, 'ST_ATIME': 7, 'ST_MTIME': 8, 'ST_CTIME': 9}
    permission_bits = {'S_ISUID': 2048, 'S_ISGID': 1024, 'S_ENFMT': 1024, 'S_ISVTX': 512, 'S_IRWXU': 448, 'S_IRUSR': 256, 'S_IREAD': 256, 'S_IWUSR': 128, 'S_IWRITE': 128, 'S_IXUSR': 64, 'S_IEXEC': 64, 'S_IRWXG': 56, 'S_IRGRP': 32, 'S_IWGRP': 16, 'S_IXGRP': 8, 'S_IRWXO': 7, 'S_IROTH': 4, 'S_IWOTH': 2, 'S_IXOTH': 1}
    file_attributes = {'FILE_ATTRIBUTE_ARCHIVE': 32, 'FILE_ATTRIBUTE_COMPRESSED': 2048, 'FILE_ATTRIBUTE_DEVICE': 64, 'FILE_ATTRIBUTE_DIRECTORY': 16, 'FILE_ATTRIBUTE_ENCRYPTED': 16384, 'FILE_ATTRIBUTE_HIDDEN': 2, 'FILE_ATTRIBUTE_INTEGRITY_STREAM': 32768, 'FILE_ATTRIBUTE_NORMAL': 128, 'FILE_ATTRIBUTE_NOT_CONTENT_INDEXED': 8192, 'FILE_ATTRIBUTE_NO_SCRUB_DATA': 131072, 'FILE_ATTRIBUTE_OFFLINE': 4096, 'FILE_ATTRIBUTE_READONLY': 1, 'FILE_ATTRIBUTE_REPARSE_POINT': 1024, 'FILE_ATTRIBUTE_SPARSE_FILE': 512, 'FILE_ATTRIBUTE_SYSTEM': 4, 'FILE_ATTRIBUTE_TEMPORARY': 256, 'FILE_ATTRIBUTE_VIRTUAL': 65536}

    def setUp(self):
        try:
            os.remove(TESTFN)
        except OSError:
            try:
                os.rmdir(TESTFN)
            except OSError:
                pass
    tearDown = setUp

    def get_mode(self, fname=TESTFN, lstat=True):
        if lstat:
            st_mode = os.lstat(fname).st_mode
        else:
            st_mode = os.stat(fname).st_mode
        modestr = self.statmod.filemode(st_mode)
        return (st_mode, modestr)

    def assertS_IS(self, name, mode):
        fmt = getattr(self.statmod, ('S_IF' + name.lstrip('F')))
        self.assertEqual(self.statmod.S_IFMT(mode), fmt)
        testname = ('S_IS' + name)
        for funcname in self.format_funcs:
            func = getattr(self.statmod, funcname, None)
            if (func is None):
                if (funcname == testname):
                    raise ValueError(funcname)
                continue
            if (funcname == testname):
                self.assertTrue(func(mode))
            else:
                self.assertFalse(func(mode))

    def test_mode(self):
        with open(TESTFN, 'w'):
            pass
        if (os.name == 'posix'):
            os.chmod(TESTFN, 448)
            (st_mode, modestr) = self.get_mode()
            self.assertEqual(modestr, '-rwx------')
            self.assertS_IS('REG', st_mode)
            self.assertEqual(self.statmod.S_IMODE(st_mode), self.statmod.S_IRWXU)
            os.chmod(TESTFN, 56)
            (st_mode, modestr) = self.get_mode()
            self.assertEqual(modestr, '----rwx---')
            self.assertS_IS('REG', st_mode)
            self.assertEqual(self.statmod.S_IMODE(st_mode), self.statmod.S_IRWXG)
            os.chmod(TESTFN, 7)
            (st_mode, modestr) = self.get_mode()
            self.assertEqual(modestr, '-------rwx')
            self.assertS_IS('REG', st_mode)
            self.assertEqual(self.statmod.S_IMODE(st_mode), self.statmod.S_IRWXO)
            os.chmod(TESTFN, 292)
            (st_mode, modestr) = self.get_mode()
            self.assertS_IS('REG', st_mode)
            self.assertEqual(modestr, '-r--r--r--')
            self.assertEqual(self.statmod.S_IMODE(st_mode), 292)
        else:
            os.chmod(TESTFN, 448)
            (st_mode, modestr) = self.get_mode()
            self.assertEqual(modestr[:3], '-rw')
            self.assertS_IS('REG', st_mode)
            self.assertEqual(self.statmod.S_IFMT(st_mode), self.statmod.S_IFREG)

    def test_directory(self):
        os.mkdir(TESTFN)
        os.chmod(TESTFN, 448)
        (st_mode, modestr) = self.get_mode()
        self.assertS_IS('DIR', st_mode)
        if (os.name == 'posix'):
            self.assertEqual(modestr, 'drwx------')
        else:
            self.assertEqual(modestr[0], 'd')

    @unittest.skipUnless(hasattr(os, 'symlink'), 'os.symlink not available')
    def test_link(self):
        try:
            os.symlink(os.getcwd(), TESTFN)
        except (OSError, NotImplementedError) as err:
            raise unittest.SkipTest(str(err))
        else:
            (st_mode, modestr) = self.get_mode()
            self.assertEqual(modestr[0], 'l')
            self.assertS_IS('LNK', st_mode)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'os.mkfifo not available')
    def test_fifo(self):
        try:
            os.mkfifo(TESTFN, 448)
        except PermissionError as e:
            self.skipTest(('os.mkfifo(): %s' % e))
        (st_mode, modestr) = self.get_mode()
        self.assertEqual(modestr, 'prwx------')
        self.assertS_IS('FIFO', st_mode)

    @unittest.skipUnless((os.name == 'posix'), 'requires Posix')
    def test_devices(self):
        if os.path.exists(os.devnull):
            (st_mode, modestr) = self.get_mode(os.devnull, lstat=False)
            self.assertEqual(modestr[0], 'c')
            self.assertS_IS('CHR', st_mode)
        for blockdev in ('/dev/sda', '/dev/hda'):
            if os.path.exists(blockdev):
                (st_mode, modestr) = self.get_mode(blockdev, lstat=False)
                self.assertEqual(modestr[0], 'b')
                self.assertS_IS('BLK', st_mode)
                break

    @socket_helper.skip_unless_bind_unix_socket
    def test_socket(self):
        with socket.socket(socket.AF_UNIX) as s:
            s.bind(TESTFN)
            (st_mode, modestr) = self.get_mode()
            self.assertEqual(modestr[0], 's')
            self.assertS_IS('SOCK', st_mode)

    def test_module_attributes(self):
        for (key, value) in self.stat_struct.items():
            modvalue = getattr(self.statmod, key)
            self.assertEqual(value, modvalue, key)
        for (key, value) in self.permission_bits.items():
            modvalue = getattr(self.statmod, key)
            self.assertEqual(value, modvalue, key)
        for key in self.file_flags:
            modvalue = getattr(self.statmod, key)
            self.assertIsInstance(modvalue, int)
        for key in self.formats:
            modvalue = getattr(self.statmod, key)
            self.assertIsInstance(modvalue, int)
        for key in self.format_funcs:
            func = getattr(self.statmod, key)
            self.assertTrue(callable(func))
            self.assertEqual(func(0), 0)

    @unittest.skipUnless((sys.platform == 'win32'), 'FILE_ATTRIBUTE_* constants are Win32 specific')
    def test_file_attribute_constants(self):
        for (key, value) in sorted(self.file_attributes.items()):
            self.assertTrue(hasattr(self.statmod, key), key)
            modvalue = getattr(self.statmod, key)
            self.assertEqual(value, modvalue, key)

class TestFilemodeCStat(TestFilemode, unittest.TestCase):
    statmod = c_stat

class TestFilemodePyStat(TestFilemode, unittest.TestCase):
    statmod = py_stat
if (__name__ == '__main__'):
    unittest.main()
