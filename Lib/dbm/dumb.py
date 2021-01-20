
"A dumb and slow but simple dbm clone.\n\nFor database spam, spam.dir contains the index (a text file),\nspam.bak *may* contain a backup of the index (also a text file),\nwhile spam.dat contains the data (a binary file).\n\nXXX TO DO:\n\n- seems to contain a bug when updating...\n\n- reclaim free space (currently, space once occupied by deleted or expanded\nitems is never reused)\n\n- support concurrent access (currently, if two processes take turns making\nupdates, they can mess up the index)\n\n- support efficient access to large databases (currently, the whole index\nis read when the database is opened, and some updates rewrite the whole index)\n\n- support opening for read-only (flag = 'm')\n\n"
import ast as _ast
import io as _io
import os as _os
import collections.abc
__all__ = ['error', 'open']
_BLOCKSIZE = 512
error = OSError

class _Database(collections.abc.MutableMapping):
    _os = _os
    _io = _io

    def __init__(self, filebasename, mode, flag='c'):
        self._mode = mode
        self._readonly = (flag == 'r')
        self._dirfile = (filebasename + '.dir')
        self._datfile = (filebasename + '.dat')
        self._bakfile = (filebasename + '.bak')
        self._index = None
        self._create(flag)
        self._update(flag)

    def _create(self, flag):
        if (flag == 'n'):
            for filename in (self._datfile, self._bakfile, self._dirfile):
                try:
                    _os.remove(filename)
                except OSError:
                    pass
        try:
            f = _io.open(self._datfile, 'r', encoding='Latin-1')
        except OSError:
            if (flag not in ('c', 'n')):
                raise
            with _io.open(self._datfile, 'w', encoding='Latin-1') as f:
                self._chmod(self._datfile)
        else:
            f.close()

    def _update(self, flag):
        self._modified = False
        self._index = {}
        try:
            f = _io.open(self._dirfile, 'r', encoding='Latin-1')
        except OSError:
            if (flag not in ('c', 'n')):
                raise
            self._modified = True
        else:
            with f:
                for line in f:
                    line = line.rstrip()
                    (key, pos_and_siz_pair) = _ast.literal_eval(line)
                    key = key.encode('Latin-1')
                    self._index[key] = pos_and_siz_pair

    def _commit(self):
        if ((self._index is None) or (not self._modified)):
            return
        try:
            self._os.unlink(self._bakfile)
        except OSError:
            pass
        try:
            self._os.rename(self._dirfile, self._bakfile)
        except OSError:
            pass
        with self._io.open(self._dirfile, 'w', encoding='Latin-1') as f:
            self._chmod(self._dirfile)
            for (key, pos_and_siz_pair) in self._index.items():
                entry = ('%r, %r\n' % (key.decode('Latin-1'), pos_and_siz_pair))
                f.write(entry)
    sync = _commit

    def _verify_open(self):
        if (self._index is None):
            raise error('DBM object has already been closed')

    def __getitem__(self, key):
        if isinstance(key, str):
            key = key.encode('utf-8')
        self._verify_open()
        (pos, siz) = self._index[key]
        with _io.open(self._datfile, 'rb') as f:
            f.seek(pos)
            dat = f.read(siz)
        return dat

    def _addval(self, val):
        with _io.open(self._datfile, 'rb+') as f:
            f.seek(0, 2)
            pos = int(f.tell())
            npos = ((((pos + _BLOCKSIZE) - 1) // _BLOCKSIZE) * _BLOCKSIZE)
            f.write((b'\x00' * (npos - pos)))
            pos = npos
            f.write(val)
        return (pos, len(val))

    def _setval(self, pos, val):
        with _io.open(self._datfile, 'rb+') as f:
            f.seek(pos)
            f.write(val)
        return (pos, len(val))

    def _addkey(self, key, pos_and_siz_pair):
        self._index[key] = pos_and_siz_pair
        with _io.open(self._dirfile, 'a', encoding='Latin-1') as f:
            self._chmod(self._dirfile)
            f.write(('%r, %r\n' % (key.decode('Latin-1'), pos_and_siz_pair)))

    def __setitem__(self, key, val):
        if self._readonly:
            raise error('The database is opened for reading only')
        if isinstance(key, str):
            key = key.encode('utf-8')
        elif (not isinstance(key, (bytes, bytearray))):
            raise TypeError('keys must be bytes or strings')
        if isinstance(val, str):
            val = val.encode('utf-8')
        elif (not isinstance(val, (bytes, bytearray))):
            raise TypeError('values must be bytes or strings')
        self._verify_open()
        self._modified = True
        if (key not in self._index):
            self._addkey(key, self._addval(val))
        else:
            (pos, siz) = self._index[key]
            oldblocks = (((siz + _BLOCKSIZE) - 1) // _BLOCKSIZE)
            newblocks = (((len(val) + _BLOCKSIZE) - 1) // _BLOCKSIZE)
            if (newblocks <= oldblocks):
                self._index[key] = self._setval(pos, val)
            else:
                self._index[key] = self._addval(val)

    def __delitem__(self, key):
        if self._readonly:
            raise error('The database is opened for reading only')
        if isinstance(key, str):
            key = key.encode('utf-8')
        self._verify_open()
        self._modified = True
        del self._index[key]
        self._commit()

    def keys(self):
        try:
            return list(self._index)
        except TypeError:
            raise error('DBM object has already been closed') from None

    def items(self):
        self._verify_open()
        return [(key, self[key]) for key in self._index.keys()]

    def __contains__(self, key):
        if isinstance(key, str):
            key = key.encode('utf-8')
        try:
            return (key in self._index)
        except TypeError:
            if (self._index is None):
                raise error('DBM object has already been closed') from None
            else:
                raise

    def iterkeys(self):
        try:
            return iter(self._index)
        except TypeError:
            raise error('DBM object has already been closed') from None
    __iter__ = iterkeys

    def __len__(self):
        try:
            return len(self._index)
        except TypeError:
            raise error('DBM object has already been closed') from None

    def close(self):
        try:
            self._commit()
        finally:
            self._index = self._datfile = self._dirfile = self._bakfile = None
    __del__ = close

    def _chmod(self, file):
        self._os.chmod(file, self._mode)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

def open(file, flag='c', mode=438):
    "Open the database file, filename, and return corresponding object.\n\n    The flag argument, used to control how the database is opened in the\n    other DBM implementations, supports only the semantics of 'c' and 'n'\n    values.  Other values will default to the semantics of 'c' value:\n    the database will always opened for update and will be created if it\n    does not exist.\n\n    The optional mode argument is the UNIX mode of the file, used only when\n    the database has to be created.  It defaults to octal code 0o666 (and\n    will be modified by the prevailing umask).\n\n    "
    try:
        um = _os.umask(0)
        _os.umask(um)
    except AttributeError:
        pass
    else:
        mode = (mode & (~ um))
    if (flag not in ('r', 'w', 'c', 'n')):
        raise ValueError("Flag must be one of 'r', 'w', 'c', or 'n'")
    return _Database(file, mode, flag=flag)
