
import sys
import os
import io
from hashlib import sha256
from contextlib import contextmanager
from random import Random
import pathlib
import unittest
import unittest.mock
import tarfile
from test import support
from test.support import os_helper
from test.support import script_helper
try:
    import gzip
except ImportError:
    gzip = None
try:
    import bz2
except ImportError:
    bz2 = None
try:
    import lzma
except ImportError:
    lzma = None

def sha256sum(data):
    return sha256(data).hexdigest()
TEMPDIR = (os.path.abspath(os_helper.TESTFN) + '-tardir')
tarextdir = (TEMPDIR + '-extract-test')
tarname = support.findfile('testtar.tar')
gzipname = os.path.join(TEMPDIR, 'testtar.tar.gz')
bz2name = os.path.join(TEMPDIR, 'testtar.tar.bz2')
xzname = os.path.join(TEMPDIR, 'testtar.tar.xz')
tmpname = os.path.join(TEMPDIR, 'tmp.tar')
dotlessname = os.path.join(TEMPDIR, 'testtar')
sha256_regtype = 'e09e4bc8b3c9d9177e77256353b36c159f5f040531bbd4b024a8f9b9196c71ce'
sha256_sparse = '4f05a776071146756345ceee937b33fc5644f5a96b9780d1c7d6a32cdf164d7b'

class TarTest():
    tarname = tarname
    suffix = ''
    open = io.FileIO
    taropen = tarfile.TarFile.taropen

    @property
    def mode(self):
        return (self.prefix + self.suffix)

@support.requires_gzip()
class GzipTest():
    tarname = gzipname
    suffix = 'gz'
    open = (gzip.GzipFile if gzip else None)
    taropen = tarfile.TarFile.gzopen

@support.requires_bz2()
class Bz2Test():
    tarname = bz2name
    suffix = 'bz2'
    open = (bz2.BZ2File if bz2 else None)
    taropen = tarfile.TarFile.bz2open

@support.requires_lzma()
class LzmaTest():
    tarname = xzname
    suffix = 'xz'
    open = (lzma.LZMAFile if lzma else None)
    taropen = tarfile.TarFile.xzopen

class ReadTest(TarTest):
    prefix = 'r:'

    def setUp(self):
        self.tar = tarfile.open(self.tarname, mode=self.mode, encoding='iso8859-1')

    def tearDown(self):
        self.tar.close()

class UstarReadTest(ReadTest, unittest.TestCase):

    def test_fileobj_regular_file(self):
        tarinfo = self.tar.getmember('ustar/regtype')
        with self.tar.extractfile(tarinfo) as fobj:
            data = fobj.read()
            self.assertEqual(len(data), tarinfo.size, 'regular file extraction failed')
            self.assertEqual(sha256sum(data), sha256_regtype, 'regular file extraction failed')

    def test_fileobj_readlines(self):
        self.tar.extract('ustar/regtype', TEMPDIR)
        tarinfo = self.tar.getmember('ustar/regtype')
        with open(os.path.join(TEMPDIR, 'ustar/regtype'), 'r') as fobj1:
            lines1 = fobj1.readlines()
        with self.tar.extractfile(tarinfo) as fobj:
            fobj2 = io.TextIOWrapper(fobj)
            lines2 = fobj2.readlines()
            self.assertEqual(lines1, lines2, 'fileobj.readlines() failed')
            self.assertEqual(len(lines2), 114, 'fileobj.readlines() failed')
            self.assertEqual(lines2[83], 'I will gladly admit that Python is not the fastest running scripting language.\n', 'fileobj.readlines() failed')

    def test_fileobj_iter(self):
        self.tar.extract('ustar/regtype', TEMPDIR)
        tarinfo = self.tar.getmember('ustar/regtype')
        with open(os.path.join(TEMPDIR, 'ustar/regtype'), 'r') as fobj1:
            lines1 = fobj1.readlines()
        with self.tar.extractfile(tarinfo) as fobj2:
            lines2 = list(io.TextIOWrapper(fobj2))
            self.assertEqual(lines1, lines2, 'fileobj.__iter__() failed')

    def test_fileobj_seek(self):
        self.tar.extract('ustar/regtype', TEMPDIR)
        with open(os.path.join(TEMPDIR, 'ustar/regtype'), 'rb') as fobj:
            data = fobj.read()
        tarinfo = self.tar.getmember('ustar/regtype')
        with self.tar.extractfile(tarinfo) as fobj:
            text = fobj.read()
            fobj.seek(0)
            self.assertEqual(0, fobj.tell(), "seek() to file's start failed")
            fobj.seek(2048, 0)
            self.assertEqual(2048, fobj.tell(), 'seek() to absolute position failed')
            fobj.seek((- 1024), 1)
            self.assertEqual(1024, fobj.tell(), 'seek() to negative relative position failed')
            fobj.seek(1024, 1)
            self.assertEqual(2048, fobj.tell(), 'seek() to positive relative position failed')
            s = fobj.read(10)
            self.assertEqual(s, data[2048:2058], 'read() after seek failed')
            fobj.seek(0, 2)
            self.assertEqual(tarinfo.size, fobj.tell(), "seek() to file's end failed")
            self.assertEqual(fobj.read(), b'', "read() at file's end did not return empty string")
            fobj.seek((- tarinfo.size), 2)
            self.assertEqual(0, fobj.tell(), "relative seek() to file's end failed")
            fobj.seek(512)
            s1 = fobj.readlines()
            fobj.seek(512)
            s2 = fobj.readlines()
            self.assertEqual(s1, s2, 'readlines() after seek failed')
            fobj.seek(0)
            self.assertEqual(len(fobj.readline()), fobj.tell(), 'tell() after readline() failed')
            fobj.seek(512)
            self.assertEqual((len(fobj.readline()) + 512), fobj.tell(), 'tell() after seek() and readline() failed')
            fobj.seek(0)
            line = fobj.readline()
            self.assertEqual(fobj.read(), data[len(line):], 'read() after readline() failed')

    def test_fileobj_text(self):
        with self.tar.extractfile('ustar/regtype') as fobj:
            fobj = io.TextIOWrapper(fobj)
            data = fobj.read().encode('iso8859-1')
            self.assertEqual(sha256sum(data), sha256_regtype)
            try:
                fobj.seek(100)
            except AttributeError:
                self.fail('seeking failed in text mode')

    def _test_fileobj_link(self, lnktype, regtype):
        with self.tar.extractfile(lnktype) as a, self.tar.extractfile(regtype) as b:
            self.assertEqual(a.name, b.name)

    def test_fileobj_link1(self):
        self._test_fileobj_link('ustar/lnktype', 'ustar/regtype')

    def test_fileobj_link2(self):
        self._test_fileobj_link('./ustar/linktest2/lnktype', 'ustar/linktest1/regtype')

    def test_fileobj_symlink1(self):
        self._test_fileobj_link('ustar/symtype', 'ustar/regtype')

    def test_fileobj_symlink2(self):
        self._test_fileobj_link('./ustar/linktest2/symtype', 'ustar/linktest1/regtype')

    def test_issue14160(self):
        self._test_fileobj_link('symtype2', 'ustar/regtype')

class GzipUstarReadTest(GzipTest, UstarReadTest):
    pass

class Bz2UstarReadTest(Bz2Test, UstarReadTest):
    pass

class LzmaUstarReadTest(LzmaTest, UstarReadTest):
    pass

class ListTest(ReadTest, unittest.TestCase):

    def setUp(self):
        self.tar = tarfile.open(self.tarname, mode=self.mode)

    def test_list(self):
        tio = io.TextIOWrapper(io.BytesIO(), 'ascii', newline='\n')
        with support.swap_attr(sys, 'stdout', tio):
            self.tar.list(verbose=False)
        out = tio.detach().getvalue()
        self.assertIn(b'ustar/conttype', out)
        self.assertIn(b'ustar/regtype', out)
        self.assertIn(b'ustar/lnktype', out)
        self.assertIn(((b'ustar' + (b'/12345' * 40)) + b'67/longname'), out)
        self.assertIn(b'./ustar/linktest2/symtype', out)
        self.assertIn(b'./ustar/linktest2/lnktype', out)
        self.assertIn(b'ustar/dirtype/', out)
        self.assertIn(b'ustar/dirtype-with-size/', out)

        def conv(b):
            s = b.decode(self.tar.encoding, 'surrogateescape')
            return s.encode('ascii', 'backslashreplace')
        self.assertIn(conv(b'ustar/umlauts-\xc4\xd6\xdc\xe4\xf6\xfc\xdf'), out)
        self.assertIn(conv(b'misc/regtype-hpux-signed-chksum-\xc4\xd6\xdc\xe4\xf6\xfc\xdf'), out)
        self.assertIn(conv(b'misc/regtype-old-v7-signed-chksum-\xc4\xd6\xdc\xe4\xf6\xfc\xdf'), out)
        self.assertIn(conv(b'pax/bad-pax-\xe4\xf6\xfc'), out)
        self.assertIn(conv(b'pax/hdrcharset-\xe4\xf6\xfc'), out)
        self.assertRegex(out, b'ustar/conttype ?\\r?\\nustar/regtype ?\\r?\\n')
        self.assertNotIn(b'link to', out)
        self.assertNotIn(b'->', out)

    def test_list_verbose(self):
        tio = io.TextIOWrapper(io.BytesIO(), 'ascii', newline='\n')
        with support.swap_attr(sys, 'stdout', tio):
            self.tar.list(verbose=True)
        out = tio.detach().getvalue()
        self.assertRegex(out, (b'\\?rw-r--r-- tarfile/tarfile\\s+7011 \\d{4}-\\d\\d-\\d\\d\\s+\\d\\d:\\d\\d:\\d\\d ustar/\\w+type ?\\r?\\n' * 2))
        self.assertIn(b'ustar/symtype -> regtype', out)
        self.assertIn(b'./ustar/linktest2/symtype -> ../linktest1/regtype', out)
        self.assertIn(b'./ustar/linktest2/lnktype link to ./ustar/linktest1/regtype', out)
        self.assertIn(((((b'gnu' + (b'/123' * 125)) + b'/longlink link to gnu') + (b'/123' * 125)) + b'/longname'), out)
        self.assertIn(((((b'pax' + (b'/123' * 125)) + b'/longlink link to pax') + (b'/123' * 125)) + b'/longname'), out)

    def test_list_members(self):
        tio = io.TextIOWrapper(io.BytesIO(), 'ascii', newline='\n')

        def members(tar):
            for tarinfo in tar.getmembers():
                if ('reg' in tarinfo.name):
                    (yield tarinfo)
        with support.swap_attr(sys, 'stdout', tio):
            self.tar.list(verbose=False, members=members(self.tar))
        out = tio.detach().getvalue()
        self.assertIn(b'ustar/regtype', out)
        self.assertNotIn(b'ustar/conttype', out)

class GzipListTest(GzipTest, ListTest):
    pass

class Bz2ListTest(Bz2Test, ListTest):
    pass

class LzmaListTest(LzmaTest, ListTest):
    pass

class CommonReadTest(ReadTest):

    def test_is_tarfile_erroneous(self):
        with open(tmpname, 'wb'):
            pass
        self.assertFalse(tarfile.is_tarfile(tmpname))
        self.assertFalse(tarfile.is_tarfile(pathlib.Path(tmpname)))
        with open(tmpname, 'rb') as fobj:
            self.assertFalse(tarfile.is_tarfile(fobj))
        self.assertFalse(tarfile.is_tarfile(io.BytesIO(b'invalid')))

    def test_is_tarfile_valid(self):
        self.assertTrue(tarfile.is_tarfile(self.tarname))
        self.assertTrue(tarfile.is_tarfile(pathlib.Path(self.tarname)))
        with open(self.tarname, 'rb') as fobj:
            self.assertTrue(tarfile.is_tarfile(fobj))
        with open(self.tarname, 'rb') as fobj:
            self.assertTrue(tarfile.is_tarfile(io.BytesIO(fobj.read())))

    def test_empty_tarfile(self):
        with tarfile.open(tmpname, self.mode.replace('r', 'w')):
            pass
        try:
            tar = tarfile.open(tmpname, self.mode)
            tar.getnames()
        except tarfile.ReadError:
            self.fail('tarfile.open() failed on empty archive')
        else:
            self.assertListEqual(tar.getmembers(), [])
        finally:
            tar.close()

    def test_non_existent_tarfile(self):
        with self.assertRaisesRegex(FileNotFoundError, 'xxx'):
            tarfile.open('xxx', self.mode)

    def test_null_tarfile(self):
        with open(tmpname, 'wb'):
            pass
        self.assertRaises(tarfile.ReadError, tarfile.open, tmpname, self.mode)
        self.assertRaises(tarfile.ReadError, tarfile.open, tmpname)

    def test_ignore_zeros(self):
        data = Random(0).randbytes(512)
        for char in (b'\x00', b'a'):
            with self.open(tmpname, 'w') as fobj:
                fobj.write((char * 1024))
                tarinfo = tarfile.TarInfo('foo')
                tarinfo.size = len(data)
                fobj.write(tarinfo.tobuf())
                fobj.write(data)
            tar = tarfile.open(tmpname, mode='r', ignore_zeros=True)
            try:
                self.assertListEqual(tar.getnames(), ['foo'], ('ignore_zeros=True should have skipped the %r-blocks' % char))
            finally:
                tar.close()

    def test_premature_end_of_archive(self):
        for size in (512, 600, 1024, 1200):
            with tarfile.open(tmpname, 'w:') as tar:
                t = tarfile.TarInfo('foo')
                t.size = 1024
                tar.addfile(t, io.BytesIO((b'a' * 1024)))
            with open(tmpname, 'r+b') as fobj:
                fobj.truncate(size)
            with tarfile.open(tmpname) as tar:
                with self.assertRaisesRegex(tarfile.ReadError, 'unexpected end of data'):
                    for t in tar:
                        pass
            with tarfile.open(tmpname) as tar:
                t = tar.next()
                with self.assertRaisesRegex(tarfile.ReadError, 'unexpected end of data'):
                    tar.extract(t, TEMPDIR)
                with self.assertRaisesRegex(tarfile.ReadError, 'unexpected end of data'):
                    tar.extractfile(t).read()

    def test_length_zero_header(self):
        with self.assertRaisesRegex(tarfile.ReadError, 'file could not be opened successfully'):
            with tarfile.open(support.findfile('recursion.tar')) as tar:
                pass

class MiscReadTestBase(CommonReadTest):

    def requires_name_attribute(self):
        pass

    def test_no_name_argument(self):
        self.requires_name_attribute()
        with open(self.tarname, 'rb') as fobj:
            self.assertIsInstance(fobj.name, str)
            with tarfile.open(fileobj=fobj, mode=self.mode) as tar:
                self.assertIsInstance(tar.name, str)
                self.assertEqual(tar.name, os.path.abspath(fobj.name))

    def test_no_name_attribute(self):
        with open(self.tarname, 'rb') as fobj:
            data = fobj.read()
        fobj = io.BytesIO(data)
        self.assertRaises(AttributeError, getattr, fobj, 'name')
        tar = tarfile.open(fileobj=fobj, mode=self.mode)
        self.assertIsNone(tar.name)

    def test_empty_name_attribute(self):
        with open(self.tarname, 'rb') as fobj:
            data = fobj.read()
        fobj = io.BytesIO(data)
        fobj.name = ''
        with tarfile.open(fileobj=fobj, mode=self.mode) as tar:
            self.assertIsNone(tar.name)

    def test_int_name_attribute(self):
        fd = os.open(self.tarname, os.O_RDONLY)
        with open(fd, 'rb') as fobj:
            self.assertIsInstance(fobj.name, int)
            with tarfile.open(fileobj=fobj, mode=self.mode) as tar:
                self.assertIsNone(tar.name)

    def test_bytes_name_attribute(self):
        self.requires_name_attribute()
        tarname = os.fsencode(self.tarname)
        with open(tarname, 'rb') as fobj:
            self.assertIsInstance(fobj.name, bytes)
            with tarfile.open(fileobj=fobj, mode=self.mode) as tar:
                self.assertIsInstance(tar.name, bytes)
                self.assertEqual(tar.name, os.path.abspath(fobj.name))

    def test_pathlike_name(self):
        tarname = pathlib.Path(self.tarname)
        with tarfile.open(tarname, mode=self.mode) as tar:
            self.assertIsInstance(tar.name, str)
            self.assertEqual(tar.name, os.path.abspath(os.fspath(tarname)))
        with self.taropen(tarname) as tar:
            self.assertIsInstance(tar.name, str)
            self.assertEqual(tar.name, os.path.abspath(os.fspath(tarname)))
        with tarfile.TarFile.open(tarname, mode=self.mode) as tar:
            self.assertIsInstance(tar.name, str)
            self.assertEqual(tar.name, os.path.abspath(os.fspath(tarname)))
        if (self.suffix == ''):
            with tarfile.TarFile(tarname, mode='r') as tar:
                self.assertIsInstance(tar.name, str)
                self.assertEqual(tar.name, os.path.abspath(os.fspath(tarname)))

    def test_illegal_mode_arg(self):
        with open(tmpname, 'wb'):
            pass
        with self.assertRaisesRegex(ValueError, 'mode must be '):
            tar = self.taropen(tmpname, 'q')
        with self.assertRaisesRegex(ValueError, 'mode must be '):
            tar = self.taropen(tmpname, 'rw')
        with self.assertRaisesRegex(ValueError, 'mode must be '):
            tar = self.taropen(tmpname, '')

    def test_fileobj_with_offset(self):
        tar = tarfile.open(self.tarname, mode=self.mode)
        try:
            tar.next()
            t = tar.next()
            name = t.name
            offset = t.offset
            with tar.extractfile(t) as f:
                data = f.read()
        finally:
            tar.close()
        with self.open(self.tarname) as fobj:
            fobj.seek(offset)
            with tar.open(self.tarname, mode='r:', fileobj=fobj) as tar:
                t = tar.next()
                self.assertEqual(t.name, name)
                tar.getmembers()
                self.assertEqual(tar.extractfile(t).read(), data, 'seek back did not work')

    def test_fail_comp(self):
        self.assertRaises(tarfile.ReadError, tarfile.open, tarname, self.mode)
        with open(tarname, 'rb') as fobj:
            self.assertRaises(tarfile.ReadError, tarfile.open, fileobj=fobj, mode=self.mode)

    def test_v7_dirtype(self):
        tarinfo = self.tar.getmember('misc/dirtype-old-v7')
        self.assertEqual(tarinfo.type, tarfile.DIRTYPE, 'v7 dirtype failed')

    def test_xstar_type(self):
        try:
            self.tar.getmember('misc/regtype-xstar')
        except KeyError:
            self.fail('failed to find misc/regtype-xstar (mangled prefix?)')

    def test_check_members(self):
        for tarinfo in self.tar:
            self.assertEqual(int(tarinfo.mtime), 1041808783, ('wrong mtime for %s' % tarinfo.name))
            if (not tarinfo.name.startswith('ustar/')):
                continue
            self.assertEqual(tarinfo.uname, 'tarfile', ('wrong uname for %s' % tarinfo.name))

    def test_find_members(self):
        self.assertEqual(self.tar.getmembers()[(- 1)].name, 'misc/eof', 'could not find all members')

    @unittest.skipUnless(hasattr(os, 'link'), 'Missing hardlink implementation')
    @os_helper.skip_unless_symlink
    def test_extract_hardlink(self):
        with tarfile.open(tarname, errorlevel=1, encoding='iso8859-1') as tar:
            tar.extract('ustar/regtype', TEMPDIR)
            self.addCleanup(os_helper.unlink, os.path.join(TEMPDIR, 'ustar/regtype'))
            tar.extract('ustar/lnktype', TEMPDIR)
            self.addCleanup(os_helper.unlink, os.path.join(TEMPDIR, 'ustar/lnktype'))
            with open(os.path.join(TEMPDIR, 'ustar/lnktype'), 'rb') as f:
                data = f.read()
            self.assertEqual(sha256sum(data), sha256_regtype)
            tar.extract('ustar/symtype', TEMPDIR)
            self.addCleanup(os_helper.unlink, os.path.join(TEMPDIR, 'ustar/symtype'))
            with open(os.path.join(TEMPDIR, 'ustar/symtype'), 'rb') as f:
                data = f.read()
            self.assertEqual(sha256sum(data), sha256_regtype)

    def test_extractall(self):
        tar = tarfile.open(tarname, encoding='iso8859-1')
        DIR = os.path.join(TEMPDIR, 'extractall')
        os.mkdir(DIR)
        try:
            directories = [t for t in tar if t.isdir()]
            tar.extractall(DIR, directories)
            for tarinfo in directories:
                path = os.path.join(DIR, tarinfo.name)
                if (sys.platform != 'win32'):
                    self.assertEqual((tarinfo.mode & 511), (os.stat(path).st_mode & 511))

                def format_mtime(mtime):
                    if isinstance(mtime, float):
                        return '{} ({})'.format(mtime, mtime.hex())
                    else:
                        return '{!r} (int)'.format(mtime)
                file_mtime = os.path.getmtime(path)
                errmsg = 'tar mtime {0} != file time {1} of path {2!a}'.format(format_mtime(tarinfo.mtime), format_mtime(file_mtime), path)
                self.assertEqual(tarinfo.mtime, file_mtime, errmsg)
        finally:
            tar.close()
            os_helper.rmtree(DIR)

    def test_extract_directory(self):
        dirtype = 'ustar/dirtype'
        DIR = os.path.join(TEMPDIR, 'extractdir')
        os.mkdir(DIR)
        try:
            with tarfile.open(tarname, encoding='iso8859-1') as tar:
                tarinfo = tar.getmember(dirtype)
                tar.extract(tarinfo, path=DIR)
                extracted = os.path.join(DIR, dirtype)
                self.assertEqual(os.path.getmtime(extracted), tarinfo.mtime)
                if (sys.platform != 'win32'):
                    self.assertEqual((os.stat(extracted).st_mode & 511), 493)
        finally:
            os_helper.rmtree(DIR)

    def test_extractall_pathlike_name(self):
        DIR = (pathlib.Path(TEMPDIR) / 'extractall')
        with os_helper.temp_dir(DIR), tarfile.open(tarname, encoding='iso8859-1') as tar:
            directories = [t for t in tar if t.isdir()]
            tar.extractall(DIR, directories)
            for tarinfo in directories:
                path = (DIR / tarinfo.name)
                self.assertEqual(os.path.getmtime(path), tarinfo.mtime)

    def test_extract_pathlike_name(self):
        dirtype = 'ustar/dirtype'
        DIR = (pathlib.Path(TEMPDIR) / 'extractall')
        with os_helper.temp_dir(DIR), tarfile.open(tarname, encoding='iso8859-1') as tar:
            tarinfo = tar.getmember(dirtype)
            tar.extract(tarinfo, path=DIR)
            extracted = (DIR / dirtype)
            self.assertEqual(os.path.getmtime(extracted), tarinfo.mtime)

    def test_init_close_fobj(self):
        empty = os.path.join(TEMPDIR, 'empty')
        with open(empty, 'wb') as fobj:
            fobj.write(b'')
        try:
            tar = object.__new__(tarfile.TarFile)
            try:
                tar.__init__(empty)
            except tarfile.ReadError:
                self.assertTrue(tar.fileobj.closed)
            else:
                self.fail('ReadError not raised')
        finally:
            os_helper.unlink(empty)

    def test_parallel_iteration(self):
        with tarfile.open(self.tarname) as tar:
            for (m1, m2) in zip(tar, tar):
                self.assertEqual(m1.offset, m2.offset)
                self.assertEqual(m1.get_info(), m2.get_info())

class MiscReadTest(MiscReadTestBase, unittest.TestCase):
    test_fail_comp = None

class GzipMiscReadTest(GzipTest, MiscReadTestBase, unittest.TestCase):
    pass

class Bz2MiscReadTest(Bz2Test, MiscReadTestBase, unittest.TestCase):

    def requires_name_attribute(self):
        self.skipTest('BZ2File have no name attribute')

class LzmaMiscReadTest(LzmaTest, MiscReadTestBase, unittest.TestCase):

    def requires_name_attribute(self):
        self.skipTest('LZMAFile have no name attribute')

class StreamReadTest(CommonReadTest, unittest.TestCase):
    prefix = 'r|'

    def test_read_through(self):
        for tarinfo in self.tar:
            if (not tarinfo.isreg()):
                continue
            with self.tar.extractfile(tarinfo) as fobj:
                while True:
                    try:
                        buf = fobj.read(512)
                    except tarfile.StreamError:
                        self.fail('simple read-through using TarFile.extractfile() failed')
                    if (not buf):
                        break

    def test_fileobj_regular_file(self):
        tarinfo = self.tar.next()
        with self.tar.extractfile(tarinfo) as fobj:
            data = fobj.read()
        self.assertEqual(len(data), tarinfo.size, 'regular file extraction failed')
        self.assertEqual(sha256sum(data), sha256_regtype, 'regular file extraction failed')

    def test_provoke_stream_error(self):
        tarinfos = self.tar.getmembers()
        with self.tar.extractfile(tarinfos[0]) as f:
            self.assertRaises(tarfile.StreamError, f.read)

    def test_compare_members(self):
        tar1 = tarfile.open(tarname, encoding='iso8859-1')
        try:
            tar2 = self.tar
            while True:
                t1 = tar1.next()
                t2 = tar2.next()
                if (t1 is None):
                    break
                self.assertIsNotNone(t2, 'stream.next() failed.')
                if (t2.islnk() or t2.issym()):
                    with self.assertRaises(tarfile.StreamError):
                        tar2.extractfile(t2)
                    continue
                v1 = tar1.extractfile(t1)
                v2 = tar2.extractfile(t2)
                if (v1 is None):
                    continue
                self.assertIsNotNone(v2, 'stream.extractfile() failed')
                self.assertEqual(v1.read(), v2.read(), 'stream extraction failed')
        finally:
            tar1.close()

class GzipStreamReadTest(GzipTest, StreamReadTest):
    pass

class Bz2StreamReadTest(Bz2Test, StreamReadTest):
    pass

class LzmaStreamReadTest(LzmaTest, StreamReadTest):
    pass

class DetectReadTest(TarTest, unittest.TestCase):

    def _testfunc_file(self, name, mode):
        try:
            tar = tarfile.open(name, mode)
        except tarfile.ReadError as e:
            self.fail()
        else:
            tar.close()

    def _testfunc_fileobj(self, name, mode):
        try:
            with open(name, 'rb') as f:
                tar = tarfile.open(name, mode, fileobj=f)
        except tarfile.ReadError as e:
            self.fail()
        else:
            tar.close()

    def _test_modes(self, testfunc):
        if self.suffix:
            with self.assertRaises(tarfile.ReadError):
                tarfile.open(tarname, mode=('r:' + self.suffix))
            with self.assertRaises(tarfile.ReadError):
                tarfile.open(tarname, mode=('r|' + self.suffix))
            with self.assertRaises(tarfile.ReadError):
                tarfile.open(self.tarname, mode='r:')
            with self.assertRaises(tarfile.ReadError):
                tarfile.open(self.tarname, mode='r|')
        testfunc(self.tarname, 'r')
        testfunc(self.tarname, ('r:' + self.suffix))
        testfunc(self.tarname, 'r:*')
        testfunc(self.tarname, ('r|' + self.suffix))
        testfunc(self.tarname, 'r|*')

    def test_detect_file(self):
        self._test_modes(self._testfunc_file)

    def test_detect_fileobj(self):
        self._test_modes(self._testfunc_fileobj)

class GzipDetectReadTest(GzipTest, DetectReadTest):
    pass

class Bz2DetectReadTest(Bz2Test, DetectReadTest):

    def test_detect_stream_bz2(self):
        with open(tarname, 'rb') as fobj:
            data = fobj.read()
        with bz2.BZ2File(tmpname, 'wb', compresslevel=1) as fobj:
            fobj.write(data)
        self._testfunc_file(tmpname, 'r|*')

class LzmaDetectReadTest(LzmaTest, DetectReadTest):
    pass

class MemberReadTest(ReadTest, unittest.TestCase):

    def _test_member(self, tarinfo, chksum=None, **kwargs):
        if (chksum is not None):
            with self.tar.extractfile(tarinfo) as f:
                self.assertEqual(sha256sum(f.read()), chksum, ('wrong sha256sum for %s' % tarinfo.name))
        kwargs['mtime'] = 1041808783
        kwargs['uid'] = 1000
        kwargs['gid'] = 100
        if ('old-v7' not in tarinfo.name):
            kwargs['uname'] = 'tarfile'
            kwargs['gname'] = 'tarfile'
        for (k, v) in kwargs.items():
            self.assertEqual(getattr(tarinfo, k), v, ('wrong value in %s field of %s' % (k, tarinfo.name)))

    def test_find_regtype(self):
        tarinfo = self.tar.getmember('ustar/regtype')
        self._test_member(tarinfo, size=7011, chksum=sha256_regtype)

    def test_find_conttype(self):
        tarinfo = self.tar.getmember('ustar/conttype')
        self._test_member(tarinfo, size=7011, chksum=sha256_regtype)

    def test_find_dirtype(self):
        tarinfo = self.tar.getmember('ustar/dirtype')
        self._test_member(tarinfo, size=0)

    def test_find_dirtype_with_size(self):
        tarinfo = self.tar.getmember('ustar/dirtype-with-size')
        self._test_member(tarinfo, size=255)

    def test_find_lnktype(self):
        tarinfo = self.tar.getmember('ustar/lnktype')
        self._test_member(tarinfo, size=0, linkname='ustar/regtype')

    def test_find_symtype(self):
        tarinfo = self.tar.getmember('ustar/symtype')
        self._test_member(tarinfo, size=0, linkname='regtype')

    def test_find_blktype(self):
        tarinfo = self.tar.getmember('ustar/blktype')
        self._test_member(tarinfo, size=0, devmajor=3, devminor=0)

    def test_find_chrtype(self):
        tarinfo = self.tar.getmember('ustar/chrtype')
        self._test_member(tarinfo, size=0, devmajor=1, devminor=3)

    def test_find_fifotype(self):
        tarinfo = self.tar.getmember('ustar/fifotype')
        self._test_member(tarinfo, size=0)

    def test_find_sparse(self):
        tarinfo = self.tar.getmember('ustar/sparse')
        self._test_member(tarinfo, size=86016, chksum=sha256_sparse)

    def test_find_gnusparse(self):
        tarinfo = self.tar.getmember('gnu/sparse')
        self._test_member(tarinfo, size=86016, chksum=sha256_sparse)

    def test_find_gnusparse_00(self):
        tarinfo = self.tar.getmember('gnu/sparse-0.0')
        self._test_member(tarinfo, size=86016, chksum=sha256_sparse)

    def test_find_gnusparse_01(self):
        tarinfo = self.tar.getmember('gnu/sparse-0.1')
        self._test_member(tarinfo, size=86016, chksum=sha256_sparse)

    def test_find_gnusparse_10(self):
        tarinfo = self.tar.getmember('gnu/sparse-1.0')
        self._test_member(tarinfo, size=86016, chksum=sha256_sparse)

    def test_find_umlauts(self):
        tarinfo = self.tar.getmember('ustar/umlauts-ÄÖÜäöüß')
        self._test_member(tarinfo, size=7011, chksum=sha256_regtype)

    def test_find_ustar_longname(self):
        name = (('ustar/' + ('12345/' * 39)) + '1234567/longname')
        self.assertIn(name, self.tar.getnames())

    def test_find_regtype_oldv7(self):
        tarinfo = self.tar.getmember('misc/regtype-old-v7')
        self._test_member(tarinfo, size=7011, chksum=sha256_regtype)

    def test_find_pax_umlauts(self):
        self.tar.close()
        self.tar = tarfile.open(self.tarname, mode=self.mode, encoding='iso8859-1')
        tarinfo = self.tar.getmember('pax/umlauts-ÄÖÜäöüß')
        self._test_member(tarinfo, size=7011, chksum=sha256_regtype)

class LongnameTest():

    def test_read_longname(self):
        longname = (((self.subdir + '/') + ('123/' * 125)) + 'longname')
        try:
            tarinfo = self.tar.getmember(longname)
        except KeyError:
            self.fail('longname not found')
        self.assertNotEqual(tarinfo.type, tarfile.DIRTYPE, 'read longname as dirtype')

    def test_read_longlink(self):
        longname = (((self.subdir + '/') + ('123/' * 125)) + 'longname')
        longlink = (((self.subdir + '/') + ('123/' * 125)) + 'longlink')
        try:
            tarinfo = self.tar.getmember(longlink)
        except KeyError:
            self.fail('longlink not found')
        self.assertEqual(tarinfo.linkname, longname, 'linkname wrong')

    def test_truncated_longname(self):
        longname = (((self.subdir + '/') + ('123/' * 125)) + 'longname')
        tarinfo = self.tar.getmember(longname)
        offset = tarinfo.offset
        self.tar.fileobj.seek(offset)
        fobj = io.BytesIO(self.tar.fileobj.read((3 * 512)))
        with self.assertRaises(tarfile.ReadError):
            tarfile.open(name='foo.tar', fileobj=fobj)

    def test_header_offset(self):
        longname = (((self.subdir + '/') + ('123/' * 125)) + 'longname')
        offset = self.tar.getmember(longname).offset
        with open(tarname, 'rb') as fobj:
            fobj.seek(offset)
            tarinfo = tarfile.TarInfo.frombuf(fobj.read(512), 'iso8859-1', 'strict')
            self.assertEqual(tarinfo.type, self.longnametype)

class GNUReadTest(LongnameTest, ReadTest, unittest.TestCase):
    subdir = 'gnu'
    longnametype = tarfile.GNUTYPE_LONGNAME

    def _test_sparse_file(self, name):
        self.tar.extract(name, TEMPDIR)
        filename = os.path.join(TEMPDIR, name)
        with open(filename, 'rb') as fobj:
            data = fobj.read()
        self.assertEqual(sha256sum(data), sha256_sparse, ('wrong sha256sum for %s' % name))
        if self._fs_supports_holes():
            s = os.stat(filename)
            self.assertLess((s.st_blocks * 512), s.st_size)

    def test_sparse_file_old(self):
        self._test_sparse_file('gnu/sparse')

    def test_sparse_file_00(self):
        self._test_sparse_file('gnu/sparse-0.0')

    def test_sparse_file_01(self):
        self._test_sparse_file('gnu/sparse-0.1')

    def test_sparse_file_10(self):
        self._test_sparse_file('gnu/sparse-1.0')

    @staticmethod
    def _fs_supports_holes():
        if sys.platform.startswith('linux'):
            name = os.path.join(TEMPDIR, 'sparse-test')
            with open(name, 'wb') as fobj:
                fobj.seek(4096)
                fobj.write((b'x' * 4096))
                fobj.truncate()
            s = os.stat(name)
            os_helper.unlink(name)
            return ((s.st_blocks * 512) < s.st_size)
        else:
            return False

class PaxReadTest(LongnameTest, ReadTest, unittest.TestCase):
    subdir = 'pax'
    longnametype = tarfile.XHDTYPE

    def test_pax_global_headers(self):
        tar = tarfile.open(tarname, encoding='iso8859-1')
        try:
            tarinfo = tar.getmember('pax/regtype1')
            self.assertEqual(tarinfo.uname, 'foo')
            self.assertEqual(tarinfo.gname, 'bar')
            self.assertEqual(tarinfo.pax_headers.get('VENDOR.umlauts'), 'ÄÖÜäöüß')
            tarinfo = tar.getmember('pax/regtype2')
            self.assertEqual(tarinfo.uname, '')
            self.assertEqual(tarinfo.gname, 'bar')
            self.assertEqual(tarinfo.pax_headers.get('VENDOR.umlauts'), 'ÄÖÜäöüß')
            tarinfo = tar.getmember('pax/regtype3')
            self.assertEqual(tarinfo.uname, 'tarfile')
            self.assertEqual(tarinfo.gname, 'tarfile')
            self.assertEqual(tarinfo.pax_headers.get('VENDOR.umlauts'), 'ÄÖÜäöüß')
        finally:
            tar.close()

    def test_pax_number_fields(self):
        tar = tarfile.open(tarname, encoding='iso8859-1')
        try:
            tarinfo = tar.getmember('pax/regtype4')
            self.assertEqual(tarinfo.size, 7011)
            self.assertEqual(tarinfo.uid, 123)
            self.assertEqual(tarinfo.gid, 123)
            self.assertEqual(tarinfo.mtime, 1041808783.0)
            self.assertEqual(type(tarinfo.mtime), float)
            self.assertEqual(float(tarinfo.pax_headers['atime']), 1041808783.0)
            self.assertEqual(float(tarinfo.pax_headers['ctime']), 1041808783.0)
        finally:
            tar.close()

class WriteTestBase(TarTest):

    def test_fileobj_no_close(self):
        fobj = io.BytesIO()
        with tarfile.open(fileobj=fobj, mode=self.mode) as tar:
            tar.addfile(tarfile.TarInfo('foo'))
        self.assertFalse(fobj.closed, 'external fileobjs must never closed')
        data = fobj.getvalue()
        del tar
        support.gc_collect()
        self.assertFalse(fobj.closed)
        self.assertEqual(data, fobj.getvalue())

    def test_eof_marker(self):
        with tarfile.open(tmpname, self.mode) as tar:
            t = tarfile.TarInfo('foo')
            t.size = (tarfile.RECORDSIZE - tarfile.BLOCKSIZE)
            tar.addfile(t, io.BytesIO((b'a' * t.size)))
        with self.open(tmpname, 'rb') as fobj:
            self.assertEqual(len(fobj.read()), (tarfile.RECORDSIZE * 2))

class WriteTest(WriteTestBase, unittest.TestCase):
    prefix = 'w:'

    def test_100_char_name(self):
        name = ('0123456789' * 10)
        tar = tarfile.open(tmpname, self.mode)
        try:
            t = tarfile.TarInfo(name)
            tar.addfile(t)
        finally:
            tar.close()
        tar = tarfile.open(tmpname)
        try:
            self.assertEqual(tar.getnames()[0], name, 'failed to store 100 char filename')
        finally:
            tar.close()

    def test_tar_size(self):
        tar = tarfile.open(tmpname, self.mode)
        try:
            path = os.path.join(TEMPDIR, 'file')
            with open(path, 'wb') as fobj:
                fobj.write(b'aaa')
            tar.add(path)
        finally:
            tar.close()
        self.assertGreater(os.path.getsize(tmpname), 0, 'tarfile is empty')

    def test_file_size(self):
        tar = tarfile.open(tmpname, self.mode)
        try:
            path = os.path.join(TEMPDIR, 'file')
            with open(path, 'wb'):
                pass
            tarinfo = tar.gettarinfo(path)
            self.assertEqual(tarinfo.size, 0)
            with open(path, 'wb') as fobj:
                fobj.write(b'aaa')
            tarinfo = tar.gettarinfo(path)
            self.assertEqual(tarinfo.size, 3)
        finally:
            tar.close()

    def test_directory_size(self):
        path = os.path.join(TEMPDIR, 'directory')
        os.mkdir(path)
        try:
            tar = tarfile.open(tmpname, self.mode)
            try:
                tarinfo = tar.gettarinfo(path)
                self.assertEqual(tarinfo.size, 0)
            finally:
                tar.close()
        finally:
            os_helper.rmdir(path)

    def test_ordered_recursion(self):
        path = os.path.join(TEMPDIR, 'directory')
        os.mkdir(path)
        open(os.path.join(path, '1'), 'a').close()
        open(os.path.join(path, '2'), 'a').close()
        try:
            tar = tarfile.open(tmpname, self.mode)
            try:
                with unittest.mock.patch('os.listdir') as mock_listdir:
                    mock_listdir.return_value = ['2', '1']
                    tar.add(path)
                paths = []
                for m in tar.getmembers():
                    paths.append(os.path.split(m.name)[(- 1)])
                self.assertEqual(paths, ['directory', '1', '2'])
            finally:
                tar.close()
        finally:
            os_helper.unlink(os.path.join(path, '1'))
            os_helper.unlink(os.path.join(path, '2'))
            os_helper.rmdir(path)

    def test_gettarinfo_pathlike_name(self):
        with tarfile.open(tmpname, self.mode) as tar:
            path = (pathlib.Path(TEMPDIR) / 'file')
            with open(path, 'wb') as fobj:
                fobj.write(b'aaa')
            tarinfo = tar.gettarinfo(path)
            tarinfo2 = tar.gettarinfo(os.fspath(path))
            self.assertIsInstance(tarinfo.name, str)
            self.assertEqual(tarinfo.name, tarinfo2.name)
            self.assertEqual(tarinfo.size, 3)

    @unittest.skipUnless(hasattr(os, 'link'), 'Missing hardlink implementation')
    def test_link_size(self):
        link = os.path.join(TEMPDIR, 'link')
        target = os.path.join(TEMPDIR, 'link_target')
        with open(target, 'wb') as fobj:
            fobj.write(b'aaa')
        try:
            os.link(target, link)
        except PermissionError as e:
            self.skipTest(('os.link(): %s' % e))
        try:
            tar = tarfile.open(tmpname, self.mode)
            try:
                tar.gettarinfo(target)
                tarinfo = tar.gettarinfo(link)
                self.assertEqual(tarinfo.size, 0)
            finally:
                tar.close()
        finally:
            os_helper.unlink(target)
            os_helper.unlink(link)

    @os_helper.skip_unless_symlink
    def test_symlink_size(self):
        path = os.path.join(TEMPDIR, 'symlink')
        os.symlink('link_target', path)
        try:
            tar = tarfile.open(tmpname, self.mode)
            try:
                tarinfo = tar.gettarinfo(path)
                self.assertEqual(tarinfo.size, 0)
            finally:
                tar.close()
        finally:
            os_helper.unlink(path)

    def test_add_self(self):
        dstname = os.path.abspath(tmpname)
        tar = tarfile.open(tmpname, self.mode)
        try:
            self.assertEqual(tar.name, dstname, 'archive name must be absolute')
            tar.add(dstname)
            self.assertEqual(tar.getnames(), [], 'added the archive to itself')
            with os_helper.change_cwd(TEMPDIR):
                tar.add(dstname)
            self.assertEqual(tar.getnames(), [], 'added the archive to itself')
        finally:
            tar.close()

    def test_filter(self):
        tempdir = os.path.join(TEMPDIR, 'filter')
        os.mkdir(tempdir)
        try:
            for name in ('foo', 'bar', 'baz'):
                name = os.path.join(tempdir, name)
                os_helper.create_empty_file(name)

            def filter(tarinfo):
                if (os.path.basename(tarinfo.name) == 'bar'):
                    return
                tarinfo.uid = 123
                tarinfo.uname = 'foo'
                return tarinfo
            tar = tarfile.open(tmpname, self.mode, encoding='iso8859-1')
            try:
                tar.add(tempdir, arcname='empty_dir', filter=filter)
            finally:
                tar.close()
            with self.assertRaises(TypeError):
                tar.add(tempdir, 'empty_dir', True, None, filter)
            tar = tarfile.open(tmpname, 'r')
            try:
                for tarinfo in tar:
                    self.assertEqual(tarinfo.uid, 123)
                    self.assertEqual(tarinfo.uname, 'foo')
                self.assertEqual(len(tar.getmembers()), 3)
            finally:
                tar.close()
        finally:
            os_helper.rmtree(tempdir)

    def _test_pathname(self, path, cmp_path=None, dir=False):
        foo = os.path.join(TEMPDIR, 'foo')
        if (not dir):
            os_helper.create_empty_file(foo)
        else:
            os.mkdir(foo)
        tar = tarfile.open(tmpname, self.mode)
        try:
            tar.add(foo, arcname=path)
        finally:
            tar.close()
        tar = tarfile.open(tmpname, 'r')
        try:
            t = tar.next()
        finally:
            tar.close()
        if (not dir):
            os_helper.unlink(foo)
        else:
            os_helper.rmdir(foo)
        self.assertEqual(t.name, (cmp_path or path.replace(os.sep, '/')))

    @os_helper.skip_unless_symlink
    def test_extractall_symlinks(self):
        tempdir = os.path.join(TEMPDIR, 'testsymlinks')
        temparchive = os.path.join(TEMPDIR, 'testsymlinks.tar')
        os.mkdir(tempdir)
        try:
            source_file = os.path.join(tempdir, 'source')
            target_file = os.path.join(tempdir, 'symlink')
            with open(source_file, 'w') as f:
                f.write('something\n')
            os.symlink(source_file, target_file)
            with tarfile.open(temparchive, 'w') as tar:
                tar.add(source_file)
                tar.add(target_file)
            with tarfile.open(temparchive) as tar:
                try:
                    tar.extractall(path=tempdir)
                except OSError:
                    self.fail('extractall failed with symlinked files')
        finally:
            os_helper.unlink(temparchive)
            os_helper.rmtree(tempdir)

    def test_pathnames(self):
        self._test_pathname('foo')
        self._test_pathname(os.path.join('foo', '.', 'bar'))
        self._test_pathname(os.path.join('foo', '..', 'bar'))
        self._test_pathname(os.path.join('.', 'foo'))
        self._test_pathname(os.path.join('.', 'foo', '.'))
        self._test_pathname(os.path.join('.', 'foo', '.', 'bar'))
        self._test_pathname(os.path.join('.', 'foo', '..', 'bar'))
        self._test_pathname(os.path.join('.', 'foo', '..', 'bar'))
        self._test_pathname(os.path.join('..', 'foo'))
        self._test_pathname(os.path.join('..', 'foo', '..'))
        self._test_pathname(os.path.join('..', 'foo', '.', 'bar'))
        self._test_pathname(os.path.join('..', 'foo', '..', 'bar'))
        self._test_pathname(((('foo' + os.sep) + os.sep) + 'bar'))
        self._test_pathname((('foo' + os.sep) + os.sep), 'foo', dir=True)

    def test_abs_pathnames(self):
        if (sys.platform == 'win32'):
            self._test_pathname('C:\\foo', 'foo')
        else:
            self._test_pathname('/foo', 'foo')
            self._test_pathname('///foo', 'foo')

    def test_cwd(self):
        with os_helper.change_cwd(TEMPDIR):
            tar = tarfile.open(tmpname, self.mode)
            try:
                tar.add('.')
            finally:
                tar.close()
            tar = tarfile.open(tmpname, 'r')
            try:
                for t in tar:
                    if (t.name != '.'):
                        self.assertTrue(t.name.startswith('./'), t.name)
            finally:
                tar.close()

    def test_open_nonwritable_fileobj(self):
        for exctype in (OSError, EOFError, RuntimeError):

            class BadFile(io.BytesIO):
                first = True

                def write(self, data):
                    if self.first:
                        self.first = False
                        raise exctype
            f = BadFile()
            with self.assertRaises(exctype):
                tar = tarfile.open(tmpname, self.mode, fileobj=f, format=tarfile.PAX_FORMAT, pax_headers={'non': 'empty'})
            self.assertFalse(f.closed)

class GzipWriteTest(GzipTest, WriteTest):
    pass

class Bz2WriteTest(Bz2Test, WriteTest):
    pass

class LzmaWriteTest(LzmaTest, WriteTest):
    pass

class StreamWriteTest(WriteTestBase, unittest.TestCase):
    prefix = 'w|'
    decompressor = None

    def test_stream_padding(self):
        tar = tarfile.open(tmpname, self.mode)
        tar.close()
        if self.decompressor:
            dec = self.decompressor()
            with open(tmpname, 'rb') as fobj:
                data = fobj.read()
            data = dec.decompress(data)
            self.assertFalse(dec.unused_data, 'found trailing data')
        else:
            with self.open(tmpname) as fobj:
                data = fobj.read()
        self.assertEqual(data.count(b'\x00'), tarfile.RECORDSIZE, 'incorrect zero padding')

    @unittest.skipUnless(((sys.platform != 'win32') and hasattr(os, 'umask')), 'Missing umask implementation')
    def test_file_mode(self):
        if os.path.exists(tmpname):
            os_helper.unlink(tmpname)
        original_umask = os.umask(18)
        try:
            tar = tarfile.open(tmpname, self.mode)
            tar.close()
            mode = (os.stat(tmpname).st_mode & 511)
            self.assertEqual(mode, 420, 'wrong file permissions')
        finally:
            os.umask(original_umask)

class GzipStreamWriteTest(GzipTest, StreamWriteTest):
    pass

class Bz2StreamWriteTest(Bz2Test, StreamWriteTest):
    decompressor = (bz2.BZ2Decompressor if bz2 else None)

class LzmaStreamWriteTest(LzmaTest, StreamWriteTest):
    decompressor = (lzma.LZMADecompressor if lzma else None)

class GNUWriteTest(unittest.TestCase):

    def _length(self, s):
        blocks = ((len(s) // 512) + 1)
        return (blocks * 512)

    def _calc_size(self, name, link=None):
        count = 512
        if (len(name) > tarfile.LENGTH_NAME):
            count += 512
            count += self._length(name)
        if ((link is not None) and (len(link) > tarfile.LENGTH_LINK)):
            count += 512
            count += self._length(link)
        return count

    def _test(self, name, link=None):
        tarinfo = tarfile.TarInfo(name)
        if link:
            tarinfo.linkname = link
            tarinfo.type = tarfile.LNKTYPE
        tar = tarfile.open(tmpname, 'w')
        try:
            tar.format = tarfile.GNU_FORMAT
            tar.addfile(tarinfo)
            v1 = self._calc_size(name, link)
            v2 = tar.offset
            self.assertEqual(v1, v2, 'GNU longname/longlink creation failed')
        finally:
            tar.close()
        tar = tarfile.open(tmpname)
        try:
            member = tar.next()
            self.assertIsNotNone(member, 'unable to read longname member')
            self.assertEqual(tarinfo.name, member.name, 'unable to read longname member')
            self.assertEqual(tarinfo.linkname, member.linkname, 'unable to read longname member')
        finally:
            tar.close()

    def test_longname_1023(self):
        self._test((('longnam/' * 127) + 'longnam'))

    def test_longname_1024(self):
        self._test((('longnam/' * 127) + 'longname'))

    def test_longname_1025(self):
        self._test((('longnam/' * 127) + 'longname_'))

    def test_longlink_1023(self):
        self._test('name', (('longlnk/' * 127) + 'longlnk'))

    def test_longlink_1024(self):
        self._test('name', (('longlnk/' * 127) + 'longlink'))

    def test_longlink_1025(self):
        self._test('name', (('longlnk/' * 127) + 'longlink_'))

    def test_longnamelink_1023(self):
        self._test((('longnam/' * 127) + 'longnam'), (('longlnk/' * 127) + 'longlnk'))

    def test_longnamelink_1024(self):
        self._test((('longnam/' * 127) + 'longname'), (('longlnk/' * 127) + 'longlink'))

    def test_longnamelink_1025(self):
        self._test((('longnam/' * 127) + 'longname_'), (('longlnk/' * 127) + 'longlink_'))

class DeviceHeaderTest(WriteTestBase, unittest.TestCase):
    prefix = 'w:'

    def test_headers_written_only_for_device_files(self):
        tempdir = os.path.join(TEMPDIR, 'device_header_test')
        os.mkdir(tempdir)
        try:
            tar = tarfile.open(tmpname, self.mode)
            try:
                input_blk = tarfile.TarInfo(name='my_block_device')
                input_reg = tarfile.TarInfo(name='my_regular_file')
                input_blk.type = tarfile.BLKTYPE
                input_reg.type = tarfile.REGTYPE
                tar.addfile(input_blk)
                tar.addfile(input_reg)
            finally:
                tar.close()
            tar = tarfile.open(tmpname, 'r')
            try:
                output_blk = tar.getmember('my_block_device')
                output_reg = tar.getmember('my_regular_file')
            finally:
                tar.close()
            self.assertEqual(output_blk.devmajor, 0)
            self.assertEqual(output_blk.devminor, 0)
            self.assertEqual(output_reg.devmajor, 0)
            self.assertEqual(output_reg.devminor, 0)
            with open(tmpname, 'rb') as infile:
                buf = infile.read()
            buf_blk = buf[output_blk.offset:output_blk.offset_data]
            buf_reg = buf[output_reg.offset:output_reg.offset_data]
            device_headers = slice(329, (329 + 16))
            self.assertEqual(buf_blk[device_headers], (b'0000000\x00' * 2))
            self.assertEqual(buf_reg[device_headers], (b'\x00' * 16))
        finally:
            os_helper.rmtree(tempdir)

class CreateTest(WriteTestBase, unittest.TestCase):
    prefix = 'x:'
    file_path = os.path.join(TEMPDIR, 'spameggs42')

    def setUp(self):
        os_helper.unlink(tmpname)

    @classmethod
    def setUpClass(cls):
        with open(cls.file_path, 'wb') as fobj:
            fobj.write(b'aaa')

    @classmethod
    def tearDownClass(cls):
        os_helper.unlink(cls.file_path)

    def test_create(self):
        with tarfile.open(tmpname, self.mode) as tobj:
            tobj.add(self.file_path)
        with self.taropen(tmpname) as tobj:
            names = tobj.getnames()
        self.assertEqual(len(names), 1)
        self.assertIn('spameggs42', names[0])

    def test_create_existing(self):
        with tarfile.open(tmpname, self.mode) as tobj:
            tobj.add(self.file_path)
        with self.assertRaises(FileExistsError):
            tobj = tarfile.open(tmpname, self.mode)
        with self.taropen(tmpname) as tobj:
            names = tobj.getnames()
        self.assertEqual(len(names), 1)
        self.assertIn('spameggs42', names[0])

    def test_create_taropen(self):
        with self.taropen(tmpname, 'x') as tobj:
            tobj.add(self.file_path)
        with self.taropen(tmpname) as tobj:
            names = tobj.getnames()
        self.assertEqual(len(names), 1)
        self.assertIn('spameggs42', names[0])

    def test_create_existing_taropen(self):
        with self.taropen(tmpname, 'x') as tobj:
            tobj.add(self.file_path)
        with self.assertRaises(FileExistsError):
            with self.taropen(tmpname, 'x'):
                pass
        with self.taropen(tmpname) as tobj:
            names = tobj.getnames()
        self.assertEqual(len(names), 1)
        self.assertIn('spameggs42', names[0])

    def test_create_pathlike_name(self):
        with tarfile.open(pathlib.Path(tmpname), self.mode) as tobj:
            self.assertIsInstance(tobj.name, str)
            self.assertEqual(tobj.name, os.path.abspath(tmpname))
            tobj.add(pathlib.Path(self.file_path))
            names = tobj.getnames()
        self.assertEqual(len(names), 1)
        self.assertIn('spameggs42', names[0])
        with self.taropen(tmpname) as tobj:
            names = tobj.getnames()
        self.assertEqual(len(names), 1)
        self.assertIn('spameggs42', names[0])

    def test_create_taropen_pathlike_name(self):
        with self.taropen(pathlib.Path(tmpname), 'x') as tobj:
            self.assertIsInstance(tobj.name, str)
            self.assertEqual(tobj.name, os.path.abspath(tmpname))
            tobj.add(pathlib.Path(self.file_path))
            names = tobj.getnames()
        self.assertEqual(len(names), 1)
        self.assertIn('spameggs42', names[0])
        with self.taropen(tmpname) as tobj:
            names = tobj.getnames()
        self.assertEqual(len(names), 1)
        self.assertIn('spameggs42', names[0])

class GzipCreateTest(GzipTest, CreateTest):
    pass

class Bz2CreateTest(Bz2Test, CreateTest):
    pass

class LzmaCreateTest(LzmaTest, CreateTest):
    pass

class CreateWithXModeTest(CreateTest):
    prefix = 'x'
    test_create_taropen = None
    test_create_existing_taropen = None

@unittest.skipUnless(hasattr(os, 'link'), 'Missing hardlink implementation')
class HardlinkTest(unittest.TestCase):

    def setUp(self):
        self.foo = os.path.join(TEMPDIR, 'foo')
        self.bar = os.path.join(TEMPDIR, 'bar')
        with open(self.foo, 'wb') as fobj:
            fobj.write(b'foo')
        try:
            os.link(self.foo, self.bar)
        except PermissionError as e:
            self.skipTest(('os.link(): %s' % e))
        self.tar = tarfile.open(tmpname, 'w')
        self.tar.add(self.foo)

    def tearDown(self):
        self.tar.close()
        os_helper.unlink(self.foo)
        os_helper.unlink(self.bar)

    def test_add_twice(self):
        tarinfo = self.tar.gettarinfo(self.foo)
        self.assertEqual(tarinfo.type, tarfile.REGTYPE, 'add file as regular failed')

    def test_add_hardlink(self):
        tarinfo = self.tar.gettarinfo(self.bar)
        self.assertEqual(tarinfo.type, tarfile.LNKTYPE, 'add file as hardlink failed')

    def test_dereference_hardlink(self):
        self.tar.dereference = True
        tarinfo = self.tar.gettarinfo(self.bar)
        self.assertEqual(tarinfo.type, tarfile.REGTYPE, 'dereferencing hardlink failed')

class PaxWriteTest(GNUWriteTest):

    def _test(self, name, link=None):
        tarinfo = tarfile.TarInfo(name)
        if link:
            tarinfo.linkname = link
            tarinfo.type = tarfile.LNKTYPE
        tar = tarfile.open(tmpname, 'w', format=tarfile.PAX_FORMAT)
        try:
            tar.addfile(tarinfo)
        finally:
            tar.close()
        tar = tarfile.open(tmpname)
        try:
            if link:
                l = tar.getmembers()[0].linkname
                self.assertEqual(link, l, 'PAX longlink creation failed')
            else:
                n = tar.getmembers()[0].name
                self.assertEqual(name, n, 'PAX longname creation failed')
        finally:
            tar.close()

    def test_pax_global_header(self):
        pax_headers = {'foo': 'bar', 'uid': '0', 'mtime': '1.23', 'test': 'äöü', 'äöü': 'test'}
        tar = tarfile.open(tmpname, 'w', format=tarfile.PAX_FORMAT, pax_headers=pax_headers)
        try:
            tar.addfile(tarfile.TarInfo('test'))
        finally:
            tar.close()
        tar = tarfile.open(tmpname, encoding='iso8859-1')
        try:
            self.assertEqual(tar.pax_headers, pax_headers)
            self.assertEqual(tar.getmembers()[0].pax_headers, pax_headers)
            for (key, val) in tar.pax_headers.items():
                self.assertIsNot(type(key), bytes)
                self.assertIsNot(type(val), bytes)
                if (key in tarfile.PAX_NUMBER_FIELDS):
                    try:
                        tarfile.PAX_NUMBER_FIELDS[key](val)
                    except (TypeError, ValueError):
                        self.fail('unable to convert pax header field')
        finally:
            tar.close()

    def test_pax_extended_header(self):
        pax_headers = {'path': 'foo', 'uid': '123'}
        tar = tarfile.open(tmpname, 'w', format=tarfile.PAX_FORMAT, encoding='iso8859-1')
        try:
            t = tarfile.TarInfo()
            t.name = 'äöü'
            t.uid = (8 ** 8)
            t.pax_headers = pax_headers
            tar.addfile(t)
        finally:
            tar.close()
        tar = tarfile.open(tmpname, encoding='iso8859-1')
        try:
            t = tar.getmembers()[0]
            self.assertEqual(t.pax_headers, pax_headers)
            self.assertEqual(t.name, 'foo')
            self.assertEqual(t.uid, 123)
        finally:
            tar.close()

class UnicodeTest():

    def test_iso8859_1_filename(self):
        self._test_unicode_filename('iso8859-1')

    def test_utf7_filename(self):
        self._test_unicode_filename('utf7')

    def test_utf8_filename(self):
        self._test_unicode_filename('utf-8')

    def _test_unicode_filename(self, encoding):
        tar = tarfile.open(tmpname, 'w', format=self.format, encoding=encoding, errors='strict')
        try:
            name = 'äöü'
            tar.addfile(tarfile.TarInfo(name))
        finally:
            tar.close()
        tar = tarfile.open(tmpname, encoding=encoding)
        try:
            self.assertEqual(tar.getmembers()[0].name, name)
        finally:
            tar.close()

    def test_unicode_filename_error(self):
        tar = tarfile.open(tmpname, 'w', format=self.format, encoding='ascii', errors='strict')
        try:
            tarinfo = tarfile.TarInfo()
            tarinfo.name = 'äöü'
            self.assertRaises(UnicodeError, tar.addfile, tarinfo)
            tarinfo.name = 'foo'
            tarinfo.uname = 'äöü'
            self.assertRaises(UnicodeError, tar.addfile, tarinfo)
        finally:
            tar.close()

    def test_unicode_argument(self):
        tar = tarfile.open(tarname, 'r', encoding='iso8859-1', errors='strict')
        try:
            for t in tar:
                self.assertIs(type(t.name), str)
                self.assertIs(type(t.linkname), str)
                self.assertIs(type(t.uname), str)
                self.assertIs(type(t.gname), str)
        finally:
            tar.close()

    def test_uname_unicode(self):
        t = tarfile.TarInfo('foo')
        t.uname = 'äöü'
        t.gname = 'äöü'
        tar = tarfile.open(tmpname, mode='w', format=self.format, encoding='iso8859-1')
        try:
            tar.addfile(t)
        finally:
            tar.close()
        tar = tarfile.open(tmpname, encoding='iso8859-1')
        try:
            t = tar.getmember('foo')
            self.assertEqual(t.uname, 'äöü')
            self.assertEqual(t.gname, 'äöü')
            if (self.format != tarfile.PAX_FORMAT):
                tar.close()
                tar = tarfile.open(tmpname, encoding='ascii')
                t = tar.getmember('foo')
                self.assertEqual(t.uname, '\udce4\udcf6\udcfc')
                self.assertEqual(t.gname, '\udce4\udcf6\udcfc')
        finally:
            tar.close()

class UstarUnicodeTest(UnicodeTest, unittest.TestCase):
    format = tarfile.USTAR_FORMAT

    def test_unicode_name1(self):
        self._test_ustar_name(('0123456789' * 10))
        self._test_ustar_name((('0123456789' * 10) + '0'), ValueError)
        self._test_ustar_name((('0123456789' * 9) + '01234567ÿ'))
        self._test_ustar_name((('0123456789' * 9) + '012345678ÿ'), ValueError)

    def test_unicode_name2(self):
        self._test_ustar_name((('0123456789' * 9) + '012345ÿÿ'))
        self._test_ustar_name((('0123456789' * 9) + '0123456ÿÿ'), ValueError)

    def test_unicode_longname1(self):
        self._test_ustar_name(((('0123456789' * 15) + '01234/') + ('0123456789' * 10)))
        self._test_ustar_name(((('0123456789' * 15) + '0123/4') + ('0123456789' * 10)), ValueError)
        self._test_ustar_name(((('0123456789' * 15) + '012ÿ/') + ('0123456789' * 10)))
        self._test_ustar_name(((('0123456789' * 15) + '0123ÿ/') + ('0123456789' * 10)), ValueError)

    def test_unicode_longname2(self):
        self._test_ustar_name(((('0123456789' * 15) + '01ÿ/2') + ('0123456789' * 10)), ValueError)
        self._test_ustar_name(((('0123456789' * 15) + '01ÿÿ/') + ('0123456789' * 10)), ValueError)

    def test_unicode_longname3(self):
        self._test_ustar_name(((('0123456789' * 15) + '01ÿÿ/2') + ('0123456789' * 10)), ValueError)
        self._test_ustar_name((((('0123456789' * 15) + '01234/') + ('0123456789' * 9)) + '01234567ÿ'))
        self._test_ustar_name((((('0123456789' * 15) + '01234/') + ('0123456789' * 9)) + '012345678ÿ'), ValueError)

    def test_unicode_longname4(self):
        self._test_ustar_name((((('0123456789' * 15) + '01234/') + ('0123456789' * 9)) + '012345ÿÿ'))
        self._test_ustar_name((((('0123456789' * 15) + '01234/') + ('0123456789' * 9)) + '0123456ÿÿ'), ValueError)

    def _test_ustar_name(self, name, exc=None):
        with tarfile.open(tmpname, 'w', format=self.format, encoding='utf-8') as tar:
            t = tarfile.TarInfo(name)
            if (exc is None):
                tar.addfile(t)
            else:
                self.assertRaises(exc, tar.addfile, t)
        if (exc is None):
            with tarfile.open(tmpname, 'r', encoding='utf-8') as tar:
                for t in tar:
                    self.assertEqual(name, t.name)
                    break

    def test_unicode_link1(self):
        self._test_ustar_link(('0123456789' * 10))
        self._test_ustar_link((('0123456789' * 10) + '0'), ValueError)
        self._test_ustar_link((('0123456789' * 9) + '01234567ÿ'))
        self._test_ustar_link((('0123456789' * 9) + '012345678ÿ'), ValueError)

    def test_unicode_link2(self):
        self._test_ustar_link((('0123456789' * 9) + '012345ÿÿ'))
        self._test_ustar_link((('0123456789' * 9) + '0123456ÿÿ'), ValueError)

    def _test_ustar_link(self, name, exc=None):
        with tarfile.open(tmpname, 'w', format=self.format, encoding='utf-8') as tar:
            t = tarfile.TarInfo('foo')
            t.linkname = name
            if (exc is None):
                tar.addfile(t)
            else:
                self.assertRaises(exc, tar.addfile, t)
        if (exc is None):
            with tarfile.open(tmpname, 'r', encoding='utf-8') as tar:
                for t in tar:
                    self.assertEqual(name, t.linkname)
                    break

class GNUUnicodeTest(UnicodeTest, unittest.TestCase):
    format = tarfile.GNU_FORMAT

    def test_bad_pax_header(self):
        for (encoding, name) in (('utf-8', 'pax/bad-pax-\udce4\udcf6\udcfc'), ('iso8859-1', 'pax/bad-pax-äöü')):
            with tarfile.open(tarname, encoding=encoding, errors='surrogateescape') as tar:
                try:
                    t = tar.getmember(name)
                except KeyError:
                    self.fail('unable to read bad GNU tar pax header')

class PAXUnicodeTest(UnicodeTest, unittest.TestCase):
    format = tarfile.PAX_FORMAT
    test_unicode_filename_error = None

    def test_binary_header(self):
        for (encoding, name) in (('utf-8', 'pax/hdrcharset-\udce4\udcf6\udcfc'), ('iso8859-1', 'pax/hdrcharset-äöü')):
            with tarfile.open(tarname, encoding=encoding, errors='surrogateescape') as tar:
                try:
                    t = tar.getmember(name)
                except KeyError:
                    self.fail('unable to read POSIX.1-2008 binary header')

class AppendTestBase():

    def setUp(self):
        self.tarname = tmpname
        if os.path.exists(self.tarname):
            os_helper.unlink(self.tarname)

    def _create_testtar(self, mode='w:'):
        with tarfile.open(tarname, encoding='iso8859-1') as src:
            t = src.getmember('ustar/regtype')
            t.name = 'foo'
            with src.extractfile(t) as f:
                with tarfile.open(self.tarname, mode) as tar:
                    tar.addfile(t, f)

    def test_append_compressed(self):
        self._create_testtar(('w:' + self.suffix))
        self.assertRaises(tarfile.ReadError, tarfile.open, tmpname, 'a')

class AppendTest(AppendTestBase, unittest.TestCase):
    test_append_compressed = None

    def _add_testfile(self, fileobj=None):
        with tarfile.open(self.tarname, 'a', fileobj=fileobj) as tar:
            tar.addfile(tarfile.TarInfo('bar'))

    def _test(self, names=['bar'], fileobj=None):
        with tarfile.open(self.tarname, fileobj=fileobj) as tar:
            self.assertEqual(tar.getnames(), names)

    def test_non_existing(self):
        self._add_testfile()
        self._test()

    def test_empty(self):
        tarfile.open(self.tarname, 'w:').close()
        self._add_testfile()
        self._test()

    def test_empty_fileobj(self):
        fobj = io.BytesIO((b'\x00' * 1024))
        self._add_testfile(fobj)
        fobj.seek(0)
        self._test(fileobj=fobj)

    def test_fileobj(self):
        self._create_testtar()
        with open(self.tarname, 'rb') as fobj:
            data = fobj.read()
        fobj = io.BytesIO(data)
        self._add_testfile(fobj)
        fobj.seek(0)
        self._test(names=['foo', 'bar'], fileobj=fobj)

    def test_existing(self):
        self._create_testtar()
        self._add_testfile()
        self._test(names=['foo', 'bar'])

    def _test_error(self, data):
        with open(self.tarname, 'wb') as fobj:
            fobj.write(data)
        self.assertRaises(tarfile.ReadError, self._add_testfile)

    def test_null(self):
        self._test_error(b'')

    def test_incomplete(self):
        self._test_error((b'\x00' * 13))

    def test_premature_eof(self):
        data = tarfile.TarInfo('foo').tobuf()
        self._test_error(data)

    def test_trailing_garbage(self):
        data = tarfile.TarInfo('foo').tobuf()
        self._test_error((data + (b'\x00' * 13)))

    def test_invalid(self):
        self._test_error((b'a' * 512))

class GzipAppendTest(GzipTest, AppendTestBase, unittest.TestCase):
    pass

class Bz2AppendTest(Bz2Test, AppendTestBase, unittest.TestCase):
    pass

class LzmaAppendTest(LzmaTest, AppendTestBase, unittest.TestCase):
    pass

class LimitsTest(unittest.TestCase):

    def test_ustar_limits(self):
        tarinfo = tarfile.TarInfo(('0123456789' * 10))
        tarinfo.tobuf(tarfile.USTAR_FORMAT)
        tarinfo = tarfile.TarInfo((('0123456789' * 10) + '0'))
        self.assertRaises(ValueError, tarinfo.tobuf, tarfile.USTAR_FORMAT)
        tarinfo = tarfile.TarInfo((('123/' * 62) + 'longname'))
        tarinfo.tobuf(tarfile.USTAR_FORMAT)
        tarinfo = tarfile.TarInfo((('1234567/' * 31) + 'longname'))
        self.assertRaises(ValueError, tarinfo.tobuf, tarfile.USTAR_FORMAT)
        tarinfo = tarfile.TarInfo((('123/' * 126) + 'longname'))
        self.assertRaises(ValueError, tarinfo.tobuf, tarfile.USTAR_FORMAT)
        tarinfo = tarfile.TarInfo('longlink')
        tarinfo.linkname = (('123/' * 126) + 'longname')
        self.assertRaises(ValueError, tarinfo.tobuf, tarfile.USTAR_FORMAT)
        tarinfo = tarfile.TarInfo('name')
        tarinfo.uid = 2097152
        self.assertRaises(ValueError, tarinfo.tobuf, tarfile.USTAR_FORMAT)

    def test_gnu_limits(self):
        tarinfo = tarfile.TarInfo((('123/' * 126) + 'longname'))
        tarinfo.tobuf(tarfile.GNU_FORMAT)
        tarinfo = tarfile.TarInfo('longlink')
        tarinfo.linkname = (('123/' * 126) + 'longname')
        tarinfo.tobuf(tarfile.GNU_FORMAT)
        tarinfo = tarfile.TarInfo('name')
        tarinfo.uid = 72057594037927936
        self.assertRaises(ValueError, tarinfo.tobuf, tarfile.GNU_FORMAT)

    def test_pax_limits(self):
        tarinfo = tarfile.TarInfo((('123/' * 126) + 'longname'))
        tarinfo.tobuf(tarfile.PAX_FORMAT)
        tarinfo = tarfile.TarInfo('longlink')
        tarinfo.linkname = (('123/' * 126) + 'longname')
        tarinfo.tobuf(tarfile.PAX_FORMAT)
        tarinfo = tarfile.TarInfo('name')
        tarinfo.uid = 72057594037927936
        tarinfo.tobuf(tarfile.PAX_FORMAT)

class MiscTest(unittest.TestCase):

    def test_char_fields(self):
        self.assertEqual(tarfile.stn('foo', 8, 'ascii', 'strict'), b'foo\x00\x00\x00\x00\x00')
        self.assertEqual(tarfile.stn('foobar', 3, 'ascii', 'strict'), b'foo')
        self.assertEqual(tarfile.nts(b'foo\x00\x00\x00\x00\x00', 'ascii', 'strict'), 'foo')
        self.assertEqual(tarfile.nts(b'foo\x00bar\x00', 'ascii', 'strict'), 'foo')

    def test_read_number_fields(self):
        self.assertEqual(tarfile.nti(b'0000001\x00'), 1)
        self.assertEqual(tarfile.nti(b'7777777\x00'), 2097151)
        self.assertEqual(tarfile.nti(b'\x80\x00\x00\x00\x00 \x00\x00'), 2097152)
        self.assertEqual(tarfile.nti(b'\x80\x00\x00\x00\xff\xff\xff\xff'), 4294967295)
        self.assertEqual(tarfile.nti(b'\xff\xff\xff\xff\xff\xff\xff\xff'), (- 1))
        self.assertEqual(tarfile.nti(b'\xff\xff\xff\xff\xff\xff\xff\x9c'), (- 100))
        self.assertEqual(tarfile.nti(b'\xff\x00\x00\x00\x00\x00\x00\x00'), (- 72057594037927936))
        self.assertEqual(tarfile.nti(b'\x00'), 0)
        self.assertEqual(tarfile.nti(b'       \x00'), 0)

    def test_write_number_fields(self):
        self.assertEqual(tarfile.itn(1), b'0000001\x00')
        self.assertEqual(tarfile.itn(2097151), b'7777777\x00')
        self.assertEqual(tarfile.itn(2097152, format=tarfile.GNU_FORMAT), b'\x80\x00\x00\x00\x00 \x00\x00')
        self.assertEqual(tarfile.itn(4294967295, format=tarfile.GNU_FORMAT), b'\x80\x00\x00\x00\xff\xff\xff\xff')
        self.assertEqual(tarfile.itn((- 1), format=tarfile.GNU_FORMAT), b'\xff\xff\xff\xff\xff\xff\xff\xff')
        self.assertEqual(tarfile.itn((- 100), format=tarfile.GNU_FORMAT), b'\xff\xff\xff\xff\xff\xff\xff\x9c')
        self.assertEqual(tarfile.itn((- 72057594037927936), format=tarfile.GNU_FORMAT), b'\xff\x00\x00\x00\x00\x00\x00\x00')
        self.assertEqual(tarfile.itn((- 100.0), format=tarfile.GNU_FORMAT), b'\xff\xff\xff\xff\xff\xff\xff\x9c')
        self.assertEqual(tarfile.itn(((8 ** 12) + 0.0), format=tarfile.GNU_FORMAT), b'\x80\x00\x00\x10\x00\x00\x00\x00')
        self.assertEqual(tarfile.nti(tarfile.itn((- 0.1), format=tarfile.GNU_FORMAT)), 0)

    def test_number_field_limits(self):
        with self.assertRaises(ValueError):
            tarfile.itn((- 1), 8, tarfile.USTAR_FORMAT)
        with self.assertRaises(ValueError):
            tarfile.itn(2097152, 8, tarfile.USTAR_FORMAT)
        with self.assertRaises(ValueError):
            tarfile.itn((- 1099511627777), 6, tarfile.GNU_FORMAT)
        with self.assertRaises(ValueError):
            tarfile.itn(1099511627776, 6, tarfile.GNU_FORMAT)

    def test__all__(self):
        not_exported = {'version', 'grp', 'pwd', 'symlink_exception', 'NUL', 'BLOCKSIZE', 'RECORDSIZE', 'GNU_MAGIC', 'POSIX_MAGIC', 'LENGTH_NAME', 'LENGTH_LINK', 'LENGTH_PREFIX', 'REGTYPE', 'AREGTYPE', 'LNKTYPE', 'SYMTYPE', 'CHRTYPE', 'BLKTYPE', 'DIRTYPE', 'FIFOTYPE', 'CONTTYPE', 'GNUTYPE_LONGNAME', 'GNUTYPE_LONGLINK', 'GNUTYPE_SPARSE', 'XHDTYPE', 'XGLTYPE', 'SOLARIS_XHDTYPE', 'SUPPORTED_TYPES', 'REGULAR_TYPES', 'GNU_TYPES', 'PAX_FIELDS', 'PAX_NAME_FIELDS', 'PAX_NUMBER_FIELDS', 'stn', 'nts', 'nti', 'itn', 'calc_chksums', 'copyfileobj', 'filemode', 'EmptyHeaderError', 'TruncatedHeaderError', 'EOFHeaderError', 'InvalidHeaderError', 'SubsequentHeaderError', 'ExFileObject', 'main'}
        support.check__all__(self, tarfile, not_exported=not_exported)

class CommandLineTest(unittest.TestCase):

    def tarfilecmd(self, *args, **kwargs):
        (rc, out, err) = script_helper.assert_python_ok('-m', 'tarfile', *args, **kwargs)
        return out.replace(os.linesep.encode(), b'\n')

    def tarfilecmd_failure(self, *args):
        return script_helper.assert_python_failure('-m', 'tarfile', *args)

    def make_simple_tarfile(self, tar_name):
        files = [support.findfile('tokenize_tests.txt'), support.findfile('tokenize_tests-no-coding-cookie-and-utf8-bom-sig-only.txt')]
        self.addCleanup(os_helper.unlink, tar_name)
        with tarfile.open(tar_name, 'w') as tf:
            for tardata in files:
                tf.add(tardata, arcname=os.path.basename(tardata))

    def test_bad_use(self):
        (rc, out, err) = self.tarfilecmd_failure()
        self.assertEqual(out, b'')
        self.assertIn(b'usage', err.lower())
        self.assertIn(b'error', err.lower())
        self.assertIn(b'required', err.lower())
        (rc, out, err) = self.tarfilecmd_failure('-l', '')
        self.assertEqual(out, b'')
        self.assertNotEqual(err.strip(), b'')

    def test_test_command(self):
        for tar_name in testtarnames:
            for opt in ('-t', '--test'):
                out = self.tarfilecmd(opt, tar_name)
                self.assertEqual(out, b'')

    def test_test_command_verbose(self):
        for tar_name in testtarnames:
            for opt in ('-v', '--verbose'):
                out = self.tarfilecmd(opt, '-t', tar_name, PYTHONIOENCODING='utf-8')
                self.assertIn(b'is a tar archive.\n', out)

    def test_test_command_invalid_file(self):
        zipname = support.findfile('zipdir.zip')
        (rc, out, err) = self.tarfilecmd_failure('-t', zipname)
        self.assertIn(b' is not a tar archive.', err)
        self.assertEqual(out, b'')
        self.assertEqual(rc, 1)
        for tar_name in testtarnames:
            with self.subTest(tar_name=tar_name):
                with open(tar_name, 'rb') as f:
                    data = f.read()
                try:
                    with open(tmpname, 'wb') as f:
                        f.write(data[:511])
                    (rc, out, err) = self.tarfilecmd_failure('-t', tmpname)
                    self.assertEqual(out, b'')
                    self.assertEqual(rc, 1)
                finally:
                    os_helper.unlink(tmpname)

    def test_list_command(self):
        for tar_name in testtarnames:
            with support.captured_stdout() as t:
                with tarfile.open(tar_name, 'r') as tf:
                    tf.list(verbose=False)
            expected = t.getvalue().encode('ascii', 'backslashreplace')
            for opt in ('-l', '--list'):
                out = self.tarfilecmd(opt, tar_name, PYTHONIOENCODING='ascii')
                self.assertEqual(out, expected)

    def test_list_command_verbose(self):
        for tar_name in testtarnames:
            with support.captured_stdout() as t:
                with tarfile.open(tar_name, 'r') as tf:
                    tf.list(verbose=True)
            expected = t.getvalue().encode('ascii', 'backslashreplace')
            for opt in ('-v', '--verbose'):
                out = self.tarfilecmd(opt, '-l', tar_name, PYTHONIOENCODING='ascii')
                self.assertEqual(out, expected)

    def test_list_command_invalid_file(self):
        zipname = support.findfile('zipdir.zip')
        (rc, out, err) = self.tarfilecmd_failure('-l', zipname)
        self.assertIn(b' is not a tar archive.', err)
        self.assertEqual(out, b'')
        self.assertEqual(rc, 1)

    def test_create_command(self):
        files = [support.findfile('tokenize_tests.txt'), support.findfile('tokenize_tests-no-coding-cookie-and-utf8-bom-sig-only.txt')]
        for opt in ('-c', '--create'):
            try:
                out = self.tarfilecmd(opt, tmpname, *files)
                self.assertEqual(out, b'')
                with tarfile.open(tmpname) as tar:
                    tar.getmembers()
            finally:
                os_helper.unlink(tmpname)

    def test_create_command_verbose(self):
        files = [support.findfile('tokenize_tests.txt'), support.findfile('tokenize_tests-no-coding-cookie-and-utf8-bom-sig-only.txt')]
        for opt in ('-v', '--verbose'):
            try:
                out = self.tarfilecmd(opt, '-c', tmpname, *files, PYTHONIOENCODING='utf-8')
                self.assertIn(b' file created.', out)
                with tarfile.open(tmpname) as tar:
                    tar.getmembers()
            finally:
                os_helper.unlink(tmpname)

    def test_create_command_dotless_filename(self):
        files = [support.findfile('tokenize_tests.txt')]
        try:
            out = self.tarfilecmd('-c', dotlessname, *files)
            self.assertEqual(out, b'')
            with tarfile.open(dotlessname) as tar:
                tar.getmembers()
        finally:
            os_helper.unlink(dotlessname)

    def test_create_command_dot_started_filename(self):
        tar_name = os.path.join(TEMPDIR, '.testtar')
        files = [support.findfile('tokenize_tests.txt')]
        try:
            out = self.tarfilecmd('-c', tar_name, *files)
            self.assertEqual(out, b'')
            with tarfile.open(tar_name) as tar:
                tar.getmembers()
        finally:
            os_helper.unlink(tar_name)

    def test_create_command_compressed(self):
        files = [support.findfile('tokenize_tests.txt'), support.findfile('tokenize_tests-no-coding-cookie-and-utf8-bom-sig-only.txt')]
        for filetype in (GzipTest, Bz2Test, LzmaTest):
            if (not filetype.open):
                continue
            try:
                tar_name = ((tmpname + '.') + filetype.suffix)
                out = self.tarfilecmd('-c', tar_name, *files)
                with filetype.taropen(tar_name) as tar:
                    tar.getmembers()
            finally:
                os_helper.unlink(tar_name)

    def test_extract_command(self):
        self.make_simple_tarfile(tmpname)
        for opt in ('-e', '--extract'):
            try:
                with os_helper.temp_cwd(tarextdir):
                    out = self.tarfilecmd(opt, tmpname)
                self.assertEqual(out, b'')
            finally:
                os_helper.rmtree(tarextdir)

    def test_extract_command_verbose(self):
        self.make_simple_tarfile(tmpname)
        for opt in ('-v', '--verbose'):
            try:
                with os_helper.temp_cwd(tarextdir):
                    out = self.tarfilecmd(opt, '-e', tmpname, PYTHONIOENCODING='utf-8')
                self.assertIn(b' file is extracted.', out)
            finally:
                os_helper.rmtree(tarextdir)

    def test_extract_command_different_directory(self):
        self.make_simple_tarfile(tmpname)
        try:
            with os_helper.temp_cwd(tarextdir):
                out = self.tarfilecmd('-e', tmpname, 'spamdir')
            self.assertEqual(out, b'')
        finally:
            os_helper.rmtree(tarextdir)

    def test_extract_command_invalid_file(self):
        zipname = support.findfile('zipdir.zip')
        with os_helper.temp_cwd(tarextdir):
            (rc, out, err) = self.tarfilecmd_failure('-e', zipname)
        self.assertIn(b' is not a tar archive.', err)
        self.assertEqual(out, b'')
        self.assertEqual(rc, 1)

class ContextManagerTest(unittest.TestCase):

    def test_basic(self):
        with tarfile.open(tarname) as tar:
            self.assertFalse(tar.closed, 'closed inside runtime context')
        self.assertTrue(tar.closed, 'context manager failed')

    def test_closed(self):
        tar = tarfile.open(tarname)
        tar.close()
        with self.assertRaises(OSError):
            with tar:
                pass

    def test_exception(self):
        with self.assertRaises(Exception) as exc:
            with tarfile.open(tarname) as tar:
                raise OSError
        self.assertIsInstance(exc.exception, OSError, 'wrong exception raised in context manager')
        self.assertTrue(tar.closed, 'context manager failed')

    def test_no_eof(self):
        try:
            with tarfile.open(tmpname, 'w') as tar:
                raise Exception
        except:
            pass
        self.assertEqual(os.path.getsize(tmpname), 0, 'context manager wrote an end-of-archive block')
        self.assertTrue(tar.closed, 'context manager failed')

    def test_eof(self):
        with tarfile.open(tmpname, 'w'):
            pass
        self.assertNotEqual(os.path.getsize(tmpname), 0, 'context manager wrote no end-of-archive block')

    def test_fileobj(self):
        with open(tmpname, 'wb') as fobj:
            try:
                with tarfile.open(fileobj=fobj, mode='w') as tar:
                    raise Exception
            except:
                pass
            self.assertFalse(fobj.closed, 'external file object was closed')
            self.assertTrue(tar.closed, 'context manager failed')

@unittest.skipIf(hasattr(os, 'link'), 'requires os.link to be missing')
class LinkEmulationTest(ReadTest, unittest.TestCase):

    def _test_link_extraction(self, name):
        self.tar.extract(name, TEMPDIR)
        with open(os.path.join(TEMPDIR, name), 'rb') as f:
            data = f.read()
        self.assertEqual(sha256sum(data), sha256_regtype)

    @unittest.skipIf(hasattr(os.path, 'islink'), 'Skip emulation - has os.path.islink but not os.link')
    def test_hardlink_extraction1(self):
        self._test_link_extraction('ustar/lnktype')

    @unittest.skipIf(hasattr(os.path, 'islink'), 'Skip emulation - has os.path.islink but not os.link')
    def test_hardlink_extraction2(self):
        self._test_link_extraction('./ustar/linktest2/lnktype')

    @unittest.skipIf(hasattr(os, 'symlink'), 'Skip emulation if symlink exists')
    def test_symlink_extraction1(self):
        self._test_link_extraction('ustar/symtype')

    @unittest.skipIf(hasattr(os, 'symlink'), 'Skip emulation if symlink exists')
    def test_symlink_extraction2(self):
        self._test_link_extraction('./ustar/linktest2/symtype')

class Bz2PartialReadTest(Bz2Test, unittest.TestCase):

    def _test_partial_input(self, mode):

        class MyBytesIO(io.BytesIO):
            hit_eof = False

            def read(self, n):
                if self.hit_eof:
                    raise AssertionError('infinite loop detected in tarfile.open()')
                self.hit_eof = (self.tell() == len(self.getvalue()))
                return super(MyBytesIO, self).read(n)

            def seek(self, *args):
                self.hit_eof = False
                return super(MyBytesIO, self).seek(*args)
        data = bz2.compress(tarfile.TarInfo('foo').tobuf())
        for x in range((len(data) + 1)):
            try:
                tarfile.open(fileobj=MyBytesIO(data[:x]), mode=mode)
            except tarfile.ReadError:
                pass

    def test_partial_input(self):
        self._test_partial_input('r')

    def test_partial_input_bz2(self):
        self._test_partial_input('r:bz2')

def root_is_uid_gid_0():
    try:
        import pwd, grp
    except ImportError:
        return False
    if (pwd.getpwuid(0)[0] != 'root'):
        return False
    if (grp.getgrgid(0)[0] != 'root'):
        return False
    return True

@unittest.skipUnless(hasattr(os, 'chown'), 'missing os.chown')
@unittest.skipUnless(hasattr(os, 'geteuid'), 'missing os.geteuid')
class NumericOwnerTest(unittest.TestCase):

    @staticmethod
    def _make_test_archive(filename_1, dirname_1, filename_2):
        fobj = io.BytesIO(b'content')
        items = [(filename_1, 99, 98, tarfile.REGTYPE, fobj), (dirname_1, 77, 76, tarfile.DIRTYPE, None), (filename_2, 88, 87, tarfile.REGTYPE, fobj)]
        with tarfile.open(tmpname, 'w') as tarfl:
            for (name, uid, gid, typ, contents) in items:
                t = tarfile.TarInfo(name)
                t.uid = uid
                t.gid = gid
                t.uname = 'root'
                t.gname = 'root'
                t.type = typ
                tarfl.addfile(t, contents)
        return tmpname

    @staticmethod
    @contextmanager
    def _setup_test(mock_geteuid):
        mock_geteuid.return_value = 0
        fname = 'numeric-owner-testfile'
        dirname = 'dir'
        filename_1 = fname
        dirname_1 = dirname
        filename_2 = os.path.join(dirname, fname)
        tar_filename = NumericOwnerTest._make_test_archive(filename_1, dirname_1, filename_2)
        with tarfile.open(tar_filename) as tarfl:
            (yield (tarfl, filename_1, dirname_1, filename_2))

    @unittest.mock.patch('os.chown')
    @unittest.mock.patch('os.chmod')
    @unittest.mock.patch('os.geteuid')
    def test_extract_with_numeric_owner(self, mock_geteuid, mock_chmod, mock_chown):
        with self._setup_test(mock_geteuid) as (tarfl, filename_1, _, filename_2):
            tarfl.extract(filename_1, TEMPDIR, numeric_owner=True)
            tarfl.extract(filename_2, TEMPDIR, numeric_owner=True)
        f_filename_1 = os.path.join(TEMPDIR, filename_1)
        f_filename_2 = os.path.join(TEMPDIR, filename_2)
        mock_chown.assert_has_calls([unittest.mock.call(f_filename_1, 99, 98), unittest.mock.call(f_filename_2, 88, 87)], any_order=True)

    @unittest.mock.patch('os.chown')
    @unittest.mock.patch('os.chmod')
    @unittest.mock.patch('os.geteuid')
    def test_extractall_with_numeric_owner(self, mock_geteuid, mock_chmod, mock_chown):
        with self._setup_test(mock_geteuid) as (tarfl, filename_1, dirname_1, filename_2):
            tarfl.extractall(TEMPDIR, numeric_owner=True)
        f_filename_1 = os.path.join(TEMPDIR, filename_1)
        f_dirname_1 = os.path.join(TEMPDIR, dirname_1)
        f_filename_2 = os.path.join(TEMPDIR, filename_2)
        mock_chown.assert_has_calls([unittest.mock.call(f_filename_1, 99, 98), unittest.mock.call(f_dirname_1, 77, 76), unittest.mock.call(f_filename_2, 88, 87)], any_order=True)

    @unittest.skipUnless(root_is_uid_gid_0(), 'uid=0,gid=0 must be named "root"')
    @unittest.mock.patch('os.chown')
    @unittest.mock.patch('os.chmod')
    @unittest.mock.patch('os.geteuid')
    def test_extract_without_numeric_owner(self, mock_geteuid, mock_chmod, mock_chown):
        with self._setup_test(mock_geteuid) as (tarfl, filename_1, _, _):
            tarfl.extract(filename_1, TEMPDIR, numeric_owner=False)
        f_filename_1 = os.path.join(TEMPDIR, filename_1)
        mock_chown.assert_called_with(f_filename_1, 0, 0)

    @unittest.mock.patch('os.geteuid')
    def test_keyword_only(self, mock_geteuid):
        with self._setup_test(mock_geteuid) as (tarfl, filename_1, _, _):
            self.assertRaises(TypeError, tarfl.extract, filename_1, TEMPDIR, False, True)

def setUpModule():
    os_helper.unlink(TEMPDIR)
    os.makedirs(TEMPDIR)
    global testtarnames
    testtarnames = [tarname]
    with open(tarname, 'rb') as fobj:
        data = fobj.read()
    for c in (GzipTest, Bz2Test, LzmaTest):
        if c.open:
            os_helper.unlink(c.tarname)
            testtarnames.append(c.tarname)
            with c.open(c.tarname, 'wb') as tar:
                tar.write(data)

def tearDownModule():
    if os.path.exists(TEMPDIR):
        os_helper.rmtree(TEMPDIR)
if (__name__ == '__main__'):
    unittest.main()
