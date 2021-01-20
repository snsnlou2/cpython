
'This module provides some more Pythonic support for SSL.\n\nObject types:\n\n  SSLSocket -- subtype of socket.socket which does SSL over the socket\n\nExceptions:\n\n  SSLError -- exception raised for I/O errors\n\nFunctions:\n\n  cert_time_to_seconds -- convert time string used for certificate\n                          notBefore and notAfter functions to integer\n                          seconds past the Epoch (the time values\n                          returned from time.time())\n\n  fetch_server_certificate (HOST, PORT) -- fetch the certificate provided\n                          by the server running on HOST at port PORT.  No\n                          validation of the certificate is performed.\n\nInteger constants:\n\nSSL_ERROR_ZERO_RETURN\nSSL_ERROR_WANT_READ\nSSL_ERROR_WANT_WRITE\nSSL_ERROR_WANT_X509_LOOKUP\nSSL_ERROR_SYSCALL\nSSL_ERROR_SSL\nSSL_ERROR_WANT_CONNECT\n\nSSL_ERROR_EOF\nSSL_ERROR_INVALID_ERROR_CODE\n\nThe following group define certificate requirements that one side is\nallowing/requiring from the other side:\n\nCERT_NONE - no certificates from the other side are required (or will\n            be looked at if provided)\nCERT_OPTIONAL - certificates are not required, but if provided will be\n                validated, and if validation fails, the connection will\n                also fail\nCERT_REQUIRED - certificates are required, and will be validated, and\n                if validation fails, the connection will also fail\n\nThe following constants identify various SSL protocol variants:\n\nPROTOCOL_SSLv2\nPROTOCOL_SSLv3\nPROTOCOL_SSLv23\nPROTOCOL_TLS\nPROTOCOL_TLS_CLIENT\nPROTOCOL_TLS_SERVER\nPROTOCOL_TLSv1\nPROTOCOL_TLSv1_1\nPROTOCOL_TLSv1_2\n\nThe following constants identify various SSL alert message descriptions as per\nhttp://www.iana.org/assignments/tls-parameters/tls-parameters.xml#tls-parameters-6\n\nALERT_DESCRIPTION_CLOSE_NOTIFY\nALERT_DESCRIPTION_UNEXPECTED_MESSAGE\nALERT_DESCRIPTION_BAD_RECORD_MAC\nALERT_DESCRIPTION_RECORD_OVERFLOW\nALERT_DESCRIPTION_DECOMPRESSION_FAILURE\nALERT_DESCRIPTION_HANDSHAKE_FAILURE\nALERT_DESCRIPTION_BAD_CERTIFICATE\nALERT_DESCRIPTION_UNSUPPORTED_CERTIFICATE\nALERT_DESCRIPTION_CERTIFICATE_REVOKED\nALERT_DESCRIPTION_CERTIFICATE_EXPIRED\nALERT_DESCRIPTION_CERTIFICATE_UNKNOWN\nALERT_DESCRIPTION_ILLEGAL_PARAMETER\nALERT_DESCRIPTION_UNKNOWN_CA\nALERT_DESCRIPTION_ACCESS_DENIED\nALERT_DESCRIPTION_DECODE_ERROR\nALERT_DESCRIPTION_DECRYPT_ERROR\nALERT_DESCRIPTION_PROTOCOL_VERSION\nALERT_DESCRIPTION_INSUFFICIENT_SECURITY\nALERT_DESCRIPTION_INTERNAL_ERROR\nALERT_DESCRIPTION_USER_CANCELLED\nALERT_DESCRIPTION_NO_RENEGOTIATION\nALERT_DESCRIPTION_UNSUPPORTED_EXTENSION\nALERT_DESCRIPTION_CERTIFICATE_UNOBTAINABLE\nALERT_DESCRIPTION_UNRECOGNIZED_NAME\nALERT_DESCRIPTION_BAD_CERTIFICATE_STATUS_RESPONSE\nALERT_DESCRIPTION_BAD_CERTIFICATE_HASH_VALUE\nALERT_DESCRIPTION_UNKNOWN_PSK_IDENTITY\n'
import sys
import os
from collections import namedtuple
from enum import Enum as _Enum, IntEnum as _IntEnum, IntFlag as _IntFlag
import _ssl
from _ssl import OPENSSL_VERSION_NUMBER, OPENSSL_VERSION_INFO, OPENSSL_VERSION
from _ssl import _SSLContext, MemoryBIO, SSLSession
from _ssl import SSLError, SSLZeroReturnError, SSLWantReadError, SSLWantWriteError, SSLSyscallError, SSLEOFError, SSLCertVerificationError
from _ssl import txt2obj as _txt2obj, nid2obj as _nid2obj
from _ssl import RAND_status, RAND_add, RAND_bytes, RAND_pseudo_bytes
try:
    from _ssl import RAND_egd
except ImportError:
    pass
from _ssl import HAS_SNI, HAS_ECDH, HAS_NPN, HAS_ALPN, HAS_SSLv2, HAS_SSLv3, HAS_TLSv1, HAS_TLSv1_1, HAS_TLSv1_2, HAS_TLSv1_3
from _ssl import _DEFAULT_CIPHERS, _OPENSSL_API_VERSION
_IntEnum._convert_('_SSLMethod', __name__, (lambda name: (name.startswith('PROTOCOL_') and (name != 'PROTOCOL_SSLv23'))), source=_ssl)
_IntFlag._convert_('Options', __name__, (lambda name: name.startswith('OP_')), source=_ssl)
_IntEnum._convert_('AlertDescription', __name__, (lambda name: name.startswith('ALERT_DESCRIPTION_')), source=_ssl)
_IntEnum._convert_('SSLErrorNumber', __name__, (lambda name: name.startswith('SSL_ERROR_')), source=_ssl)
_IntFlag._convert_('VerifyFlags', __name__, (lambda name: name.startswith('VERIFY_')), source=_ssl)
_IntEnum._convert_('VerifyMode', __name__, (lambda name: name.startswith('CERT_')), source=_ssl)
PROTOCOL_SSLv23 = _SSLMethod.PROTOCOL_SSLv23 = _SSLMethod.PROTOCOL_TLS
_PROTOCOL_NAMES = {value: name for (name, value) in _SSLMethod.__members__.items()}
_SSLv2_IF_EXISTS = getattr(_SSLMethod, 'PROTOCOL_SSLv2', None)

class TLSVersion(_IntEnum):
    MINIMUM_SUPPORTED = _ssl.PROTO_MINIMUM_SUPPORTED
    SSLv3 = _ssl.PROTO_SSLv3
    TLSv1 = _ssl.PROTO_TLSv1
    TLSv1_1 = _ssl.PROTO_TLSv1_1
    TLSv1_2 = _ssl.PROTO_TLSv1_2
    TLSv1_3 = _ssl.PROTO_TLSv1_3
    MAXIMUM_SUPPORTED = _ssl.PROTO_MAXIMUM_SUPPORTED

class _TLSContentType(_IntEnum):
    'Content types (record layer)\n\n    See RFC 8446, section B.1\n    '
    CHANGE_CIPHER_SPEC = 20
    ALERT = 21
    HANDSHAKE = 22
    APPLICATION_DATA = 23
    HEADER = 256
    INNER_CONTENT_TYPE = 257

class _TLSAlertType(_IntEnum):
    'Alert types for TLSContentType.ALERT messages\n\n    See RFC 8466, section B.2\n    '
    CLOSE_NOTIFY = 0
    UNEXPECTED_MESSAGE = 10
    BAD_RECORD_MAC = 20
    DECRYPTION_FAILED = 21
    RECORD_OVERFLOW = 22
    DECOMPRESSION_FAILURE = 30
    HANDSHAKE_FAILURE = 40
    NO_CERTIFICATE = 41
    BAD_CERTIFICATE = 42
    UNSUPPORTED_CERTIFICATE = 43
    CERTIFICATE_REVOKED = 44
    CERTIFICATE_EXPIRED = 45
    CERTIFICATE_UNKNOWN = 46
    ILLEGAL_PARAMETER = 47
    UNKNOWN_CA = 48
    ACCESS_DENIED = 49
    DECODE_ERROR = 50
    DECRYPT_ERROR = 51
    EXPORT_RESTRICTION = 60
    PROTOCOL_VERSION = 70
    INSUFFICIENT_SECURITY = 71
    INTERNAL_ERROR = 80
    INAPPROPRIATE_FALLBACK = 86
    USER_CANCELED = 90
    NO_RENEGOTIATION = 100
    MISSING_EXTENSION = 109
    UNSUPPORTED_EXTENSION = 110
    CERTIFICATE_UNOBTAINABLE = 111
    UNRECOGNIZED_NAME = 112
    BAD_CERTIFICATE_STATUS_RESPONSE = 113
    BAD_CERTIFICATE_HASH_VALUE = 114
    UNKNOWN_PSK_IDENTITY = 115
    CERTIFICATE_REQUIRED = 116
    NO_APPLICATION_PROTOCOL = 120

class _TLSMessageType(_IntEnum):
    'Message types (handshake protocol)\n\n    See RFC 8446, section B.3\n    '
    HELLO_REQUEST = 0
    CLIENT_HELLO = 1
    SERVER_HELLO = 2
    HELLO_VERIFY_REQUEST = 3
    NEWSESSION_TICKET = 4
    END_OF_EARLY_DATA = 5
    HELLO_RETRY_REQUEST = 6
    ENCRYPTED_EXTENSIONS = 8
    CERTIFICATE = 11
    SERVER_KEY_EXCHANGE = 12
    CERTIFICATE_REQUEST = 13
    SERVER_DONE = 14
    CERTIFICATE_VERIFY = 15
    CLIENT_KEY_EXCHANGE = 16
    FINISHED = 20
    CERTIFICATE_URL = 21
    CERTIFICATE_STATUS = 22
    SUPPLEMENTAL_DATA = 23
    KEY_UPDATE = 24
    NEXT_PROTO = 67
    MESSAGE_HASH = 254
    CHANGE_CIPHER_SPEC = 257
if (sys.platform == 'win32'):
    from _ssl import enum_certificates, enum_crls
from socket import socket, SOCK_STREAM, create_connection
from socket import SOL_SOCKET, SO_TYPE
import socket as _socket
import base64
import errno
import warnings
socket_error = OSError
CHANNEL_BINDING_TYPES = ['tls-unique']
HAS_NEVER_CHECK_COMMON_NAME = hasattr(_ssl, 'HOSTFLAG_NEVER_CHECK_SUBJECT')
_RESTRICTED_SERVER_CIPHERS = _DEFAULT_CIPHERS
CertificateError = SSLCertVerificationError

def _dnsname_match(dn, hostname):
    "Matching according to RFC 6125, section 6.4.3\n\n    - Hostnames are compared lower case.\n    - For IDNA, both dn and hostname must be encoded as IDN A-label (ACE).\n    - Partial wildcards like 'www*.example.org', multiple wildcards, sole\n      wildcard or wildcards in labels other then the left-most label are not\n      supported and a CertificateError is raised.\n    - A wildcard must match at least one character.\n    "
    if (not dn):
        return False
    wildcards = dn.count('*')
    if (not wildcards):
        return (dn.lower() == hostname.lower())
    if (wildcards > 1):
        raise CertificateError('too many wildcards in certificate DNS name: {!r}.'.format(dn))
    (dn_leftmost, sep, dn_remainder) = dn.partition('.')
    if ('*' in dn_remainder):
        raise CertificateError('wildcard can only be present in the leftmost label: {!r}.'.format(dn))
    if (not sep):
        raise CertificateError('sole wildcard without additional labels are not support: {!r}.'.format(dn))
    if (dn_leftmost != '*'):
        raise CertificateError('partial wildcards in leftmost label are not supported: {!r}.'.format(dn))
    (hostname_leftmost, sep, hostname_remainder) = hostname.partition('.')
    if ((not hostname_leftmost) or (not sep)):
        return False
    return (dn_remainder.lower() == hostname_remainder.lower())

def _inet_paton(ipname):
    'Try to convert an IP address to packed binary form\n\n    Supports IPv4 addresses on all platforms and IPv6 on platforms with IPv6\n    support.\n    '
    try:
        addr = _socket.inet_aton(ipname)
    except OSError:
        pass
    else:
        if (_socket.inet_ntoa(addr) == ipname):
            return addr
        else:
            raise ValueError('{!r} is not a quad-dotted IPv4 address.'.format(ipname))
    try:
        return _socket.inet_pton(_socket.AF_INET6, ipname)
    except OSError:
        raise ValueError('{!r} is neither an IPv4 nor an IP6 address.'.format(ipname))
    except AttributeError:
        pass
    raise ValueError('{!r} is not an IPv4 address.'.format(ipname))

def _ipaddress_match(cert_ipaddress, host_ip):
    'Exact matching of IP addresses.\n\n    RFC 6125 explicitly doesn\'t define an algorithm for this\n    (section 1.7.2 - "Out of Scope").\n    '
    ip = _inet_paton(cert_ipaddress.rstrip())
    return (ip == host_ip)

def match_hostname(cert, hostname):
    'Verify that *cert* (in decoded format as returned by\n    SSLSocket.getpeercert()) matches the *hostname*.  RFC 2818 and RFC 6125\n    rules are followed.\n\n    The function matches IP addresses rather than dNSNames if hostname is a\n    valid ipaddress string. IPv4 addresses are supported on all platforms.\n    IPv6 addresses are supported on platforms with IPv6 support (AF_INET6\n    and inet_pton).\n\n    CertificateError is raised on failure. On success, the function\n    returns nothing.\n    '
    if (not cert):
        raise ValueError('empty or no certificate, match_hostname needs a SSL socket or SSL context with either CERT_OPTIONAL or CERT_REQUIRED')
    try:
        host_ip = _inet_paton(hostname)
    except ValueError:
        host_ip = None
    dnsnames = []
    san = cert.get('subjectAltName', ())
    for (key, value) in san:
        if (key == 'DNS'):
            if ((host_ip is None) and _dnsname_match(value, hostname)):
                return
            dnsnames.append(value)
        elif (key == 'IP Address'):
            if ((host_ip is not None) and _ipaddress_match(value, host_ip)):
                return
            dnsnames.append(value)
    if (not dnsnames):
        for sub in cert.get('subject', ()):
            for (key, value) in sub:
                if (key == 'commonName'):
                    if _dnsname_match(value, hostname):
                        return
                    dnsnames.append(value)
    if (len(dnsnames) > 1):
        raise CertificateError(("hostname %r doesn't match either of %s" % (hostname, ', '.join(map(repr, dnsnames)))))
    elif (len(dnsnames) == 1):
        raise CertificateError(("hostname %r doesn't match %r" % (hostname, dnsnames[0])))
    else:
        raise CertificateError('no appropriate commonName or subjectAltName fields were found')
DefaultVerifyPaths = namedtuple('DefaultVerifyPaths', 'cafile capath openssl_cafile_env openssl_cafile openssl_capath_env openssl_capath')

def get_default_verify_paths():
    'Return paths to default cafile and capath.\n    '
    parts = _ssl.get_default_verify_paths()
    cafile = os.environ.get(parts[0], parts[1])
    capath = os.environ.get(parts[2], parts[3])
    return DefaultVerifyPaths((cafile if os.path.isfile(cafile) else None), (capath if os.path.isdir(capath) else None), *parts)

class _ASN1Object(namedtuple('_ASN1Object', 'nid shortname longname oid')):
    'ASN.1 object identifier lookup\n    '
    __slots__ = ()

    def __new__(cls, oid):
        return super().__new__(cls, *_txt2obj(oid, name=False))

    @classmethod
    def fromnid(cls, nid):
        'Create _ASN1Object from OpenSSL numeric ID\n        '
        return super().__new__(cls, *_nid2obj(nid))

    @classmethod
    def fromname(cls, name):
        'Create _ASN1Object from short name, long name or OID\n        '
        return super().__new__(cls, *_txt2obj(name, name=True))

class Purpose(_ASN1Object, _Enum):
    'SSLContext purpose flags with X509v3 Extended Key Usage objects\n    '
    SERVER_AUTH = '1.3.6.1.5.5.7.3.1'
    CLIENT_AUTH = '1.3.6.1.5.5.7.3.2'

class SSLContext(_SSLContext):
    'An SSLContext holds various SSL-related configuration options and\n    data, such as certificates and possibly a private key.'
    _windows_cert_stores = ('CA', 'ROOT')
    sslsocket_class = None
    sslobject_class = None

    def __new__(cls, protocol=PROTOCOL_TLS, *args, **kwargs):
        self = _SSLContext.__new__(cls, protocol)
        return self

    def _encode_hostname(self, hostname):
        if (hostname is None):
            return None
        elif isinstance(hostname, str):
            return hostname.encode('idna').decode('ascii')
        else:
            return hostname.decode('ascii')

    def wrap_socket(self, sock, server_side=False, do_handshake_on_connect=True, suppress_ragged_eofs=True, server_hostname=None, session=None):
        return self.sslsocket_class._create(sock=sock, server_side=server_side, do_handshake_on_connect=do_handshake_on_connect, suppress_ragged_eofs=suppress_ragged_eofs, server_hostname=server_hostname, context=self, session=session)

    def wrap_bio(self, incoming, outgoing, server_side=False, server_hostname=None, session=None):
        return self.sslobject_class._create(incoming, outgoing, server_side=server_side, server_hostname=self._encode_hostname(server_hostname), session=session, context=self)

    def set_npn_protocols(self, npn_protocols):
        protos = bytearray()
        for protocol in npn_protocols:
            b = bytes(protocol, 'ascii')
            if ((len(b) == 0) or (len(b) > 255)):
                raise SSLError('NPN protocols must be 1 to 255 in length')
            protos.append(len(b))
            protos.extend(b)
        self._set_npn_protocols(protos)

    def set_servername_callback(self, server_name_callback):
        if (server_name_callback is None):
            self.sni_callback = None
        else:
            if (not callable(server_name_callback)):
                raise TypeError('not a callable object')

            def shim_cb(sslobj, servername, sslctx):
                servername = self._encode_hostname(servername)
                return server_name_callback(sslobj, servername, sslctx)
            self.sni_callback = shim_cb

    def set_alpn_protocols(self, alpn_protocols):
        protos = bytearray()
        for protocol in alpn_protocols:
            b = bytes(protocol, 'ascii')
            if ((len(b) == 0) or (len(b) > 255)):
                raise SSLError('ALPN protocols must be 1 to 255 in length')
            protos.append(len(b))
            protos.extend(b)
        self._set_alpn_protocols(protos)

    def _load_windows_store_certs(self, storename, purpose):
        certs = bytearray()
        try:
            for (cert, encoding, trust) in enum_certificates(storename):
                if (encoding == 'x509_asn'):
                    if ((trust is True) or (purpose.oid in trust)):
                        certs.extend(cert)
        except PermissionError:
            warnings.warn('unable to enumerate Windows certificate store')
        if certs:
            self.load_verify_locations(cadata=certs)
        return certs

    def load_default_certs(self, purpose=Purpose.SERVER_AUTH):
        if (not isinstance(purpose, _ASN1Object)):
            raise TypeError(purpose)
        if (sys.platform == 'win32'):
            for storename in self._windows_cert_stores:
                self._load_windows_store_certs(storename, purpose)
        self.set_default_verify_paths()
    if hasattr(_SSLContext, 'minimum_version'):

        @property
        def minimum_version(self):
            return TLSVersion(super().minimum_version)

        @minimum_version.setter
        def minimum_version(self, value):
            if (value == TLSVersion.SSLv3):
                self.options &= (~ Options.OP_NO_SSLv3)
            super(SSLContext, SSLContext).minimum_version.__set__(self, value)

        @property
        def maximum_version(self):
            return TLSVersion(super().maximum_version)

        @maximum_version.setter
        def maximum_version(self, value):
            super(SSLContext, SSLContext).maximum_version.__set__(self, value)

    @property
    def options(self):
        return Options(super().options)

    @options.setter
    def options(self, value):
        super(SSLContext, SSLContext).options.__set__(self, value)
    if hasattr(_ssl, 'HOSTFLAG_NEVER_CHECK_SUBJECT'):

        @property
        def hostname_checks_common_name(self):
            ncs = (self._host_flags & _ssl.HOSTFLAG_NEVER_CHECK_SUBJECT)
            return (ncs != _ssl.HOSTFLAG_NEVER_CHECK_SUBJECT)

        @hostname_checks_common_name.setter
        def hostname_checks_common_name(self, value):
            if value:
                self._host_flags &= (~ _ssl.HOSTFLAG_NEVER_CHECK_SUBJECT)
            else:
                self._host_flags |= _ssl.HOSTFLAG_NEVER_CHECK_SUBJECT
    else:

        @property
        def hostname_checks_common_name(self):
            return True

    @property
    def _msg_callback(self):
        "TLS message callback\n\n        The message callback provides a debugging hook to analyze TLS\n        connections. The callback is called for any TLS protocol message\n        (header, handshake, alert, and more), but not for application data.\n        Due to technical  limitations, the callback can't be used to filter\n        traffic or to abort a connection. Any exception raised in the\n        callback is delayed until the handshake, read, or write operation\n        has been performed.\n\n        def msg_cb(conn, direction, version, content_type, msg_type, data):\n            pass\n\n        conn\n            :class:`SSLSocket` or :class:`SSLObject` instance\n        direction\n            ``read`` or ``write``\n        version\n            :class:`TLSVersion` enum member or int for unknown version. For a\n            frame header, it's the header version.\n        content_type\n            :class:`_TLSContentType` enum member or int for unsupported\n            content type.\n        msg_type\n            Either a :class:`_TLSContentType` enum number for a header\n            message, a :class:`_TLSAlertType` enum member for an alert\n            message, a :class:`_TLSMessageType` enum member for other\n            messages, or int for unsupported message types.\n        data\n            Raw, decrypted message content as bytes\n        "
        inner = super()._msg_callback
        if (inner is not None):
            return inner.user_function
        else:
            return None

    @_msg_callback.setter
    def _msg_callback(self, callback):
        if (callback is None):
            super(SSLContext, SSLContext)._msg_callback.__set__(self, None)
            return
        if (not hasattr(callback, '__call__')):
            raise TypeError(f'{callback} is not callable.')

        def inner(conn, direction, version, content_type, msg_type, data):
            try:
                version = TLSVersion(version)
            except ValueError:
                pass
            try:
                content_type = _TLSContentType(content_type)
            except ValueError:
                pass
            if (content_type == _TLSContentType.HEADER):
                msg_enum = _TLSContentType
            elif (content_type == _TLSContentType.ALERT):
                msg_enum = _TLSAlertType
            else:
                msg_enum = _TLSMessageType
            try:
                msg_type = msg_enum(msg_type)
            except ValueError:
                pass
            return callback(conn, direction, version, content_type, msg_type, data)
        inner.user_function = callback
        super(SSLContext, SSLContext)._msg_callback.__set__(self, inner)

    @property
    def protocol(self):
        return _SSLMethod(super().protocol)

    @property
    def verify_flags(self):
        return VerifyFlags(super().verify_flags)

    @verify_flags.setter
    def verify_flags(self, value):
        super(SSLContext, SSLContext).verify_flags.__set__(self, value)

    @property
    def verify_mode(self):
        value = super().verify_mode
        try:
            return VerifyMode(value)
        except ValueError:
            return value

    @verify_mode.setter
    def verify_mode(self, value):
        super(SSLContext, SSLContext).verify_mode.__set__(self, value)

def create_default_context(purpose=Purpose.SERVER_AUTH, *, cafile=None, capath=None, cadata=None):
    'Create a SSLContext object with default settings.\n\n    NOTE: The protocol and settings may change anytime without prior\n          deprecation. The values represent a fair balance between maximum\n          compatibility and security.\n    '
    if (not isinstance(purpose, _ASN1Object)):
        raise TypeError(purpose)
    context = SSLContext(PROTOCOL_TLS)
    if (purpose == Purpose.SERVER_AUTH):
        context.verify_mode = CERT_REQUIRED
        context.check_hostname = True
    if (cafile or capath or cadata):
        context.load_verify_locations(cafile, capath, cadata)
    elif (context.verify_mode != CERT_NONE):
        context.load_default_certs(purpose)
    if hasattr(context, 'keylog_filename'):
        keylogfile = os.environ.get('SSLKEYLOGFILE')
        if (keylogfile and (not sys.flags.ignore_environment)):
            context.keylog_filename = keylogfile
    return context

def _create_unverified_context(protocol=PROTOCOL_TLS, *, cert_reqs=CERT_NONE, check_hostname=False, purpose=Purpose.SERVER_AUTH, certfile=None, keyfile=None, cafile=None, capath=None, cadata=None):
    "Create a SSLContext object for Python stdlib modules\n\n    All Python stdlib modules shall use this function to create SSLContext\n    objects in order to keep common settings in one place. The configuration\n    is less restrict than create_default_context()'s to increase backward\n    compatibility.\n    "
    if (not isinstance(purpose, _ASN1Object)):
        raise TypeError(purpose)
    context = SSLContext(protocol)
    if (not check_hostname):
        context.check_hostname = False
    if (cert_reqs is not None):
        context.verify_mode = cert_reqs
    if check_hostname:
        context.check_hostname = True
    if (keyfile and (not certfile)):
        raise ValueError('certfile must be specified')
    if (certfile or keyfile):
        context.load_cert_chain(certfile, keyfile)
    if (cafile or capath or cadata):
        context.load_verify_locations(cafile, capath, cadata)
    elif (context.verify_mode != CERT_NONE):
        context.load_default_certs(purpose)
    if hasattr(context, 'keylog_filename'):
        keylogfile = os.environ.get('SSLKEYLOGFILE')
        if (keylogfile and (not sys.flags.ignore_environment)):
            context.keylog_filename = keylogfile
    return context
_create_default_https_context = create_default_context
_create_stdlib_context = _create_unverified_context

class SSLObject():
    'This class implements an interface on top of a low-level SSL object as\n    implemented by OpenSSL. This object captures the state of an SSL connection\n    but does not provide any network IO itself. IO needs to be performed\n    through separate "BIO" objects which are OpenSSL\'s IO abstraction layer.\n\n    This class does not have a public constructor. Instances are returned by\n    ``SSLContext.wrap_bio``. This class is typically used by framework authors\n    that want to implement asynchronous IO for SSL through memory buffers.\n\n    When compared to ``SSLSocket``, this object lacks the following features:\n\n     * Any form of network IO, including methods such as ``recv`` and ``send``.\n     * The ``do_handshake_on_connect`` and ``suppress_ragged_eofs`` machinery.\n    '

    def __init__(self, *args, **kwargs):
        raise TypeError(f'{self.__class__.__name__} does not have a public constructor. Instances are returned by SSLContext.wrap_bio().')

    @classmethod
    def _create(cls, incoming, outgoing, server_side=False, server_hostname=None, session=None, context=None):
        self = cls.__new__(cls)
        sslobj = context._wrap_bio(incoming, outgoing, server_side=server_side, server_hostname=server_hostname, owner=self, session=session)
        self._sslobj = sslobj
        return self

    @property
    def context(self):
        'The SSLContext that is currently in use.'
        return self._sslobj.context

    @context.setter
    def context(self, ctx):
        self._sslobj.context = ctx

    @property
    def session(self):
        'The SSLSession for client socket.'
        return self._sslobj.session

    @session.setter
    def session(self, session):
        self._sslobj.session = session

    @property
    def session_reused(self):
        'Was the client session reused during handshake'
        return self._sslobj.session_reused

    @property
    def server_side(self):
        'Whether this is a server-side socket.'
        return self._sslobj.server_side

    @property
    def server_hostname(self):
        'The currently set server hostname (for SNI), or ``None`` if no\n        server hostname is set.'
        return self._sslobj.server_hostname

    def read(self, len=1024, buffer=None):
        "Read up to 'len' bytes from the SSL object and return them.\n\n        If 'buffer' is provided, read into this buffer and return the number of\n        bytes read.\n        "
        if (buffer is not None):
            v = self._sslobj.read(len, buffer)
        else:
            v = self._sslobj.read(len)
        return v

    def write(self, data):
        "Write 'data' to the SSL object and return the number of bytes\n        written.\n\n        The 'data' argument must support the buffer interface.\n        "
        return self._sslobj.write(data)

    def getpeercert(self, binary_form=False):
        'Returns a formatted version of the data in the certificate provided\n        by the other end of the SSL channel.\n\n        Return None if no certificate was provided, {} if a certificate was\n        provided, but not validated.\n        '
        return self._sslobj.getpeercert(binary_form)

    def selected_npn_protocol(self):
        'Return the currently selected NPN protocol as a string, or ``None``\n        if a next protocol was not negotiated or if NPN is not supported by one\n        of the peers.'
        if _ssl.HAS_NPN:
            return self._sslobj.selected_npn_protocol()

    def selected_alpn_protocol(self):
        'Return the currently selected ALPN protocol as a string, or ``None``\n        if a next protocol was not negotiated or if ALPN is not supported by one\n        of the peers.'
        if _ssl.HAS_ALPN:
            return self._sslobj.selected_alpn_protocol()

    def cipher(self):
        'Return the currently selected cipher as a 3-tuple ``(name,\n        ssl_version, secret_bits)``.'
        return self._sslobj.cipher()

    def shared_ciphers(self):
        'Return a list of ciphers shared by the client during the handshake or\n        None if this is not a valid server connection.\n        '
        return self._sslobj.shared_ciphers()

    def compression(self):
        'Return the current compression algorithm in use, or ``None`` if\n        compression was not negotiated or not supported by one of the peers.'
        return self._sslobj.compression()

    def pending(self):
        'Return the number of bytes that can be read immediately.'
        return self._sslobj.pending()

    def do_handshake(self):
        'Start the SSL/TLS handshake.'
        self._sslobj.do_handshake()

    def unwrap(self):
        'Start the SSL shutdown handshake.'
        return self._sslobj.shutdown()

    def get_channel_binding(self, cb_type='tls-unique'):
        'Get channel binding data for current connection.  Raise ValueError\n        if the requested `cb_type` is not supported.  Return bytes of the data\n        or None if the data is not available (e.g. before the handshake).'
        return self._sslobj.get_channel_binding(cb_type)

    def version(self):
        'Return a string identifying the protocol version used by the\n        current SSL channel. '
        return self._sslobj.version()

    def verify_client_post_handshake(self):
        return self._sslobj.verify_client_post_handshake()

def _sslcopydoc(func):
    'Copy docstring from SSLObject to SSLSocket'
    func.__doc__ = getattr(SSLObject, func.__name__).__doc__
    return func

class SSLSocket(socket):
    'This class implements a subtype of socket.socket that wraps\n    the underlying OS socket in an SSL context when necessary, and\n    provides read and write methods over that channel. '

    def __init__(self, *args, **kwargs):
        raise TypeError(f'{self.__class__.__name__} does not have a public constructor. Instances are returned by SSLContext.wrap_socket().')

    @classmethod
    def _create(cls, sock, server_side=False, do_handshake_on_connect=True, suppress_ragged_eofs=True, server_hostname=None, context=None, session=None):
        if (sock.getsockopt(SOL_SOCKET, SO_TYPE) != SOCK_STREAM):
            raise NotImplementedError('only stream sockets are supported')
        if server_side:
            if server_hostname:
                raise ValueError('server_hostname can only be specified in client mode')
            if (session is not None):
                raise ValueError('session can only be specified in client mode')
        if (context.check_hostname and (not server_hostname)):
            raise ValueError('check_hostname requires server_hostname')
        kwargs = dict(family=sock.family, type=sock.type, proto=sock.proto, fileno=sock.fileno())
        self = cls.__new__(cls, **kwargs)
        super(SSLSocket, self).__init__(**kwargs)
        self.settimeout(sock.gettimeout())
        sock.detach()
        self._context = context
        self._session = session
        self._closed = False
        self._sslobj = None
        self.server_side = server_side
        self.server_hostname = context._encode_hostname(server_hostname)
        self.do_handshake_on_connect = do_handshake_on_connect
        self.suppress_ragged_eofs = suppress_ragged_eofs
        try:
            self.getpeername()
        except OSError as e:
            if (e.errno != errno.ENOTCONN):
                raise
            connected = False
        else:
            connected = True
        self._connected = connected
        if connected:
            try:
                self._sslobj = self._context._wrap_socket(self, server_side, self.server_hostname, owner=self, session=self._session)
                if do_handshake_on_connect:
                    timeout = self.gettimeout()
                    if (timeout == 0.0):
                        raise ValueError('do_handshake_on_connect should not be specified for non-blocking sockets')
                    self.do_handshake()
            except (OSError, ValueError):
                self.close()
                raise
        return self

    @property
    @_sslcopydoc
    def context(self):
        return self._context

    @context.setter
    def context(self, ctx):
        self._context = ctx
        self._sslobj.context = ctx

    @property
    @_sslcopydoc
    def session(self):
        if (self._sslobj is not None):
            return self._sslobj.session

    @session.setter
    def session(self, session):
        self._session = session
        if (self._sslobj is not None):
            self._sslobj.session = session

    @property
    @_sslcopydoc
    def session_reused(self):
        if (self._sslobj is not None):
            return self._sslobj.session_reused

    def dup(self):
        raise NotImplementedError(("Can't dup() %s instances" % self.__class__.__name__))

    def _checkClosed(self, msg=None):
        pass

    def _check_connected(self):
        if (not self._connected):
            self.getpeername()

    def read(self, len=1024, buffer=None):
        'Read up to LEN bytes and return them.\n        Return zero-length string on EOF.'
        self._checkClosed()
        if (self._sslobj is None):
            raise ValueError('Read on closed or unwrapped SSL socket.')
        try:
            if (buffer is not None):
                return self._sslobj.read(len, buffer)
            else:
                return self._sslobj.read(len)
        except SSLError as x:
            if ((x.args[0] == SSL_ERROR_EOF) and self.suppress_ragged_eofs):
                if (buffer is not None):
                    return 0
                else:
                    return b''
            else:
                raise

    def write(self, data):
        'Write DATA to the underlying SSL channel.  Returns\n        number of bytes of DATA actually transmitted.'
        self._checkClosed()
        if (self._sslobj is None):
            raise ValueError('Write on closed or unwrapped SSL socket.')
        return self._sslobj.write(data)

    @_sslcopydoc
    def getpeercert(self, binary_form=False):
        self._checkClosed()
        self._check_connected()
        return self._sslobj.getpeercert(binary_form)

    @_sslcopydoc
    def selected_npn_protocol(self):
        self._checkClosed()
        if ((self._sslobj is None) or (not _ssl.HAS_NPN)):
            return None
        else:
            return self._sslobj.selected_npn_protocol()

    @_sslcopydoc
    def selected_alpn_protocol(self):
        self._checkClosed()
        if ((self._sslobj is None) or (not _ssl.HAS_ALPN)):
            return None
        else:
            return self._sslobj.selected_alpn_protocol()

    @_sslcopydoc
    def cipher(self):
        self._checkClosed()
        if (self._sslobj is None):
            return None
        else:
            return self._sslobj.cipher()

    @_sslcopydoc
    def shared_ciphers(self):
        self._checkClosed()
        if (self._sslobj is None):
            return None
        else:
            return self._sslobj.shared_ciphers()

    @_sslcopydoc
    def compression(self):
        self._checkClosed()
        if (self._sslobj is None):
            return None
        else:
            return self._sslobj.compression()

    def send(self, data, flags=0):
        self._checkClosed()
        if (self._sslobj is not None):
            if (flags != 0):
                raise ValueError(('non-zero flags not allowed in calls to send() on %s' % self.__class__))
            return self._sslobj.write(data)
        else:
            return super().send(data, flags)

    def sendto(self, data, flags_or_addr, addr=None):
        self._checkClosed()
        if (self._sslobj is not None):
            raise ValueError(('sendto not allowed on instances of %s' % self.__class__))
        elif (addr is None):
            return super().sendto(data, flags_or_addr)
        else:
            return super().sendto(data, flags_or_addr, addr)

    def sendmsg(self, *args, **kwargs):
        raise NotImplementedError(('sendmsg not allowed on instances of %s' % self.__class__))

    def sendall(self, data, flags=0):
        self._checkClosed()
        if (self._sslobj is not None):
            if (flags != 0):
                raise ValueError(('non-zero flags not allowed in calls to sendall() on %s' % self.__class__))
            count = 0
            with memoryview(data) as view, view.cast('B') as byte_view:
                amount = len(byte_view)
                while (count < amount):
                    v = self.send(byte_view[count:])
                    count += v
        else:
            return super().sendall(data, flags)

    def sendfile(self, file, offset=0, count=None):
        'Send a file, possibly by using os.sendfile() if this is a\n        clear-text socket.  Return the total number of bytes sent.\n        '
        if (self._sslobj is not None):
            return self._sendfile_use_send(file, offset, count)
        else:
            return super().sendfile(file, offset, count)

    def recv(self, buflen=1024, flags=0):
        self._checkClosed()
        if (self._sslobj is not None):
            if (flags != 0):
                raise ValueError(('non-zero flags not allowed in calls to recv() on %s' % self.__class__))
            return self.read(buflen)
        else:
            return super().recv(buflen, flags)

    def recv_into(self, buffer, nbytes=None, flags=0):
        self._checkClosed()
        if (buffer and (nbytes is None)):
            nbytes = len(buffer)
        elif (nbytes is None):
            nbytes = 1024
        if (self._sslobj is not None):
            if (flags != 0):
                raise ValueError(('non-zero flags not allowed in calls to recv_into() on %s' % self.__class__))
            return self.read(nbytes, buffer)
        else:
            return super().recv_into(buffer, nbytes, flags)

    def recvfrom(self, buflen=1024, flags=0):
        self._checkClosed()
        if (self._sslobj is not None):
            raise ValueError(('recvfrom not allowed on instances of %s' % self.__class__))
        else:
            return super().recvfrom(buflen, flags)

    def recvfrom_into(self, buffer, nbytes=None, flags=0):
        self._checkClosed()
        if (self._sslobj is not None):
            raise ValueError(('recvfrom_into not allowed on instances of %s' % self.__class__))
        else:
            return super().recvfrom_into(buffer, nbytes, flags)

    def recvmsg(self, *args, **kwargs):
        raise NotImplementedError(('recvmsg not allowed on instances of %s' % self.__class__))

    def recvmsg_into(self, *args, **kwargs):
        raise NotImplementedError(('recvmsg_into not allowed on instances of %s' % self.__class__))

    @_sslcopydoc
    def pending(self):
        self._checkClosed()
        if (self._sslobj is not None):
            return self._sslobj.pending()
        else:
            return 0

    def shutdown(self, how):
        self._checkClosed()
        self._sslobj = None
        super().shutdown(how)

    @_sslcopydoc
    def unwrap(self):
        if self._sslobj:
            s = self._sslobj.shutdown()
            self._sslobj = None
            return s
        else:
            raise ValueError(('No SSL wrapper around ' + str(self)))

    @_sslcopydoc
    def verify_client_post_handshake(self):
        if self._sslobj:
            return self._sslobj.verify_client_post_handshake()
        else:
            raise ValueError(('No SSL wrapper around ' + str(self)))

    def _real_close(self):
        self._sslobj = None
        super()._real_close()

    @_sslcopydoc
    def do_handshake(self, block=False):
        self._check_connected()
        timeout = self.gettimeout()
        try:
            if ((timeout == 0.0) and block):
                self.settimeout(None)
            self._sslobj.do_handshake()
        finally:
            self.settimeout(timeout)

    def _real_connect(self, addr, connect_ex):
        if self.server_side:
            raise ValueError("can't connect in server-side mode")
        if (self._connected or (self._sslobj is not None)):
            raise ValueError('attempt to connect already-connected SSLSocket!')
        self._sslobj = self.context._wrap_socket(self, False, self.server_hostname, owner=self, session=self._session)
        try:
            if connect_ex:
                rc = super().connect_ex(addr)
            else:
                rc = None
                super().connect(addr)
            if (not rc):
                self._connected = True
                if self.do_handshake_on_connect:
                    self.do_handshake()
            return rc
        except (OSError, ValueError):
            self._sslobj = None
            raise

    def connect(self, addr):
        'Connects to remote ADDR, and then wraps the connection in\n        an SSL channel.'
        self._real_connect(addr, False)

    def connect_ex(self, addr):
        'Connects to remote ADDR, and then wraps the connection in\n        an SSL channel.'
        return self._real_connect(addr, True)

    def accept(self):
        'Accepts a new connection from a remote client, and returns\n        a tuple containing that new connection wrapped with a server-side\n        SSL channel, and the address of the remote client.'
        (newsock, addr) = super().accept()
        newsock = self.context.wrap_socket(newsock, do_handshake_on_connect=self.do_handshake_on_connect, suppress_ragged_eofs=self.suppress_ragged_eofs, server_side=True)
        return (newsock, addr)

    @_sslcopydoc
    def get_channel_binding(self, cb_type='tls-unique'):
        if (self._sslobj is not None):
            return self._sslobj.get_channel_binding(cb_type)
        else:
            if (cb_type not in CHANNEL_BINDING_TYPES):
                raise ValueError('{0} channel binding type not implemented'.format(cb_type))
            return None

    @_sslcopydoc
    def version(self):
        if (self._sslobj is not None):
            return self._sslobj.version()
        else:
            return None
SSLContext.sslsocket_class = SSLSocket
SSLContext.sslobject_class = SSLObject

def wrap_socket(sock, keyfile=None, certfile=None, server_side=False, cert_reqs=CERT_NONE, ssl_version=PROTOCOL_TLS, ca_certs=None, do_handshake_on_connect=True, suppress_ragged_eofs=True, ciphers=None):
    if (server_side and (not certfile)):
        raise ValueError('certfile must be specified for server-side operations')
    if (keyfile and (not certfile)):
        raise ValueError('certfile must be specified')
    context = SSLContext(ssl_version)
    context.verify_mode = cert_reqs
    if ca_certs:
        context.load_verify_locations(ca_certs)
    if certfile:
        context.load_cert_chain(certfile, keyfile)
    if ciphers:
        context.set_ciphers(ciphers)
    return context.wrap_socket(sock=sock, server_side=server_side, do_handshake_on_connect=do_handshake_on_connect, suppress_ragged_eofs=suppress_ragged_eofs)

def cert_time_to_seconds(cert_time):
    'Return the time in seconds since the Epoch, given the timestring\n    representing the "notBefore" or "notAfter" date from a certificate\n    in ``"%b %d %H:%M:%S %Y %Z"`` strptime format (C locale).\n\n    "notBefore" or "notAfter" dates must use UTC (RFC 5280).\n\n    Month is one of: Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec\n    UTC should be specified as GMT (see ASN1_TIME_print())\n    '
    from time import strptime
    from calendar import timegm
    months = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
    time_format = ' %d %H:%M:%S %Y GMT'
    try:
        month_number = (months.index(cert_time[:3].title()) + 1)
    except ValueError:
        raise ValueError(('time data %r does not match format "%%b%s"' % (cert_time, time_format)))
    else:
        tt = strptime(cert_time[3:], time_format)
        return timegm(((tt[0], month_number) + tt[2:6]))
PEM_HEADER = '-----BEGIN CERTIFICATE-----'
PEM_FOOTER = '-----END CERTIFICATE-----'

def DER_cert_to_PEM_cert(der_cert_bytes):
    'Takes a certificate in binary DER format and returns the\n    PEM version of it as a string.'
    f = str(base64.standard_b64encode(der_cert_bytes), 'ASCII', 'strict')
    ss = [PEM_HEADER]
    ss += [f[i:(i + 64)] for i in range(0, len(f), 64)]
    ss.append((PEM_FOOTER + '\n'))
    return '\n'.join(ss)

def PEM_cert_to_DER_cert(pem_cert_string):
    'Takes a certificate in ASCII PEM format and returns the\n    DER-encoded version of it as a byte sequence'
    if (not pem_cert_string.startswith(PEM_HEADER)):
        raise ValueError(('Invalid PEM encoding; must start with %s' % PEM_HEADER))
    if (not pem_cert_string.strip().endswith(PEM_FOOTER)):
        raise ValueError(('Invalid PEM encoding; must end with %s' % PEM_FOOTER))
    d = pem_cert_string.strip()[len(PEM_HEADER):(- len(PEM_FOOTER))]
    return base64.decodebytes(d.encode('ASCII', 'strict'))

def get_server_certificate(addr, ssl_version=PROTOCOL_TLS, ca_certs=None):
    "Retrieve the certificate from the server at the specified address,\n    and return it as a PEM-encoded string.\n    If 'ca_certs' is specified, validate the server cert against it.\n    If 'ssl_version' is specified, use it in the connection attempt."
    (host, port) = addr
    if (ca_certs is not None):
        cert_reqs = CERT_REQUIRED
    else:
        cert_reqs = CERT_NONE
    context = _create_stdlib_context(ssl_version, cert_reqs=cert_reqs, cafile=ca_certs)
    with create_connection(addr) as sock:
        with context.wrap_socket(sock) as sslsock:
            dercert = sslsock.getpeercert(True)
    return DER_cert_to_PEM_cert(dercert)

def get_protocol_name(protocol_code):
    return _PROTOCOL_NAMES.get(protocol_code, '<unknown>')
