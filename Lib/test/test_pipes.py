
import pipes
import os
import string
import unittest
import shutil
from test.support import run_unittest, reap_children
from test.support.os_helper import TESTFN, unlink
if (os.name != 'posix'):
    raise unittest.SkipTest('pipes module only works on posix')
TESTFN2 = (TESTFN + '2')
s_command = ('tr %s %s' % (string.ascii_lowercase, string.ascii_uppercase))

class SimplePipeTests(unittest.TestCase):

    def tearDown(self):
        for f in (TESTFN, TESTFN2):
            unlink(f)

    def testSimplePipe1(self):
        if (shutil.which('tr') is None):
            self.skipTest('tr is not available')
        t = pipes.Template()
        t.append(s_command, pipes.STDIN_STDOUT)
        with t.open(TESTFN, 'w') as f:
            f.write('hello world #1')
        with open(TESTFN) as f:
            self.assertEqual(f.read(), 'HELLO WORLD #1')

    def testSimplePipe2(self):
        if (shutil.which('tr') is None):
            self.skipTest('tr is not available')
        with open(TESTFN, 'w') as f:
            f.write('hello world #2')
        t = pipes.Template()
        t.append((s_command + ' < $IN > $OUT'), pipes.FILEIN_FILEOUT)
        t.copy(TESTFN, TESTFN2)
        with open(TESTFN2) as f:
            self.assertEqual(f.read(), 'HELLO WORLD #2')

    def testSimplePipe3(self):
        if (shutil.which('tr') is None):
            self.skipTest('tr is not available')
        with open(TESTFN, 'w') as f:
            f.write('hello world #2')
        t = pipes.Template()
        t.append((s_command + ' < $IN'), pipes.FILEIN_STDOUT)
        f = t.open(TESTFN, 'r')
        try:
            self.assertEqual(f.read(), 'HELLO WORLD #2')
        finally:
            f.close()

    def testEmptyPipeline1(self):
        d = 'empty pipeline test COPY'
        with open(TESTFN, 'w') as f:
            f.write(d)
        with open(TESTFN2, 'w') as f:
            f.write('')
        t = pipes.Template()
        t.copy(TESTFN, TESTFN2)
        with open(TESTFN2) as f:
            self.assertEqual(f.read(), d)

    def testEmptyPipeline2(self):
        d = 'empty pipeline test READ'
        with open(TESTFN, 'w') as f:
            f.write(d)
        t = pipes.Template()
        f = t.open(TESTFN, 'r')
        try:
            self.assertEqual(f.read(), d)
        finally:
            f.close()

    def testEmptyPipeline3(self):
        d = 'empty pipeline test WRITE'
        t = pipes.Template()
        with t.open(TESTFN, 'w') as f:
            f.write(d)
        with open(TESTFN) as f:
            self.assertEqual(f.read(), d)

    def testRepr(self):
        t = pipes.Template()
        self.assertEqual(repr(t), '<Template instance, steps=[]>')
        t.append('tr a-z A-Z', pipes.STDIN_STDOUT)
        self.assertEqual(repr(t), "<Template instance, steps=[('tr a-z A-Z', '--')]>")

    def testSetDebug(self):
        t = pipes.Template()
        t.debug(False)
        self.assertEqual(t.debugging, False)
        t.debug(True)
        self.assertEqual(t.debugging, True)

    def testReadOpenSink(self):
        t = pipes.Template()
        t.append('boguscmd', pipes.SINK)
        self.assertRaises(ValueError, t.open, 'bogusfile', 'r')

    def testWriteOpenSource(self):
        t = pipes.Template()
        t.prepend('boguscmd', pipes.SOURCE)
        self.assertRaises(ValueError, t.open, 'bogusfile', 'w')

    def testBadAppendOptions(self):
        t = pipes.Template()
        self.assertRaises(TypeError, t.append, 7, pipes.STDIN_STDOUT)
        self.assertRaises(ValueError, t.append, 'boguscmd', 'xx')
        self.assertRaises(ValueError, t.append, 'boguscmd', pipes.SOURCE)
        t = pipes.Template()
        t.append('boguscmd', pipes.SINK)
        self.assertRaises(ValueError, t.append, 'boguscmd', pipes.SINK)
        t = pipes.Template()
        self.assertRaises(ValueError, t.append, 'boguscmd $OUT', pipes.FILEIN_FILEOUT)
        t = pipes.Template()
        self.assertRaises(ValueError, t.append, 'boguscmd', pipes.FILEIN_STDOUT)
        t = pipes.Template()
        self.assertRaises(ValueError, t.append, 'boguscmd $IN', pipes.FILEIN_FILEOUT)
        t = pipes.Template()
        self.assertRaises(ValueError, t.append, 'boguscmd', pipes.STDIN_FILEOUT)

    def testBadPrependOptions(self):
        t = pipes.Template()
        self.assertRaises(TypeError, t.prepend, 7, pipes.STDIN_STDOUT)
        self.assertRaises(ValueError, t.prepend, 'tr a-z A-Z', 'xx')
        self.assertRaises(ValueError, t.prepend, 'boguscmd', pipes.SINK)
        t = pipes.Template()
        t.prepend('boguscmd', pipes.SOURCE)
        self.assertRaises(ValueError, t.prepend, 'boguscmd', pipes.SOURCE)
        t = pipes.Template()
        self.assertRaises(ValueError, t.prepend, 'boguscmd $OUT', pipes.FILEIN_FILEOUT)
        t = pipes.Template()
        self.assertRaises(ValueError, t.prepend, 'boguscmd', pipes.FILEIN_STDOUT)
        t = pipes.Template()
        self.assertRaises(ValueError, t.prepend, 'boguscmd $IN', pipes.FILEIN_FILEOUT)
        t = pipes.Template()
        self.assertRaises(ValueError, t.prepend, 'boguscmd', pipes.STDIN_FILEOUT)

    def testBadOpenMode(self):
        t = pipes.Template()
        self.assertRaises(ValueError, t.open, 'bogusfile', 'x')

    def testClone(self):
        t = pipes.Template()
        t.append('tr a-z A-Z', pipes.STDIN_STDOUT)
        u = t.clone()
        self.assertNotEqual(id(t), id(u))
        self.assertEqual(t.steps, u.steps)
        self.assertNotEqual(id(t.steps), id(u.steps))
        self.assertEqual(t.debugging, u.debugging)

def test_main():
    run_unittest(SimplePipeTests)
    reap_children()
if (__name__ == '__main__'):
    test_main()
