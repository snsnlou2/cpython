
'HMAC (Keyed-Hashing for Message Authentication) module.\n\nImplements the HMAC algorithm as described by RFC 2104.\n'
import warnings as _warnings
try:
    import _hashlib as _hashopenssl
except ImportError:
    _hashopenssl = None
    _openssl_md_meths = None
    from _operator import _compare_digest as compare_digest
else:
    _openssl_md_meths = frozenset(_hashopenssl.openssl_md_meth_names)
    compare_digest = _hashopenssl.compare_digest
import hashlib as _hashlib
trans_5C = bytes(((x ^ 92) for x in range(256)))
trans_36 = bytes(((x ^ 54) for x in range(256)))
digest_size = None

class HMAC():
    'RFC 2104 HMAC class.  Also complies with RFC 4231.\n\n    This supports the API for Cryptographic Hash Functions (PEP 247).\n    '
    blocksize = 64
    __slots__ = ('_digest_cons', '_inner', '_outer', 'block_size', 'digest_size')

    def __init__(self, key, msg=None, digestmod=''):
        'Create a new HMAC object.\n\n        key: bytes or buffer, key for the keyed hash object.\n        msg: bytes or buffer, Initial input for the hash or None.\n        digestmod: A hash name suitable for hashlib.new(). *OR*\n                   A hashlib constructor returning a new hash object. *OR*\n                   A module supporting PEP 247.\n\n                   Required as of 3.8, despite its position after the optional\n                   msg argument.  Passing it as a keyword argument is\n                   recommended, though not required for legacy API reasons.\n        '
        if (not isinstance(key, (bytes, bytearray))):
            raise TypeError(('key: expected bytes or bytearray, but got %r' % type(key).__name__))
        if (not digestmod):
            raise TypeError("Missing required parameter 'digestmod'.")
        if callable(digestmod):
            self._digest_cons = digestmod
        elif isinstance(digestmod, str):
            self._digest_cons = (lambda d=b'': _hashlib.new(digestmod, d))
        else:
            self._digest_cons = (lambda d=b'': digestmod.new(d))
        self._outer = self._digest_cons()
        self._inner = self._digest_cons()
        self.digest_size = self._inner.digest_size
        if hasattr(self._inner, 'block_size'):
            blocksize = self._inner.block_size
            if (blocksize < 16):
                _warnings.warn(('block_size of %d seems too small; using our default of %d.' % (blocksize, self.blocksize)), RuntimeWarning, 2)
                blocksize = self.blocksize
        else:
            _warnings.warn(('No block_size attribute on given digest object; Assuming %d.' % self.blocksize), RuntimeWarning, 2)
            blocksize = self.blocksize
        self.block_size = blocksize
        if (len(key) > blocksize):
            key = self._digest_cons(key).digest()
        key = key.ljust(blocksize, b'\x00')
        self._outer.update(key.translate(trans_5C))
        self._inner.update(key.translate(trans_36))
        if (msg is not None):
            self.update(msg)

    @property
    def name(self):
        return ('hmac-' + self._inner.name)

    @property
    def digest_cons(self):
        return self._digest_cons

    @property
    def inner(self):
        return self._inner

    @property
    def outer(self):
        return self._outer

    def update(self, msg):
        'Feed data from msg into this hashing object.'
        self._inner.update(msg)

    def copy(self):
        "Return a separate copy of this hashing object.\n\n        An update to this copy won't affect the original object.\n        "
        other = self.__class__.__new__(self.__class__)
        other._digest_cons = self._digest_cons
        other.digest_size = self.digest_size
        other._inner = self._inner.copy()
        other._outer = self._outer.copy()
        return other

    def _current(self):
        'Return a hash object for the current state.\n\n        To be used only internally with digest() and hexdigest().\n        '
        h = self._outer.copy()
        h.update(self._inner.digest())
        return h

    def digest(self):
        'Return the hash value of this hashing object.\n\n        This returns the hmac value as bytes.  The object is\n        not altered in any way by this function; you can continue\n        updating the object after calling this function.\n        '
        h = self._current()
        return h.digest()

    def hexdigest(self):
        'Like digest(), but returns a string of hexadecimal digits instead.\n        '
        h = self._current()
        return h.hexdigest()

def new(key, msg=None, digestmod=''):
    'Create a new hashing object and return it.\n\n    key: bytes or buffer, The starting key for the hash.\n    msg: bytes or buffer, Initial input for the hash, or None.\n    digestmod: A hash name suitable for hashlib.new(). *OR*\n               A hashlib constructor returning a new hash object. *OR*\n               A module supporting PEP 247.\n\n               Required as of 3.8, despite its position after the optional\n               msg argument.  Passing it as a keyword argument is\n               recommended, though not required for legacy API reasons.\n\n    You can now feed arbitrary bytes into the object using its update()\n    method, and can ask for the hash value at any time by calling its digest()\n    or hexdigest() methods.\n    '
    return HMAC(key, msg, digestmod)

def digest(key, msg, digest):
    'Fast inline implementation of HMAC.\n\n    key: bytes or buffer, The key for the keyed hash object.\n    msg: bytes or buffer, Input message.\n    digest: A hash name suitable for hashlib.new() for best performance. *OR*\n            A hashlib constructor returning a new hash object. *OR*\n            A module supporting PEP 247.\n    '
    if ((_hashopenssl is not None) and isinstance(digest, str) and (digest in _openssl_md_meths)):
        return _hashopenssl.hmac_digest(key, msg, digest)
    if callable(digest):
        digest_cons = digest
    elif isinstance(digest, str):
        digest_cons = (lambda d=b'': _hashlib.new(digest, d))
    else:
        digest_cons = (lambda d=b'': digest.new(d))
    inner = digest_cons()
    outer = digest_cons()
    blocksize = getattr(inner, 'block_size', 64)
    if (len(key) > blocksize):
        key = digest_cons(key).digest()
    key = (key + (b'\x00' * (blocksize - len(key))))
    inner.update(key.translate(trans_36))
    outer.update(key.translate(trans_5C))
    inner.update(msg)
    outer.update(inner.digest())
    return outer.digest()
