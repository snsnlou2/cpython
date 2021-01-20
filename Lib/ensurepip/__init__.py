
import os
import os.path
import sys
import runpy
import tempfile
from importlib import resources
from . import _bundled
__all__ = ['version', 'bootstrap']
_SETUPTOOLS_VERSION = '47.1.0'
_PIP_VERSION = '20.1.1'
_PROJECTS = [('setuptools', _SETUPTOOLS_VERSION, 'py3'), ('pip', _PIP_VERSION, 'py2.py3')]

def _run_pip(args, additional_paths=None):
    if (additional_paths is not None):
        sys.path = (additional_paths + sys.path)
    backup_argv = sys.argv[:]
    sys.argv[1:] = args
    try:
        runpy.run_module('pip', run_name='__main__', alter_sys=True)
    except SystemExit as exc:
        return exc.code
    finally:
        sys.argv[:] = backup_argv
    raise SystemError('pip did not exit, this should never happen')

def version():
    '\n    Returns a string specifying the bundled version of pip.\n    '
    return _PIP_VERSION

def _disable_pip_configuration_settings():
    keys_to_remove = [k for k in os.environ if k.startswith('PIP_')]
    for k in keys_to_remove:
        del os.environ[k]
    os.environ['PIP_CONFIG_FILE'] = os.devnull

def bootstrap(*, root=None, upgrade=False, user=False, altinstall=False, default_pip=False, verbosity=0):
    '\n    Bootstrap pip into the current Python installation (or the given root\n    directory).\n\n    Note that calling this function will alter both sys.path and os.environ.\n    '
    _bootstrap(root=root, upgrade=upgrade, user=user, altinstall=altinstall, default_pip=default_pip, verbosity=verbosity)

def _bootstrap(*, root=None, upgrade=False, user=False, altinstall=False, default_pip=False, verbosity=0):
    '\n    Bootstrap pip into the current Python installation (or the given root\n    directory). Returns pip command status code.\n\n    Note that calling this function will alter both sys.path and os.environ.\n    '
    if (altinstall and default_pip):
        raise ValueError('Cannot use altinstall and default_pip together')
    sys.audit('ensurepip.bootstrap', root)
    _disable_pip_configuration_settings()
    if altinstall:
        os.environ['ENSUREPIP_OPTIONS'] = 'altinstall'
    elif (not default_pip):
        os.environ['ENSUREPIP_OPTIONS'] = 'install'
    with tempfile.TemporaryDirectory() as tmpdir:
        additional_paths = []
        for (project, version, py_tag) in _PROJECTS:
            wheel_name = '{}-{}-{}-none-any.whl'.format(project, version, py_tag)
            whl = resources.read_binary(_bundled, wheel_name)
            with open(os.path.join(tmpdir, wheel_name), 'wb') as fp:
                fp.write(whl)
            additional_paths.append(os.path.join(tmpdir, wheel_name))
        args = ['install', '--no-cache-dir', '--no-index', '--find-links', tmpdir]
        if root:
            args += ['--root', root]
        if upgrade:
            args += ['--upgrade']
        if user:
            args += ['--user']
        if verbosity:
            args += [('-' + ('v' * verbosity))]
        return _run_pip((args + [p[0] for p in _PROJECTS]), additional_paths)

def _uninstall_helper(*, verbosity=0):
    'Helper to support a clean default uninstall process on Windows\n\n    Note that calling this function may alter os.environ.\n    '
    try:
        import pip
    except ImportError:
        return
    if (pip.__version__ != _PIP_VERSION):
        msg = 'ensurepip will only uninstall a matching version ({!r} installed, {!r} bundled)'
        print(msg.format(pip.__version__, _PIP_VERSION), file=sys.stderr)
        return
    _disable_pip_configuration_settings()
    args = ['uninstall', '-y', '--disable-pip-version-check']
    if verbosity:
        args += [('-' + ('v' * verbosity))]
    return _run_pip((args + [p[0] for p in reversed(_PROJECTS)]))

def _main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(prog='python -m ensurepip')
    parser.add_argument('--version', action='version', version='pip {}'.format(version()), help='Show the version of pip that is bundled with this Python.')
    parser.add_argument('-v', '--verbose', action='count', default=0, dest='verbosity', help='Give more output. Option is additive, and can be used up to 3 times.')
    parser.add_argument('-U', '--upgrade', action='store_true', default=False, help='Upgrade pip and dependencies, even if already installed.')
    parser.add_argument('--user', action='store_true', default=False, help='Install using the user scheme.')
    parser.add_argument('--root', default=None, help='Install everything relative to this alternate root directory.')
    parser.add_argument('--altinstall', action='store_true', default=False, help='Make an alternate install, installing only the X.Y versioned scripts (Default: pipX, pipX.Y, easy_install-X.Y).')
    parser.add_argument('--default-pip', action='store_true', default=False, help='Make a default pip install, installing the unqualified pip and easy_install in addition to the versioned scripts.')
    args = parser.parse_args(argv)
    return _bootstrap(root=args.root, upgrade=args.upgrade, user=args.user, verbosity=args.verbosity, altinstall=args.altinstall, default_pip=args.default_pip)
