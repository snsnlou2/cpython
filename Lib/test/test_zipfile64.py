
from test import support
support.requires('extralargefile', 'test requires loads of disk-space bytes and a long time to run')
import zipfile, os, unittest
import time
import sys
from tempfile import TemporaryFile
from test.support import os_helper
from test.support import TESTFN, requires_zlib
TESTFN2 = (TESTFN + '2')
_PRINT_WORKING_MSG_INTERVAL = 60

class TestsWithSourceFile(unittest.TestCase):

    def setUp(self):
        line_gen = (('Test of zipfile line %d.' % i) for i in range(1000000))
        self.data = '\n'.join(line_gen).encode('ascii')
        with open(TESTFN, 'wb') as fp:
            fp.write(self.data)

    def zipTest(self, f, compression):
        with zipfile.ZipFile(f, 'w', compression) as zipfp:
            filecount = ((6 * (1024 ** 3)) // len(self.data))
            next_time = (time.monotonic() + _PRINT_WORKING_MSG_INTERVAL)
            for num in range(filecount):
                zipfp.writestr(('testfn%d' % num), self.data)
                if (next_time <= time.monotonic()):
                    next_time = (time.monotonic() + _PRINT_WORKING_MSG_INTERVAL)
                    print(('  zipTest still writing %d of %d, be patient...' % (num, filecount)), file=sys.__stdout__)
                    sys.__stdout__.flush()
        with zipfile.ZipFile(f, 'r', compression) as zipfp:
            for num in range(filecount):
                self.assertEqual(zipfp.read(('testfn%d' % num)), self.data)
                if (next_time <= time.monotonic()):
                    next_time = (time.monotonic() + _PRINT_WORKING_MSG_INTERVAL)
                    print(('  zipTest still reading %d of %d, be patient...' % (num, filecount)), file=sys.__stdout__)
                    sys.__stdout__.flush()

    def testStored(self):
        with TemporaryFile() as f:
            self.zipTest(f, zipfile.ZIP_STORED)
            self.assertFalse(f.closed)
        self.zipTest(TESTFN2, zipfile.ZIP_STORED)

    @requires_zlib()
    def testDeflated(self):
        with TemporaryFile() as f:
            self.zipTest(f, zipfile.ZIP_DEFLATED)
            self.assertFalse(f.closed)
        self.zipTest(TESTFN2, zipfile.ZIP_DEFLATED)

    def tearDown(self):
        for fname in (TESTFN, TESTFN2):
            if os.path.exists(fname):
                os.remove(fname)

class OtherTests(unittest.TestCase):

    def testMoreThan64kFiles(self):
        with zipfile.ZipFile(TESTFN, mode='w', allowZip64=True) as zipf:
            zipf.debug = 100
            numfiles = (((1 << 16) * 3) // 2)
            for i in range(numfiles):
                zipf.writestr(('foo%08d' % i), ('%d' % ((i ** 3) % 57)))
            self.assertEqual(len(zipf.namelist()), numfiles)
        with zipfile.ZipFile(TESTFN, mode='r') as zipf2:
            self.assertEqual(len(zipf2.namelist()), numfiles)
            for i in range(numfiles):
                content = zipf2.read(('foo%08d' % i)).decode('ascii')
                self.assertEqual(content, ('%d' % ((i ** 3) % 57)))

    def testMoreThan64kFilesAppend(self):
        with zipfile.ZipFile(TESTFN, mode='w', allowZip64=False) as zipf:
            zipf.debug = 100
            numfiles = ((1 << 16) - 1)
            for i in range(numfiles):
                zipf.writestr(('foo%08d' % i), ('%d' % ((i ** 3) % 57)))
            self.assertEqual(len(zipf.namelist()), numfiles)
            with self.assertRaises(zipfile.LargeZipFile):
                zipf.writestr(('foo%08d' % numfiles), b'')
            self.assertEqual(len(zipf.namelist()), numfiles)
        with zipfile.ZipFile(TESTFN, mode='a', allowZip64=False) as zipf:
            zipf.debug = 100
            self.assertEqual(len(zipf.namelist()), numfiles)
            with self.assertRaises(zipfile.LargeZipFile):
                zipf.writestr(('foo%08d' % numfiles), b'')
            self.assertEqual(len(zipf.namelist()), numfiles)
        with zipfile.ZipFile(TESTFN, mode='a', allowZip64=True) as zipf:
            zipf.debug = 100
            self.assertEqual(len(zipf.namelist()), numfiles)
            numfiles2 = (((1 << 16) * 3) // 2)
            for i in range(numfiles, numfiles2):
                zipf.writestr(('foo%08d' % i), ('%d' % ((i ** 3) % 57)))
            self.assertEqual(len(zipf.namelist()), numfiles2)
        with zipfile.ZipFile(TESTFN, mode='r') as zipf2:
            self.assertEqual(len(zipf2.namelist()), numfiles2)
            for i in range(numfiles2):
                content = zipf2.read(('foo%08d' % i)).decode('ascii')
                self.assertEqual(content, ('%d' % ((i ** 3) % 57)))

    def tearDown(self):
        os_helper.unlink(TESTFN)
        os_helper.unlink(TESTFN2)
if (__name__ == '__main__'):
    unittest.main()
