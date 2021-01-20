
import os
import signal
import subprocess
import sys
import unittest
from test import support
from test.support import script_helper

@unittest.skipUnless((os.name == 'posix'), 'only supported on Unix')
class EINTRTests(unittest.TestCase):

    @unittest.skipUnless(hasattr(signal, 'setitimer'), 'requires setitimer()')
    def test_all(self):
        tester = support.findfile('eintr_tester.py', subdir='eintrdata')
        args = ['-u', tester, '-v']
        if support.verbose:
            print()
            print('--- run eintr_tester.py ---', flush=True)
            args = [sys.executable, '-E', '-X', 'faulthandler', *args]
            proc = subprocess.run(args)
            print(f'--- eintr_tester.py completed: exit code {proc.returncode} ---', flush=True)
            if proc.returncode:
                self.fail('eintr_tester.py failed')
        else:
            script_helper.assert_python_ok('-u', tester, '-v')
if (__name__ == '__main__'):
    unittest.main()
