
'Tests for distutils.command.bdist_wininst.'
import sys
import platform
import unittest
from test.support import run_unittest
from test.support.warnings_helper import check_warnings
from distutils.command.bdist_wininst import bdist_wininst
from distutils.tests import support

@unittest.skipIf(((sys.platform == 'win32') and (platform.machine() == 'ARM64')), 'bdist_wininst is not supported in this install')
@unittest.skipIf(getattr(bdist_wininst, '_unsupported', False), 'bdist_wininst is not supported in this install')
class BuildWinInstTestCase(support.TempdirManager, support.LoggingSilencer, unittest.TestCase):

    def test_get_exe_bytes(self):
        (pkg_pth, dist) = self.create_dist()
        with check_warnings(('', DeprecationWarning)):
            cmd = bdist_wininst(dist)
        cmd.ensure_finalized()
        exe_file = cmd.get_exe_bytes()
        self.assertGreater(len(exe_file), 10)

def test_suite():
    return unittest.makeSuite(BuildWinInstTestCase)
if (__name__ == '__main__'):
    run_unittest(test_suite())
