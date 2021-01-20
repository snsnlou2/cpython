
import fnmatch
import functools
import io
import ntpath
import os
import posixpath
import re
import sys
from _collections_abc import Sequence
from errno import EINVAL, ENOENT, ENOTDIR, EBADF, ELOOP
from operator import attrgetter
from stat import S_ISDIR, S_ISLNK, S_ISREG, S_ISSOCK, S_ISBLK, S_ISCHR, S_ISFIFO
from urllib.parse import quote_from_bytes as urlquote_from_bytes
supports_symlinks = True
if (os.name == 'nt'):
    import nt
    if (sys.getwindowsversion()[:2] >= (6, 0)):
        from nt import _getfinalpathname
    else:
        supports_symlinks = False
        _getfinalpathname = None
else:
    nt = None
__all__ = ['PurePath', 'PurePosixPath', 'PureWindowsPath', 'Path', 'PosixPath', 'WindowsPath']
_IGNORED_ERROS = (ENOENT, ENOTDIR, EBADF, ELOOP)
_IGNORED_WINERRORS = (21, 1921)

def _ignore_error(exception):
    return ((getattr(exception, 'errno', None) in _IGNORED_ERROS) or (getattr(exception, 'winerror', None) in _IGNORED_WINERRORS))

def _is_wildcard_pattern(pat):
    return (('*' in pat) or ('?' in pat) or ('[' in pat))

class _Flavour(object):
    'A flavour implements a particular (platform-specific) set of path\n    semantics.'

    def __init__(self):
        self.join = self.sep.join

    def parse_parts(self, parts):
        parsed = []
        sep = self.sep
        altsep = self.altsep
        drv = root = ''
        it = reversed(parts)
        for part in it:
            if (not part):
                continue
            if altsep:
                part = part.replace(altsep, sep)
            (drv, root, rel) = self.splitroot(part)
            if (sep in rel):
                for x in reversed(rel.split(sep)):
                    if (x and (x != '.')):
                        parsed.append(sys.intern(x))
            elif (rel and (rel != '.')):
                parsed.append(sys.intern(rel))
            if (drv or root):
                if (not drv):
                    for part in it:
                        if (not part):
                            continue
                        if altsep:
                            part = part.replace(altsep, sep)
                        drv = self.splitroot(part)[0]
                        if drv:
                            break
                break
        if (drv or root):
            parsed.append((drv + root))
        parsed.reverse()
        return (drv, root, parsed)

    def join_parsed_parts(self, drv, root, parts, drv2, root2, parts2):
        '\n        Join the two paths represented by the respective\n        (drive, root, parts) tuples.  Return a new (drive, root, parts) tuple.\n        '
        if root2:
            if ((not drv2) and drv):
                return (drv, root2, ([(drv + root2)] + parts2[1:]))
        elif drv2:
            if ((drv2 == drv) or (self.casefold(drv2) == self.casefold(drv))):
                return (drv, root, (parts + parts2[1:]))
        else:
            return (drv, root, (parts + parts2))
        return (drv2, root2, parts2)

class _WindowsFlavour(_Flavour):
    sep = '\\'
    altsep = '/'
    has_drv = True
    pathmod = ntpath
    is_supported = (os.name == 'nt')
    drive_letters = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
    ext_namespace_prefix = '\\\\?\\'
    reserved_names = (({'CON', 'PRN', 'AUX', 'NUL'} | {('COM%d' % i) for i in range(1, 10)}) | {('LPT%d' % i) for i in range(1, 10)})

    def splitroot(self, part, sep=sep):
        first = part[0:1]
        second = part[1:2]
        if ((second == sep) and (first == sep)):
            (prefix, part) = self._split_extended_path(part)
            first = part[0:1]
            second = part[1:2]
        else:
            prefix = ''
        third = part[2:3]
        if ((second == sep) and (first == sep) and (third != sep)):
            index = part.find(sep, 2)
            if (index != (- 1)):
                index2 = part.find(sep, (index + 1))
                if (index2 != (index + 1)):
                    if (index2 == (- 1)):
                        index2 = len(part)
                    if prefix:
                        return ((prefix + part[1:index2]), sep, part[(index2 + 1):])
                    else:
                        return (part[:index2], sep, part[(index2 + 1):])
        drv = root = ''
        if ((second == ':') and (first in self.drive_letters)):
            drv = part[:2]
            part = part[2:]
            first = third
        if (first == sep):
            root = first
            part = part.lstrip(sep)
        return ((prefix + drv), root, part)

    def casefold(self, s):
        return s.lower()

    def casefold_parts(self, parts):
        return [p.lower() for p in parts]

    def compile_pattern(self, pattern):
        return re.compile(fnmatch.translate(pattern), re.IGNORECASE).fullmatch

    def resolve(self, path, strict=False):
        s = str(path)
        if (not s):
            return os.getcwd()
        previous_s = None
        if (_getfinalpathname is not None):
            if strict:
                return self._ext_to_normal(_getfinalpathname(s))
            else:
                tail_parts = []
                while True:
                    try:
                        s = self._ext_to_normal(_getfinalpathname(s))
                    except FileNotFoundError:
                        previous_s = s
                        (s, tail) = os.path.split(s)
                        tail_parts.append(tail)
                        if (previous_s == s):
                            return path
                    else:
                        return os.path.join(s, *reversed(tail_parts))
        return None

    def _split_extended_path(self, s, ext_prefix=ext_namespace_prefix):
        prefix = ''
        if s.startswith(ext_prefix):
            prefix = s[:4]
            s = s[4:]
            if s.startswith('UNC\\'):
                prefix += s[:3]
                s = ('\\' + s[3:])
        return (prefix, s)

    def _ext_to_normal(self, s):
        return self._split_extended_path(s)[1]

    def is_reserved(self, parts):
        if (not parts):
            return False
        if parts[0].startswith('\\\\'):
            return False
        return (parts[(- 1)].partition('.')[0].upper() in self.reserved_names)

    def make_uri(self, path):
        drive = path.drive
        if ((len(drive) == 2) and (drive[1] == ':')):
            rest = path.as_posix()[2:].lstrip('/')
            return ('file:///%s/%s' % (drive, urlquote_from_bytes(rest.encode('utf-8'))))
        else:
            return ('file:' + urlquote_from_bytes(path.as_posix().encode('utf-8')))

    def gethomedir(self, username):
        if ('USERPROFILE' in os.environ):
            userhome = os.environ['USERPROFILE']
        elif ('HOMEPATH' in os.environ):
            try:
                drv = os.environ['HOMEDRIVE']
            except KeyError:
                drv = ''
            userhome = (drv + os.environ['HOMEPATH'])
        else:
            raise RuntimeError("Can't determine home directory")
        if username:
            if (os.environ['USERNAME'] != username):
                (drv, root, parts) = self.parse_parts((userhome,))
                if (parts[(- 1)] != os.environ['USERNAME']):
                    raise RuntimeError(("Can't determine home directory for %r" % username))
                parts[(- 1)] = username
                if (drv or root):
                    userhome = ((drv + root) + self.join(parts[1:]))
                else:
                    userhome = self.join(parts)
        return userhome

class _PosixFlavour(_Flavour):
    sep = '/'
    altsep = ''
    has_drv = False
    pathmod = posixpath
    is_supported = (os.name != 'nt')

    def splitroot(self, part, sep=sep):
        if (part and (part[0] == sep)):
            stripped_part = part.lstrip(sep)
            if ((len(part) - len(stripped_part)) == 2):
                return ('', (sep * 2), stripped_part)
            else:
                return ('', sep, stripped_part)
        else:
            return ('', '', part)

    def casefold(self, s):
        return s

    def casefold_parts(self, parts):
        return parts

    def compile_pattern(self, pattern):
        return re.compile(fnmatch.translate(pattern)).fullmatch

    def resolve(self, path, strict=False):
        sep = self.sep
        accessor = path._accessor
        seen = {}

        def _resolve(path, rest):
            if rest.startswith(sep):
                path = ''
            for name in rest.split(sep):
                if ((not name) or (name == '.')):
                    continue
                if (name == '..'):
                    (path, _, _) = path.rpartition(sep)
                    continue
                newpath = ((path + sep) + name)
                if (newpath in seen):
                    path = seen[newpath]
                    if (path is not None):
                        continue
                    raise RuntimeError(('Symlink loop from %r' % newpath))
                try:
                    target = accessor.readlink(newpath)
                except OSError as e:
                    if ((e.errno != EINVAL) and strict):
                        raise
                    path = newpath
                else:
                    seen[newpath] = None
                    path = _resolve(path, target)
                    seen[newpath] = path
            return path
        base = ('' if path.is_absolute() else os.getcwd())
        return (_resolve(base, str(path)) or sep)

    def is_reserved(self, parts):
        return False

    def make_uri(self, path):
        bpath = bytes(path)
        return ('file://' + urlquote_from_bytes(bpath))

    def gethomedir(self, username):
        if (not username):
            try:
                return os.environ['HOME']
            except KeyError:
                import pwd
                return pwd.getpwuid(os.getuid()).pw_dir
        else:
            import pwd
            try:
                return pwd.getpwnam(username).pw_dir
            except KeyError:
                raise RuntimeError(("Can't determine home directory for %r" % username))
_windows_flavour = _WindowsFlavour()
_posix_flavour = _PosixFlavour()

class _Accessor():
    'An accessor implements a particular (system-specific or not) way of\n    accessing paths on the filesystem.'

class _NormalAccessor(_Accessor):
    stat = os.stat
    lstat = os.lstat
    open = os.open
    listdir = os.listdir
    scandir = os.scandir
    chmod = os.chmod
    if hasattr(os, 'lchmod'):
        lchmod = os.lchmod
    else:

        def lchmod(self, pathobj, mode):
            raise NotImplementedError('lchmod() not available on this system')
    mkdir = os.mkdir
    unlink = os.unlink
    if hasattr(os, 'link'):
        link_to = os.link
    else:

        @staticmethod
        def link_to(self, target):
            raise NotImplementedError('os.link() not available on this system')
    rmdir = os.rmdir
    rename = os.rename
    replace = os.replace
    if nt:
        if supports_symlinks:
            symlink = os.symlink
        else:

            def symlink(a, b, target_is_directory):
                raise NotImplementedError('symlink() not available on this system')
    else:

        @staticmethod
        def symlink(a, b, target_is_directory):
            return os.symlink(a, b)
    utime = os.utime

    def readlink(self, path):
        return os.readlink(path)

    def owner(self, path):
        try:
            import pwd
            return pwd.getpwuid(self.stat(path).st_uid).pw_name
        except ImportError:
            raise NotImplementedError('Path.owner() is unsupported on this system')

    def group(self, path):
        try:
            import grp
            return grp.getgrgid(self.stat(path).st_gid).gr_name
        except ImportError:
            raise NotImplementedError('Path.group() is unsupported on this system')
_normal_accessor = _NormalAccessor()

def _make_selector(pattern_parts, flavour):
    pat = pattern_parts[0]
    child_parts = pattern_parts[1:]
    if (pat == '**'):
        cls = _RecursiveWildcardSelector
    elif ('**' in pat):
        raise ValueError("Invalid pattern: '**' can only be an entire path component")
    elif _is_wildcard_pattern(pat):
        cls = _WildcardSelector
    else:
        cls = _PreciseSelector
    return cls(pat, child_parts, flavour)
if hasattr(functools, 'lru_cache'):
    _make_selector = functools.lru_cache()(_make_selector)

class _Selector():
    'A selector matches a specific glob pattern part against the children\n    of a given path.'

    def __init__(self, child_parts, flavour):
        self.child_parts = child_parts
        if child_parts:
            self.successor = _make_selector(child_parts, flavour)
            self.dironly = True
        else:
            self.successor = _TerminatingSelector()
            self.dironly = False

    def select_from(self, parent_path):
        'Iterate over all child paths of `parent_path` matched by this\n        selector.  This can contain parent_path itself.'
        path_cls = type(parent_path)
        is_dir = path_cls.is_dir
        exists = path_cls.exists
        scandir = parent_path._accessor.scandir
        if (not is_dir(parent_path)):
            return iter([])
        return self._select_from(parent_path, is_dir, exists, scandir)

class _TerminatingSelector():

    def _select_from(self, parent_path, is_dir, exists, scandir):
        (yield parent_path)

class _PreciseSelector(_Selector):

    def __init__(self, name, child_parts, flavour):
        self.name = name
        _Selector.__init__(self, child_parts, flavour)

    def _select_from(self, parent_path, is_dir, exists, scandir):
        try:
            path = parent_path._make_child_relpath(self.name)
            if (is_dir if self.dironly else exists)(path):
                for p in self.successor._select_from(path, is_dir, exists, scandir):
                    (yield p)
        except PermissionError:
            return

class _WildcardSelector(_Selector):

    def __init__(self, pat, child_parts, flavour):
        self.match = flavour.compile_pattern(pat)
        _Selector.__init__(self, child_parts, flavour)

    def _select_from(self, parent_path, is_dir, exists, scandir):
        try:
            with scandir(parent_path) as scandir_it:
                entries = list(scandir_it)
            for entry in entries:
                if self.dironly:
                    try:
                        if (not entry.is_dir()):
                            continue
                    except OSError as e:
                        if (not _ignore_error(e)):
                            raise
                        continue
                name = entry.name
                if self.match(name):
                    path = parent_path._make_child_relpath(name)
                    for p in self.successor._select_from(path, is_dir, exists, scandir):
                        (yield p)
        except PermissionError:
            return

class _RecursiveWildcardSelector(_Selector):

    def __init__(self, pat, child_parts, flavour):
        _Selector.__init__(self, child_parts, flavour)

    def _iterate_directories(self, parent_path, is_dir, scandir):
        (yield parent_path)
        try:
            with scandir(parent_path) as scandir_it:
                entries = list(scandir_it)
            for entry in entries:
                entry_is_dir = False
                try:
                    entry_is_dir = entry.is_dir()
                except OSError as e:
                    if (not _ignore_error(e)):
                        raise
                if (entry_is_dir and (not entry.is_symlink())):
                    path = parent_path._make_child_relpath(entry.name)
                    for p in self._iterate_directories(path, is_dir, scandir):
                        (yield p)
        except PermissionError:
            return

    def _select_from(self, parent_path, is_dir, exists, scandir):
        try:
            yielded = set()
            try:
                successor_select = self.successor._select_from
                for starting_point in self._iterate_directories(parent_path, is_dir, scandir):
                    for p in successor_select(starting_point, is_dir, exists, scandir):
                        if (p not in yielded):
                            (yield p)
                            yielded.add(p)
            finally:
                yielded.clear()
        except PermissionError:
            return

class _PathParents(Sequence):
    "This object provides sequence-like access to the logical ancestors\n    of a path.  Don't try to construct it yourself."
    __slots__ = ('_pathcls', '_drv', '_root', '_parts')

    def __init__(self, path):
        self._pathcls = type(path)
        self._drv = path._drv
        self._root = path._root
        self._parts = path._parts

    def __len__(self):
        if (self._drv or self._root):
            return (len(self._parts) - 1)
        else:
            return len(self._parts)

    def __getitem__(self, idx):
        if ((idx < 0) or (idx >= len(self))):
            raise IndexError(idx)
        return self._pathcls._from_parsed_parts(self._drv, self._root, self._parts[:((- idx) - 1)])

    def __repr__(self):
        return '<{}.parents>'.format(self._pathcls.__name__)

class PurePath(object):
    "Base class for manipulating paths without I/O.\n\n    PurePath represents a filesystem path and offers operations which\n    don't imply any actual filesystem I/O.  Depending on your system,\n    instantiating a PurePath will return either a PurePosixPath or a\n    PureWindowsPath object.  You can also instantiate either of these classes\n    directly, regardless of your system.\n    "
    __slots__ = ('_drv', '_root', '_parts', '_str', '_hash', '_pparts', '_cached_cparts')

    def __new__(cls, *args):
        'Construct a PurePath from one or several strings and or existing\n        PurePath objects.  The strings and path objects are combined so as\n        to yield a canonicalized path, which is incorporated into the\n        new PurePath object.\n        '
        if (cls is PurePath):
            cls = (PureWindowsPath if (os.name == 'nt') else PurePosixPath)
        return cls._from_parts(args)

    def __reduce__(self):
        return (self.__class__, tuple(self._parts))

    @classmethod
    def _parse_args(cls, args):
        parts = []
        for a in args:
            if isinstance(a, PurePath):
                parts += a._parts
            else:
                a = os.fspath(a)
                if isinstance(a, str):
                    parts.append(str(a))
                else:
                    raise TypeError(('argument should be a str object or an os.PathLike object returning str, not %r' % type(a)))
        return cls._flavour.parse_parts(parts)

    @classmethod
    def _from_parts(cls, args, init=True):
        self = object.__new__(cls)
        (drv, root, parts) = self._parse_args(args)
        self._drv = drv
        self._root = root
        self._parts = parts
        if init:
            self._init()
        return self

    @classmethod
    def _from_parsed_parts(cls, drv, root, parts, init=True):
        self = object.__new__(cls)
        self._drv = drv
        self._root = root
        self._parts = parts
        if init:
            self._init()
        return self

    @classmethod
    def _format_parsed_parts(cls, drv, root, parts):
        if (drv or root):
            return ((drv + root) + cls._flavour.join(parts[1:]))
        else:
            return cls._flavour.join(parts)

    def _init(self):
        pass

    def _make_child(self, args):
        (drv, root, parts) = self._parse_args(args)
        (drv, root, parts) = self._flavour.join_parsed_parts(self._drv, self._root, self._parts, drv, root, parts)
        return self._from_parsed_parts(drv, root, parts)

    def __str__(self):
        'Return the string representation of the path, suitable for\n        passing to system calls.'
        try:
            return self._str
        except AttributeError:
            self._str = (self._format_parsed_parts(self._drv, self._root, self._parts) or '.')
            return self._str

    def __fspath__(self):
        return str(self)

    def as_posix(self):
        'Return the string representation of the path with forward (/)\n        slashes.'
        f = self._flavour
        return str(self).replace(f.sep, '/')

    def __bytes__(self):
        'Return the bytes representation of the path.  This is only\n        recommended to use under Unix.'
        return os.fsencode(self)

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.as_posix())

    def as_uri(self):
        "Return the path as a 'file' URI."
        if (not self.is_absolute()):
            raise ValueError("relative path can't be expressed as a file URI")
        return self._flavour.make_uri(self)

    @property
    def _cparts(self):
        try:
            return self._cached_cparts
        except AttributeError:
            self._cached_cparts = self._flavour.casefold_parts(self._parts)
            return self._cached_cparts

    def __eq__(self, other):
        if (not isinstance(other, PurePath)):
            return NotImplemented
        return ((self._cparts == other._cparts) and (self._flavour is other._flavour))

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(tuple(self._cparts))
            return self._hash

    def __lt__(self, other):
        if ((not isinstance(other, PurePath)) or (self._flavour is not other._flavour)):
            return NotImplemented
        return (self._cparts < other._cparts)

    def __le__(self, other):
        if ((not isinstance(other, PurePath)) or (self._flavour is not other._flavour)):
            return NotImplemented
        return (self._cparts <= other._cparts)

    def __gt__(self, other):
        if ((not isinstance(other, PurePath)) or (self._flavour is not other._flavour)):
            return NotImplemented
        return (self._cparts > other._cparts)

    def __ge__(self, other):
        if ((not isinstance(other, PurePath)) or (self._flavour is not other._flavour)):
            return NotImplemented
        return (self._cparts >= other._cparts)

    def __class_getitem__(cls, type):
        return cls
    drive = property(attrgetter('_drv'), doc='The drive prefix (letter or UNC path), if any.')
    root = property(attrgetter('_root'), doc='The root of the path, if any.')

    @property
    def anchor(self):
        "The concatenation of the drive and root, or ''."
        anchor = (self._drv + self._root)
        return anchor

    @property
    def name(self):
        'The final path component, if any.'
        parts = self._parts
        if (len(parts) == (1 if (self._drv or self._root) else 0)):
            return ''
        return parts[(- 1)]

    @property
    def suffix(self):
        "\n        The final component's last suffix, if any.\n\n        This includes the leading period. For example: '.txt'\n        "
        name = self.name
        i = name.rfind('.')
        if (0 < i < (len(name) - 1)):
            return name[i:]
        else:
            return ''

    @property
    def suffixes(self):
        "\n        A list of the final component's suffixes, if any.\n\n        These include the leading periods. For example: ['.tar', '.gz']\n        "
        name = self.name
        if name.endswith('.'):
            return []
        name = name.lstrip('.')
        return [('.' + suffix) for suffix in name.split('.')[1:]]

    @property
    def stem(self):
        'The final path component, minus its last suffix.'
        name = self.name
        i = name.rfind('.')
        if (0 < i < (len(name) - 1)):
            return name[:i]
        else:
            return name

    def with_name(self, name):
        'Return a new path with the file name changed.'
        if (not self.name):
            raise ValueError(('%r has an empty name' % (self,)))
        (drv, root, parts) = self._flavour.parse_parts((name,))
        if ((not name) or (name[(- 1)] in [self._flavour.sep, self._flavour.altsep]) or drv or root or (len(parts) != 1)):
            raise ValueError(('Invalid name %r' % name))
        return self._from_parsed_parts(self._drv, self._root, (self._parts[:(- 1)] + [name]))

    def with_stem(self, stem):
        'Return a new path with the stem changed.'
        return self.with_name((stem + self.suffix))

    def with_suffix(self, suffix):
        'Return a new path with the file suffix changed.  If the path\n        has no suffix, add given suffix.  If the given suffix is an empty\n        string, remove the suffix from the path.\n        '
        f = self._flavour
        if ((f.sep in suffix) or (f.altsep and (f.altsep in suffix))):
            raise ValueError(('Invalid suffix %r' % (suffix,)))
        if ((suffix and (not suffix.startswith('.'))) or (suffix == '.')):
            raise ValueError(('Invalid suffix %r' % suffix))
        name = self.name
        if (not name):
            raise ValueError(('%r has an empty name' % (self,)))
        old_suffix = self.suffix
        if (not old_suffix):
            name = (name + suffix)
        else:
            name = (name[:(- len(old_suffix))] + suffix)
        return self._from_parsed_parts(self._drv, self._root, (self._parts[:(- 1)] + [name]))

    def relative_to(self, *other):
        'Return the relative path to another path identified by the passed\n        arguments.  If the operation is not possible (because this is not\n        a subpath of the other path), raise ValueError.\n        '
        if (not other):
            raise TypeError('need at least one argument')
        parts = self._parts
        drv = self._drv
        root = self._root
        if root:
            abs_parts = ([drv, root] + parts[1:])
        else:
            abs_parts = parts
        (to_drv, to_root, to_parts) = self._parse_args(other)
        if to_root:
            to_abs_parts = ([to_drv, to_root] + to_parts[1:])
        else:
            to_abs_parts = to_parts
        n = len(to_abs_parts)
        cf = self._flavour.casefold_parts
        if ((root or drv) if (n == 0) else (cf(abs_parts[:n]) != cf(to_abs_parts))):
            formatted = self._format_parsed_parts(to_drv, to_root, to_parts)
            raise ValueError('{!r} is not in the subpath of {!r} OR one path is relative and the other is absolute.'.format(str(self), str(formatted)))
        return self._from_parsed_parts('', (root if (n == 1) else ''), abs_parts[n:])

    def is_relative_to(self, *other):
        'Return True if the path is relative to another path or False.\n        '
        try:
            self.relative_to(*other)
            return True
        except ValueError:
            return False

    @property
    def parts(self):
        'An object providing sequence-like access to the\n        components in the filesystem path.'
        try:
            return self._pparts
        except AttributeError:
            self._pparts = tuple(self._parts)
            return self._pparts

    def joinpath(self, *args):
        'Combine this path with one or several arguments, and return a\n        new path representing either a subpath (if all arguments are relative\n        paths) or a totally different path (if one of the arguments is\n        anchored).\n        '
        return self._make_child(args)

    def __truediv__(self, key):
        try:
            return self._make_child((key,))
        except TypeError:
            return NotImplemented

    def __rtruediv__(self, key):
        try:
            return self._from_parts(([key] + self._parts))
        except TypeError:
            return NotImplemented

    @property
    def parent(self):
        'The logical parent of the path.'
        drv = self._drv
        root = self._root
        parts = self._parts
        if ((len(parts) == 1) and (drv or root)):
            return self
        return self._from_parsed_parts(drv, root, parts[:(- 1)])

    @property
    def parents(self):
        "A sequence of this path's logical parents."
        return _PathParents(self)

    def is_absolute(self):
        'True if the path is absolute (has both a root and, if applicable,\n        a drive).'
        if (not self._root):
            return False
        return ((not self._flavour.has_drv) or bool(self._drv))

    def is_reserved(self):
        'Return True if the path contains one of the special names reserved\n        by the system, if any.'
        return self._flavour.is_reserved(self._parts)

    def match(self, path_pattern):
        '\n        Return True if this path matches the given pattern.\n        '
        cf = self._flavour.casefold
        path_pattern = cf(path_pattern)
        (drv, root, pat_parts) = self._flavour.parse_parts((path_pattern,))
        if (not pat_parts):
            raise ValueError('empty pattern')
        if (drv and (drv != cf(self._drv))):
            return False
        if (root and (root != cf(self._root))):
            return False
        parts = self._cparts
        if (drv or root):
            if (len(pat_parts) != len(parts)):
                return False
            pat_parts = pat_parts[1:]
        elif (len(pat_parts) > len(parts)):
            return False
        for (part, pat) in zip(reversed(parts), reversed(pat_parts)):
            if (not fnmatch.fnmatchcase(part, pat)):
                return False
        return True
os.PathLike.register(PurePath)

class PurePosixPath(PurePath):
    'PurePath subclass for non-Windows systems.\n\n    On a POSIX system, instantiating a PurePath should return this object.\n    However, you can also instantiate it directly on any system.\n    '
    _flavour = _posix_flavour
    __slots__ = ()

class PureWindowsPath(PurePath):
    'PurePath subclass for Windows systems.\n\n    On a Windows system, instantiating a PurePath should return this object.\n    However, you can also instantiate it directly on any system.\n    '
    _flavour = _windows_flavour
    __slots__ = ()

class Path(PurePath):
    'PurePath subclass that can make system calls.\n\n    Path represents a filesystem path but unlike PurePath, also offers\n    methods to do system calls on path objects. Depending on your system,\n    instantiating a Path will return either a PosixPath or a WindowsPath\n    object. You can also instantiate a PosixPath or WindowsPath directly,\n    but cannot instantiate a WindowsPath on a POSIX system or vice versa.\n    '
    __slots__ = ('_accessor',)

    def __new__(cls, *args, **kwargs):
        if (cls is Path):
            cls = (WindowsPath if (os.name == 'nt') else PosixPath)
        self = cls._from_parts(args, init=False)
        if (not self._flavour.is_supported):
            raise NotImplementedError(('cannot instantiate %r on your system' % (cls.__name__,)))
        self._init()
        return self

    def _init(self, template=None):
        if (template is not None):
            self._accessor = template._accessor
        else:
            self._accessor = _normal_accessor

    def _make_child_relpath(self, part):
        parts = (self._parts + [part])
        return self._from_parsed_parts(self._drv, self._root, parts)

    def __enter__(self):
        return self

    def __exit__(self, t, v, tb):
        pass

    def _opener(self, name, flags, mode=438):
        return self._accessor.open(self, flags, mode)

    def _raw_open(self, flags, mode=511):
        '\n        Open the file pointed by this path and return a file descriptor,\n        as os.open() does.\n        '
        return self._accessor.open(self, flags, mode)

    @classmethod
    def cwd(cls):
        'Return a new path pointing to the current working directory\n        (as returned by os.getcwd()).\n        '
        return cls(os.getcwd())

    @classmethod
    def home(cls):
        "Return a new path pointing to the user's home directory (as\n        returned by os.path.expanduser('~')).\n        "
        return cls(cls()._flavour.gethomedir(None))

    def samefile(self, other_path):
        'Return whether other_path is the same or not as this file\n        (as returned by os.path.samefile()).\n        '
        st = self.stat()
        try:
            other_st = other_path.stat()
        except AttributeError:
            other_st = self._accessor.stat(other_path)
        return os.path.samestat(st, other_st)

    def iterdir(self):
        "Iterate over the files in this directory.  Does not yield any\n        result for the special paths '.' and '..'.\n        "
        for name in self._accessor.listdir(self):
            if (name in {'.', '..'}):
                continue
            (yield self._make_child_relpath(name))

    def glob(self, pattern):
        'Iterate over this subtree and yield all existing files (of any\n        kind, including directories) matching the given relative pattern.\n        '
        sys.audit('pathlib.Path.glob', self, pattern)
        if (not pattern):
            raise ValueError('Unacceptable pattern: {!r}'.format(pattern))
        (drv, root, pattern_parts) = self._flavour.parse_parts((pattern,))
        if (drv or root):
            raise NotImplementedError('Non-relative patterns are unsupported')
        selector = _make_selector(tuple(pattern_parts), self._flavour)
        for p in selector.select_from(self):
            (yield p)

    def rglob(self, pattern):
        'Recursively yield all existing files (of any kind, including\n        directories) matching the given relative pattern, anywhere in\n        this subtree.\n        '
        sys.audit('pathlib.Path.rglob', self, pattern)
        (drv, root, pattern_parts) = self._flavour.parse_parts((pattern,))
        if (drv or root):
            raise NotImplementedError('Non-relative patterns are unsupported')
        selector = _make_selector((('**',) + tuple(pattern_parts)), self._flavour)
        for p in selector.select_from(self):
            (yield p)

    def absolute(self):
        "Return an absolute version of this path.  This function works\n        even if the path doesn't point to anything.\n\n        No normalization is done, i.e. all '.' and '..' will be kept along.\n        Use resolve() to get the canonical path to a file.\n        "
        if self.is_absolute():
            return self
        obj = self._from_parts(([os.getcwd()] + self._parts), init=False)
        obj._init(template=self)
        return obj

    def resolve(self, strict=False):
        '\n        Make the path absolute, resolving all symlinks on the way and also\n        normalizing it (for example turning slashes into backslashes under\n        Windows).\n        '
        s = self._flavour.resolve(self, strict=strict)
        if (s is None):
            self.stat()
            s = str(self.absolute())
        normed = self._flavour.pathmod.normpath(s)
        obj = self._from_parts((normed,), init=False)
        obj._init(template=self)
        return obj

    def stat(self):
        '\n        Return the result of the stat() system call on this path, like\n        os.stat() does.\n        '
        return self._accessor.stat(self)

    def owner(self):
        '\n        Return the login name of the file owner.\n        '
        return self._accessor.owner(self)

    def group(self):
        '\n        Return the group name of the file gid.\n        '
        return self._accessor.group(self)

    def open(self, mode='r', buffering=(- 1), encoding=None, errors=None, newline=None):
        '\n        Open the file pointed by this path and return a file object, as\n        the built-in open() function does.\n        '
        return io.open(self, mode, buffering, encoding, errors, newline, opener=self._opener)

    def read_bytes(self):
        '\n        Open the file in bytes mode, read it, and close the file.\n        '
        with self.open(mode='rb') as f:
            return f.read()

    def read_text(self, encoding=None, errors=None):
        '\n        Open the file in text mode, read it, and close the file.\n        '
        with self.open(mode='r', encoding=encoding, errors=errors) as f:
            return f.read()

    def write_bytes(self, data):
        '\n        Open the file in bytes mode, write to it, and close the file.\n        '
        view = memoryview(data)
        with self.open(mode='wb') as f:
            return f.write(view)

    def write_text(self, data, encoding=None, errors=None):
        '\n        Open the file in text mode, write to it, and close the file.\n        '
        if (not isinstance(data, str)):
            raise TypeError(('data must be str, not %s' % data.__class__.__name__))
        with self.open(mode='w', encoding=encoding, errors=errors) as f:
            return f.write(data)

    def readlink(self):
        '\n        Return the path to which the symbolic link points.\n        '
        path = self._accessor.readlink(self)
        obj = self._from_parts((path,), init=False)
        obj._init(template=self)
        return obj

    def touch(self, mode=438, exist_ok=True):
        "\n        Create this file with the given access mode, if it doesn't exist.\n        "
        if exist_ok:
            try:
                self._accessor.utime(self, None)
            except OSError:
                pass
            else:
                return
        flags = (os.O_CREAT | os.O_WRONLY)
        if (not exist_ok):
            flags |= os.O_EXCL
        fd = self._raw_open(flags, mode)
        os.close(fd)

    def mkdir(self, mode=511, parents=False, exist_ok=False):
        '\n        Create a new directory at this given path.\n        '
        try:
            self._accessor.mkdir(self, mode)
        except FileNotFoundError:
            if ((not parents) or (self.parent == self)):
                raise
            self.parent.mkdir(parents=True, exist_ok=True)
            self.mkdir(mode, parents=False, exist_ok=exist_ok)
        except OSError:
            if ((not exist_ok) or (not self.is_dir())):
                raise

    def chmod(self, mode):
        '\n        Change the permissions of the path, like os.chmod().\n        '
        self._accessor.chmod(self, mode)

    def lchmod(self, mode):
        "\n        Like chmod(), except if the path points to a symlink, the symlink's\n        permissions are changed, rather than its target's.\n        "
        self._accessor.lchmod(self, mode)

    def unlink(self, missing_ok=False):
        '\n        Remove this file or link.\n        If the path is a directory, use rmdir() instead.\n        '
        try:
            self._accessor.unlink(self)
        except FileNotFoundError:
            if (not missing_ok):
                raise

    def rmdir(self):
        '\n        Remove this directory.  The directory must be empty.\n        '
        self._accessor.rmdir(self)

    def lstat(self):
        "\n        Like stat(), except if the path points to a symlink, the symlink's\n        status information is returned, rather than its target's.\n        "
        return self._accessor.lstat(self)

    def link_to(self, target):
        '\n        Create a hard link pointing to a path named target.\n        '
        self._accessor.link_to(self, target)

    def rename(self, target):
        '\n        Rename this path to the given path,\n        and return a new Path instance pointing to the given path.\n        '
        self._accessor.rename(self, target)
        return self.__class__(target)

    def replace(self, target):
        '\n        Rename this path to the given path, clobbering the existing\n        destination if it exists, and return a new Path instance\n        pointing to the given path.\n        '
        self._accessor.replace(self, target)
        return self.__class__(target)

    def symlink_to(self, target, target_is_directory=False):
        "\n        Make this path a symlink pointing to the given path.\n        Note the order of arguments (self, target) is the reverse of os.symlink's.\n        "
        self._accessor.symlink(target, self, target_is_directory)

    def exists(self):
        '\n        Whether this path exists.\n        '
        try:
            self.stat()
        except OSError as e:
            if (not _ignore_error(e)):
                raise
            return False
        except ValueError:
            return False
        return True

    def is_dir(self):
        '\n        Whether this path is a directory.\n        '
        try:
            return S_ISDIR(self.stat().st_mode)
        except OSError as e:
            if (not _ignore_error(e)):
                raise
            return False
        except ValueError:
            return False

    def is_file(self):
        '\n        Whether this path is a regular file (also True for symlinks pointing\n        to regular files).\n        '
        try:
            return S_ISREG(self.stat().st_mode)
        except OSError as e:
            if (not _ignore_error(e)):
                raise
            return False
        except ValueError:
            return False

    def is_mount(self):
        '\n        Check if this path is a POSIX mount point\n        '
        if ((not self.exists()) or (not self.is_dir())):
            return False
        try:
            parent_dev = self.parent.stat().st_dev
        except OSError:
            return False
        dev = self.stat().st_dev
        if (dev != parent_dev):
            return True
        ino = self.stat().st_ino
        parent_ino = self.parent.stat().st_ino
        return (ino == parent_ino)

    def is_symlink(self):
        '\n        Whether this path is a symbolic link.\n        '
        try:
            return S_ISLNK(self.lstat().st_mode)
        except OSError as e:
            if (not _ignore_error(e)):
                raise
            return False
        except ValueError:
            return False

    def is_block_device(self):
        '\n        Whether this path is a block device.\n        '
        try:
            return S_ISBLK(self.stat().st_mode)
        except OSError as e:
            if (not _ignore_error(e)):
                raise
            return False
        except ValueError:
            return False

    def is_char_device(self):
        '\n        Whether this path is a character device.\n        '
        try:
            return S_ISCHR(self.stat().st_mode)
        except OSError as e:
            if (not _ignore_error(e)):
                raise
            return False
        except ValueError:
            return False

    def is_fifo(self):
        '\n        Whether this path is a FIFO.\n        '
        try:
            return S_ISFIFO(self.stat().st_mode)
        except OSError as e:
            if (not _ignore_error(e)):
                raise
            return False
        except ValueError:
            return False

    def is_socket(self):
        '\n        Whether this path is a socket.\n        '
        try:
            return S_ISSOCK(self.stat().st_mode)
        except OSError as e:
            if (not _ignore_error(e)):
                raise
            return False
        except ValueError:
            return False

    def expanduser(self):
        ' Return a new path with expanded ~ and ~user constructs\n        (as returned by os.path.expanduser)\n        '
        if ((not (self._drv or self._root)) and self._parts and (self._parts[0][:1] == '~')):
            homedir = self._flavour.gethomedir(self._parts[0][1:])
            return self._from_parts(([homedir] + self._parts[1:]))
        return self

class PosixPath(Path, PurePosixPath):
    'Path subclass for non-Windows systems.\n\n    On a POSIX system, instantiating a Path should return this object.\n    '
    __slots__ = ()

class WindowsPath(Path, PureWindowsPath):
    'Path subclass for Windows systems.\n\n    On a Windows system, instantiating a Path should return this object.\n    '
    __slots__ = ()

    def is_mount(self):
        raise NotImplementedError('Path.is_mount() is unsupported on this system')
