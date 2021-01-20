
'\nTest harness for the venv module.\n\nCopyright (C) 2011-2012 Vinay Sajip.\nLicensed to the PSF under a contributor agreement.\n'
import ensurepip
import os
import os.path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from test.support import captured_stdout, captured_stderr, requires_zlib, skip_if_broken_multiprocessing_synchronize
from test.support.os_helper import can_symlink, EnvironmentVarGuard, rmtree
import unittest
import venv
from unittest.mock import patch
try:
    import ctypes
except ImportError:
    ctypes = None
requireVenvCreate = unittest.skipUnless(((sys.prefix == sys.base_prefix) or (sys._base_executable != sys.executable)), 'cannot run venv.create from within a venv on this platform')

def check_output(cmd, encoding=None):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding=encoding)
    (out, err) = p.communicate()
    if p.returncode:
        raise subprocess.CalledProcessError(p.returncode, cmd, out, err)
    return (out, err)

class BaseTest(unittest.TestCase):
    'Base class for venv tests.'
    maxDiff = (80 * 50)

    def setUp(self):
        self.env_dir = os.path.realpath(tempfile.mkdtemp())
        if (os.name == 'nt'):
            self.bindir = 'Scripts'
            self.lib = ('Lib',)
            self.include = 'Include'
        else:
            self.bindir = 'bin'
            self.lib = ('lib', ('python%d.%d' % sys.version_info[:2]))
            self.include = 'include'
        executable = sys._base_executable
        self.exe = os.path.split(executable)[(- 1)]
        if ((sys.platform == 'win32') and os.path.lexists(executable) and (not os.path.exists(executable))):
            self.cannot_link_exe = True
        else:
            self.cannot_link_exe = False

    def tearDown(self):
        rmtree(self.env_dir)

    def run_with_capture(self, func, *args, **kwargs):
        with captured_stdout() as output:
            with captured_stderr() as error:
                func(*args, **kwargs)
        return (output.getvalue(), error.getvalue())

    def get_env_file(self, *args):
        return os.path.join(self.env_dir, *args)

    def get_text_file_contents(self, *args, encoding='utf-8'):
        with open(self.get_env_file(*args), 'r', encoding=encoding) as f:
            result = f.read()
        return result

class BasicTest(BaseTest):
    'Test venv module functionality.'

    def isdir(self, *args):
        fn = self.get_env_file(*args)
        self.assertTrue(os.path.isdir(fn))

    def test_defaults(self):
        '\n        Test the create function with default arguments.\n        '
        rmtree(self.env_dir)
        self.run_with_capture(venv.create, self.env_dir)
        self.isdir(self.bindir)
        self.isdir(self.include)
        self.isdir(*self.lib)
        p = self.get_env_file('lib64')
        conditions = ((struct.calcsize('P') == 8) and (os.name == 'posix') and (sys.platform != 'darwin'))
        if conditions:
            self.assertTrue(os.path.islink(p))
        else:
            self.assertFalse(os.path.exists(p))
        data = self.get_text_file_contents('pyvenv.cfg')
        executable = sys._base_executable
        path = os.path.dirname(executable)
        self.assertIn(('home = %s' % path), data)
        fn = self.get_env_file(self.bindir, self.exe)
        if (not os.path.exists(fn)):
            bd = self.get_env_file(self.bindir)
            print(('Contents of %r:' % bd))
            print(('    %r' % os.listdir(bd)))
        self.assertTrue(os.path.exists(fn), ('File %r should exist.' % fn))

    def test_prompt(self):
        env_name = os.path.split(self.env_dir)[1]
        rmtree(self.env_dir)
        builder = venv.EnvBuilder()
        self.run_with_capture(builder.create, self.env_dir)
        context = builder.ensure_directories(self.env_dir)
        data = self.get_text_file_contents('pyvenv.cfg')
        self.assertEqual(context.prompt, ('(%s) ' % env_name))
        self.assertNotIn('prompt = ', data)
        rmtree(self.env_dir)
        builder = venv.EnvBuilder(prompt='My prompt')
        self.run_with_capture(builder.create, self.env_dir)
        context = builder.ensure_directories(self.env_dir)
        data = self.get_text_file_contents('pyvenv.cfg')
        self.assertEqual(context.prompt, '(My prompt) ')
        self.assertIn("prompt = 'My prompt'\n", data)
        rmtree(self.env_dir)
        builder = venv.EnvBuilder(prompt='.')
        cwd = os.path.basename(os.getcwd())
        self.run_with_capture(builder.create, self.env_dir)
        context = builder.ensure_directories(self.env_dir)
        data = self.get_text_file_contents('pyvenv.cfg')
        self.assertEqual(context.prompt, ('(%s) ' % cwd))
        self.assertIn(("prompt = '%s'\n" % cwd), data)

    def test_upgrade_dependencies(self):
        builder = venv.EnvBuilder()
        bin_path = ('Scripts' if (sys.platform == 'win32') else 'bin')
        python_exe = ('python.exe' if (sys.platform == 'win32') else 'python')
        with tempfile.TemporaryDirectory() as fake_env_dir:

            def pip_cmd_checker(cmd):
                self.assertEqual(cmd, [os.path.join(fake_env_dir, bin_path, python_exe), '-m', 'pip', 'install', '--upgrade', 'pip', 'setuptools'])
            fake_context = builder.ensure_directories(fake_env_dir)
            with patch('venv.subprocess.check_call', pip_cmd_checker):
                builder.upgrade_dependencies(fake_context)

    @requireVenvCreate
    def test_prefixes(self):
        '\n        Test that the prefix values are as expected.\n        '
        rmtree(self.env_dir)
        self.run_with_capture(venv.create, self.env_dir)
        envpy = os.path.join(self.env_dir, self.bindir, self.exe)
        cmd = [envpy, '-c', None]
        for (prefix, expected) in (('prefix', self.env_dir), ('exec_prefix', self.env_dir), ('base_prefix', sys.base_prefix), ('base_exec_prefix', sys.base_exec_prefix)):
            cmd[2] = ('import sys; print(sys.%s)' % prefix)
            (out, err) = check_output(cmd)
            self.assertEqual(out.strip(), expected.encode())
    if (sys.platform == 'win32'):
        ENV_SUBDIRS = (('Scripts',), ('Include',), ('Lib',), ('Lib', 'site-packages'))
    else:
        ENV_SUBDIRS = (('bin',), ('include',), ('lib',), ('lib', ('python%d.%d' % sys.version_info[:2])), ('lib', ('python%d.%d' % sys.version_info[:2]), 'site-packages'))

    def create_contents(self, paths, filename):
        '\n        Create some files in the environment which are unrelated\n        to the virtual environment.\n        '
        for subdirs in paths:
            d = os.path.join(self.env_dir, *subdirs)
            os.mkdir(d)
            fn = os.path.join(d, filename)
            with open(fn, 'wb') as f:
                f.write(b'Still here?')

    def test_overwrite_existing(self):
        '\n        Test creating environment in an existing directory.\n        '
        self.create_contents(self.ENV_SUBDIRS, 'foo')
        venv.create(self.env_dir)
        for subdirs in self.ENV_SUBDIRS:
            fn = os.path.join(self.env_dir, *(subdirs + ('foo',)))
            self.assertTrue(os.path.exists(fn))
            with open(fn, 'rb') as f:
                self.assertEqual(f.read(), b'Still here?')
        builder = venv.EnvBuilder(clear=True)
        builder.create(self.env_dir)
        for subdirs in self.ENV_SUBDIRS:
            fn = os.path.join(self.env_dir, *(subdirs + ('foo',)))
            self.assertFalse(os.path.exists(fn))

    def clear_directory(self, path):
        for fn in os.listdir(path):
            fn = os.path.join(path, fn)
            if (os.path.islink(fn) or os.path.isfile(fn)):
                os.remove(fn)
            elif os.path.isdir(fn):
                rmtree(fn)

    def test_unoverwritable_fails(self):
        for paths in self.ENV_SUBDIRS[:3]:
            fn = os.path.join(self.env_dir, *paths)
            with open(fn, 'wb') as f:
                f.write(b'')
            self.assertRaises((ValueError, OSError), venv.create, self.env_dir)
            self.clear_directory(self.env_dir)

    def test_upgrade(self):
        '\n        Test upgrading an existing environment directory.\n        '
        for upgrade in (False, True):
            builder = venv.EnvBuilder(upgrade=upgrade)
            self.run_with_capture(builder.create, self.env_dir)
            self.isdir(self.bindir)
            self.isdir(self.include)
            self.isdir(*self.lib)
            fn = self.get_env_file(self.bindir, self.exe)
            if (not os.path.exists(fn)):
                bd = self.get_env_file(self.bindir)
                print(('Contents of %r:' % bd))
                print(('    %r' % os.listdir(bd)))
            self.assertTrue(os.path.exists(fn), ('File %r should exist.' % fn))

    def test_isolation(self):
        '\n        Test isolation from system site-packages\n        '
        for (ssp, s) in ((True, 'true'), (False, 'false')):
            builder = venv.EnvBuilder(clear=True, system_site_packages=ssp)
            builder.create(self.env_dir)
            data = self.get_text_file_contents('pyvenv.cfg')
            self.assertIn(('include-system-site-packages = %s\n' % s), data)

    @unittest.skipUnless(can_symlink(), 'Needs symlinks')
    def test_symlinking(self):
        '\n        Test symlinking works as expected\n        '
        for usl in (False, True):
            builder = venv.EnvBuilder(clear=True, symlinks=usl)
            builder.create(self.env_dir)
            fn = self.get_env_file(self.bindir, self.exe)
            if usl:
                if self.cannot_link_exe:
                    self.assertFalse(os.path.islink(fn))
                else:
                    self.assertTrue(os.path.islink(fn))

    @requireVenvCreate
    def test_executable(self):
        '\n        Test that the sys.executable value is as expected.\n        '
        rmtree(self.env_dir)
        self.run_with_capture(venv.create, self.env_dir)
        envpy = os.path.join(os.path.realpath(self.env_dir), self.bindir, self.exe)
        (out, err) = check_output([envpy, '-c', 'import sys; print(sys.executable)'])
        self.assertEqual(out.strip(), envpy.encode())

    @unittest.skipUnless(can_symlink(), 'Needs symlinks')
    def test_executable_symlinks(self):
        '\n        Test that the sys.executable value is as expected.\n        '
        rmtree(self.env_dir)
        builder = venv.EnvBuilder(clear=True, symlinks=True)
        builder.create(self.env_dir)
        envpy = os.path.join(os.path.realpath(self.env_dir), self.bindir, self.exe)
        (out, err) = check_output([envpy, '-c', 'import sys; print(sys.executable)'])
        self.assertEqual(out.strip(), envpy.encode())

    @unittest.skipUnless((os.name == 'nt'), 'only relevant on Windows')
    def test_unicode_in_batch_file(self):
        '\n        Test handling of Unicode paths\n        '
        rmtree(self.env_dir)
        env_dir = os.path.join(os.path.realpath(self.env_dir), 'ϼўТλФЙ')
        builder = venv.EnvBuilder(clear=True)
        builder.create(env_dir)
        activate = os.path.join(env_dir, self.bindir, 'activate.bat')
        envpy = os.path.join(env_dir, self.bindir, self.exe)
        (out, err) = check_output([activate, '&', self.exe, '-c', 'print(0)'], encoding='oem')
        self.assertEqual(out.strip(), '0')

    @requireVenvCreate
    def test_multiprocessing(self):
        '\n        Test that the multiprocessing is able to spawn.\n        '
        skip_if_broken_multiprocessing_synchronize()
        rmtree(self.env_dir)
        self.run_with_capture(venv.create, self.env_dir)
        envpy = os.path.join(os.path.realpath(self.env_dir), self.bindir, self.exe)
        (out, err) = check_output([envpy, '-c', 'from multiprocessing import Pool; pool = Pool(1); print(pool.apply_async("Python".lower).get(3)); pool.terminate()'])
        self.assertEqual(out.strip(), 'python'.encode())

    @unittest.skipIf((os.name == 'nt'), 'not relevant on Windows')
    def test_deactivate_with_strict_bash_opts(self):
        bash = shutil.which('bash')
        if (bash is None):
            self.skipTest('bash required for this test')
        rmtree(self.env_dir)
        builder = venv.EnvBuilder(clear=True)
        builder.create(self.env_dir)
        activate = os.path.join(self.env_dir, self.bindir, 'activate')
        test_script = os.path.join(self.env_dir, 'test_strict.sh')
        with open(test_script, 'w') as f:
            f.write(f'''set -euo pipefail
source {activate}
deactivate
''')
        (out, err) = check_output([bash, test_script])
        self.assertEqual(out, ''.encode())
        self.assertEqual(err, ''.encode())

    @unittest.skipUnless((sys.platform == 'darwin'), 'only relevant on macOS')
    def test_macos_env(self):
        rmtree(self.env_dir)
        builder = venv.EnvBuilder()
        builder.create(self.env_dir)
        envpy = os.path.join(os.path.realpath(self.env_dir), self.bindir, self.exe)
        (out, err) = check_output([envpy, '-c', 'import os; print("__PYVENV_LAUNCHER__" in os.environ)'])
        self.assertEqual(out.strip(), 'False'.encode())

@requireVenvCreate
class EnsurePipTest(BaseTest):
    'Test venv module installation of pip.'

    def assert_pip_not_installed(self):
        envpy = os.path.join(os.path.realpath(self.env_dir), self.bindir, self.exe)
        (out, err) = check_output([envpy, '-c', 'try:\n import pip\nexcept ImportError:\n print("OK")'])
        err = err.decode('latin-1')
        self.assertEqual(err, '')
        out = out.decode('latin-1')
        self.assertEqual(out.strip(), 'OK')

    def test_no_pip_by_default(self):
        rmtree(self.env_dir)
        self.run_with_capture(venv.create, self.env_dir)
        self.assert_pip_not_installed()

    def test_explicit_no_pip(self):
        rmtree(self.env_dir)
        self.run_with_capture(venv.create, self.env_dir, with_pip=False)
        self.assert_pip_not_installed()

    def test_devnull(self):
        with open(os.devnull, 'rb') as f:
            self.assertEqual(f.read(), b'')
        self.assertTrue(os.path.exists(os.devnull))

    def do_test_with_pip(self, system_site_packages):
        rmtree(self.env_dir)
        with EnvironmentVarGuard() as envvars:
            envvars['PYTHONWARNINGS'] = 'e'
            envvars['PIP_NO_INSTALL'] = '1'
            with tempfile.TemporaryDirectory() as home_dir:
                envvars['HOME'] = home_dir
                bad_config = '[global]\nno-install=1'
                win_location = ('pip', 'pip.ini')
                posix_location = ('.pip', 'pip.conf')
                for (dirname, fname) in (posix_location,):
                    dirpath = os.path.join(home_dir, dirname)
                    os.mkdir(dirpath)
                    fpath = os.path.join(dirpath, fname)
                    with open(fpath, 'w') as f:
                        f.write(bad_config)
                try:
                    self.run_with_capture(venv.create, self.env_dir, system_site_packages=system_site_packages, with_pip=True)
                except subprocess.CalledProcessError as exc:
                    details = exc.output.decode(errors='replace')
                    msg = '{}\n\n**Subprocess Output**\n{}'
                    self.fail(msg.format(exc, details))
        envpy = os.path.join(os.path.realpath(self.env_dir), self.bindir, self.exe)
        (out, err) = check_output([envpy, '-W', 'ignore::DeprecationWarning', '-I', '-m', 'pip', '--version'])
        err = err.decode('latin-1')
        self.assertEqual(err, '')
        out = out.decode('latin-1')
        expected_version = 'pip {}'.format(ensurepip.version())
        self.assertEqual(out[:len(expected_version)], expected_version)
        env_dir = os.fsencode(self.env_dir).decode('latin-1')
        self.assertIn(env_dir, out)
        with EnvironmentVarGuard() as envvars:
            (out, err) = check_output([envpy, '-W', 'ignore::DeprecationWarning', '-I', '-m', 'ensurepip._uninstall'])
        err = err.decode('latin-1')
        err = re.sub('^(WARNING: )?The directory .* or its parent directory is not owned or is not writable by the current user.*$', '', err, flags=re.MULTILINE)
        self.assertEqual(err.rstrip(), '')
        out = out.decode('latin-1')
        self.assertIn('Successfully uninstalled pip', out)
        self.assertIn('Successfully uninstalled setuptools', out)
        if (not system_site_packages):
            self.assert_pip_not_installed()

    @unittest.skipUnless(ctypes, 'pip requires ctypes')
    @requires_zlib()
    def test_with_pip(self):
        self.do_test_with_pip(False)
        self.do_test_with_pip(True)
if (__name__ == '__main__'):
    unittest.main()
