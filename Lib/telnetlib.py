
'TELNET client class.\n\nBased on RFC 854: TELNET Protocol Specification, by J. Postel and\nJ. Reynolds\n\nExample:\n\n>>> from telnetlib import Telnet\n>>> tn = Telnet(\'www.python.org\', 79)   # connect to finger port\n>>> tn.write(b\'guido\\r\\n\')\n>>> print(tn.read_all())\nLogin       Name               TTY         Idle    When    Where\nguido    Guido van Rossum      pts/2        <Dec  2 11:10> snag.cnri.reston..\n\n>>>\n\nNote that read_all() won\'t read until eof -- it just reads some data\n-- but it guarantees to read at least one byte unless EOF is hit.\n\nIt is possible to pass a Telnet object to a selector in order to wait until\nmore data is available.  Note that in this case, read_eager() may return b\'\'\neven if there was data on the socket, because the protocol negotiation may have\neaten the data.  This is why EOFError is needed in some cases to distinguish\nbetween "no data" and "connection closed" (since the socket also appears ready\nfor reading when it is closed).\n\nTo do:\n- option negotiation\n- timeout should be intrinsic to the connection object instead of an\n  option on one of the read calls only\n\n'
import sys
import socket
import selectors
from time import monotonic as _time
__all__ = ['Telnet']
DEBUGLEVEL = 0
TELNET_PORT = 23
IAC = bytes([255])
DONT = bytes([254])
DO = bytes([253])
WONT = bytes([252])
WILL = bytes([251])
theNULL = bytes([0])
SE = bytes([240])
NOP = bytes([241])
DM = bytes([242])
BRK = bytes([243])
IP = bytes([244])
AO = bytes([245])
AYT = bytes([246])
EC = bytes([247])
EL = bytes([248])
GA = bytes([249])
SB = bytes([250])
BINARY = bytes([0])
ECHO = bytes([1])
RCP = bytes([2])
SGA = bytes([3])
NAMS = bytes([4])
STATUS = bytes([5])
TM = bytes([6])
RCTE = bytes([7])
NAOL = bytes([8])
NAOP = bytes([9])
NAOCRD = bytes([10])
NAOHTS = bytes([11])
NAOHTD = bytes([12])
NAOFFD = bytes([13])
NAOVTS = bytes([14])
NAOVTD = bytes([15])
NAOLFD = bytes([16])
XASCII = bytes([17])
LOGOUT = bytes([18])
BM = bytes([19])
DET = bytes([20])
SUPDUP = bytes([21])
SUPDUPOUTPUT = bytes([22])
SNDLOC = bytes([23])
TTYPE = bytes([24])
EOR = bytes([25])
TUID = bytes([26])
OUTMRK = bytes([27])
TTYLOC = bytes([28])
VT3270REGIME = bytes([29])
X3PAD = bytes([30])
NAWS = bytes([31])
TSPEED = bytes([32])
LFLOW = bytes([33])
LINEMODE = bytes([34])
XDISPLOC = bytes([35])
OLD_ENVIRON = bytes([36])
AUTHENTICATION = bytes([37])
ENCRYPT = bytes([38])
NEW_ENVIRON = bytes([39])
TN3270E = bytes([40])
XAUTH = bytes([41])
CHARSET = bytes([42])
RSP = bytes([43])
COM_PORT_OPTION = bytes([44])
SUPPRESS_LOCAL_ECHO = bytes([45])
TLS = bytes([46])
KERMIT = bytes([47])
SEND_URL = bytes([48])
FORWARD_X = bytes([49])
PRAGMA_LOGON = bytes([138])
SSPI_LOGON = bytes([139])
PRAGMA_HEARTBEAT = bytes([140])
EXOPL = bytes([255])
NOOPT = bytes([0])
if hasattr(selectors, 'PollSelector'):
    _TelnetSelector = selectors.PollSelector
else:
    _TelnetSelector = selectors.SelectSelector

class Telnet():
    "Telnet interface class.\n\n    An instance of this class represents a connection to a telnet\n    server.  The instance is initially not connected; the open()\n    method must be used to establish a connection.  Alternatively, the\n    host name and optional port number can be passed to the\n    constructor, too.\n\n    Don't try to reopen an already connected instance.\n\n    This class has many read_*() methods.  Note that some of them\n    raise EOFError when the end of the connection is read, because\n    they can return an empty string for other reasons.  See the\n    individual doc strings.\n\n    read_until(expected, [timeout])\n        Read until the expected string has been seen, or a timeout is\n        hit (default is no timeout); may block.\n\n    read_all()\n        Read all data until EOF; may block.\n\n    read_some()\n        Read at least one byte or EOF; may block.\n\n    read_very_eager()\n        Read all data available already queued or on the socket,\n        without blocking.\n\n    read_eager()\n        Read either data already queued or some data available on the\n        socket, without blocking.\n\n    read_lazy()\n        Read all data in the raw queue (processing it first), without\n        doing any socket I/O.\n\n    read_very_lazy()\n        Reads all data in the cooked queue, without doing any socket\n        I/O.\n\n    read_sb_data()\n        Reads available data between SB ... SE sequence. Don't block.\n\n    set_option_negotiation_callback(callback)\n        Each time a telnet option is read on the input flow, this callback\n        (if set) is called with the following parameters :\n        callback(telnet socket, command, option)\n            option will be chr(0) when there is no option.\n        No other action is done afterwards by telnetlib.\n\n    "

    def __init__(self, host=None, port=0, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        'Constructor.\n\n        When called without arguments, create an unconnected instance.\n        With a hostname argument, it connects the instance; port number\n        and timeout are optional.\n        '
        self.debuglevel = DEBUGLEVEL
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.rawq = b''
        self.irawq = 0
        self.cookedq = b''
        self.eof = 0
        self.iacseq = b''
        self.sb = 0
        self.sbdataq = b''
        self.option_callback = None
        if (host is not None):
            self.open(host, port, timeout)

    def open(self, host, port=0, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        "Connect to a host.\n\n        The optional second argument is the port number, which\n        defaults to the standard telnet port (23).\n\n        Don't try to reopen an already connected instance.\n        "
        self.eof = 0
        if (not port):
            port = TELNET_PORT
        self.host = host
        self.port = port
        self.timeout = timeout
        sys.audit('telnetlib.Telnet.open', self, host, port)
        self.sock = socket.create_connection((host, port), timeout)

    def __del__(self):
        'Destructor -- close the connection.'
        self.close()

    def msg(self, msg, *args):
        'Print a debug message, when the debug level is > 0.\n\n        If extra arguments are present, they are substituted in the\n        message using the standard string formatting operator.\n\n        '
        if (self.debuglevel > 0):
            print(('Telnet(%s,%s):' % (self.host, self.port)), end=' ')
            if args:
                print((msg % args))
            else:
                print(msg)

    def set_debuglevel(self, debuglevel):
        'Set the debug level.\n\n        The higher it is, the more debug output you get (on sys.stdout).\n\n        '
        self.debuglevel = debuglevel

    def close(self):
        'Close the connection.'
        sock = self.sock
        self.sock = None
        self.eof = True
        self.iacseq = b''
        self.sb = 0
        if sock:
            sock.close()

    def get_socket(self):
        'Return the socket object used internally.'
        return self.sock

    def fileno(self):
        'Return the fileno() of the socket object used internally.'
        return self.sock.fileno()

    def write(self, buffer):
        'Write a string to the socket, doubling any IAC characters.\n\n        Can block if the connection is blocked.  May raise\n        OSError if the connection is closed.\n\n        '
        if (IAC in buffer):
            buffer = buffer.replace(IAC, (IAC + IAC))
        sys.audit('telnetlib.Telnet.write', self, buffer)
        self.msg('send %r', buffer)
        self.sock.sendall(buffer)

    def read_until(self, match, timeout=None):
        'Read until a given string is encountered or until timeout.\n\n        When no match is found, return whatever is available instead,\n        possibly the empty string.  Raise EOFError if the connection\n        is closed and no cooked data is available.\n\n        '
        n = len(match)
        self.process_rawq()
        i = self.cookedq.find(match)
        if (i >= 0):
            i = (i + n)
            buf = self.cookedq[:i]
            self.cookedq = self.cookedq[i:]
            return buf
        if (timeout is not None):
            deadline = (_time() + timeout)
        with _TelnetSelector() as selector:
            selector.register(self, selectors.EVENT_READ)
            while (not self.eof):
                if selector.select(timeout):
                    i = max(0, (len(self.cookedq) - n))
                    self.fill_rawq()
                    self.process_rawq()
                    i = self.cookedq.find(match, i)
                    if (i >= 0):
                        i = (i + n)
                        buf = self.cookedq[:i]
                        self.cookedq = self.cookedq[i:]
                        return buf
                if (timeout is not None):
                    timeout = (deadline - _time())
                    if (timeout < 0):
                        break
        return self.read_very_lazy()

    def read_all(self):
        'Read all data until EOF; block until connection closed.'
        self.process_rawq()
        while (not self.eof):
            self.fill_rawq()
            self.process_rawq()
        buf = self.cookedq
        self.cookedq = b''
        return buf

    def read_some(self):
        "Read at least one byte of cooked data unless EOF is hit.\n\n        Return b'' if EOF is hit.  Block if no data is immediately\n        available.\n\n        "
        self.process_rawq()
        while ((not self.cookedq) and (not self.eof)):
            self.fill_rawq()
            self.process_rawq()
        buf = self.cookedq
        self.cookedq = b''
        return buf

    def read_very_eager(self):
        "Read everything that's possible without blocking in I/O (eager).\n\n        Raise EOFError if connection closed and no cooked data\n        available.  Return b'' if no cooked data available otherwise.\n        Don't block unless in the midst of an IAC sequence.\n\n        "
        self.process_rawq()
        while ((not self.eof) and self.sock_avail()):
            self.fill_rawq()
            self.process_rawq()
        return self.read_very_lazy()

    def read_eager(self):
        "Read readily available data.\n\n        Raise EOFError if connection closed and no cooked data\n        available.  Return b'' if no cooked data available otherwise.\n        Don't block unless in the midst of an IAC sequence.\n\n        "
        self.process_rawq()
        while ((not self.cookedq) and (not self.eof) and self.sock_avail()):
            self.fill_rawq()
            self.process_rawq()
        return self.read_very_lazy()

    def read_lazy(self):
        "Process and return data that's already in the queues (lazy).\n\n        Raise EOFError if connection closed and no data available.\n        Return b'' if no cooked data available otherwise.  Don't block\n        unless in the midst of an IAC sequence.\n\n        "
        self.process_rawq()
        return self.read_very_lazy()

    def read_very_lazy(self):
        "Return any data available in the cooked queue (very lazy).\n\n        Raise EOFError if connection closed and no data available.\n        Return b'' if no cooked data available otherwise.  Don't block.\n\n        "
        buf = self.cookedq
        self.cookedq = b''
        if ((not buf) and self.eof and (not self.rawq)):
            raise EOFError('telnet connection closed')
        return buf

    def read_sb_data(self):
        "Return any data available in the SB ... SE queue.\n\n        Return b'' if no SB ... SE available. Should only be called\n        after seeing a SB or SE command. When a new SB command is\n        found, old unread SB data will be discarded. Don't block.\n\n        "
        buf = self.sbdataq
        self.sbdataq = b''
        return buf

    def set_option_negotiation_callback(self, callback):
        'Provide a callback function called after each receipt of a telnet option.'
        self.option_callback = callback

    def process_rawq(self):
        "Transfer from raw queue to cooked queue.\n\n        Set self.eof when connection is closed.  Don't block unless in\n        the midst of an IAC sequence.\n\n        "
        buf = [b'', b'']
        try:
            while self.rawq:
                c = self.rawq_getchar()
                if (not self.iacseq):
                    if (c == theNULL):
                        continue
                    if (c == b'\x11'):
                        continue
                    if (c != IAC):
                        buf[self.sb] = (buf[self.sb] + c)
                        continue
                    else:
                        self.iacseq += c
                elif (len(self.iacseq) == 1):
                    if (c in (DO, DONT, WILL, WONT)):
                        self.iacseq += c
                        continue
                    self.iacseq = b''
                    if (c == IAC):
                        buf[self.sb] = (buf[self.sb] + c)
                    else:
                        if (c == SB):
                            self.sb = 1
                            self.sbdataq = b''
                        elif (c == SE):
                            self.sb = 0
                            self.sbdataq = (self.sbdataq + buf[1])
                            buf[1] = b''
                        if self.option_callback:
                            self.option_callback(self.sock, c, NOOPT)
                        else:
                            self.msg(('IAC %d not recognized' % ord(c)))
                elif (len(self.iacseq) == 2):
                    cmd = self.iacseq[1:2]
                    self.iacseq = b''
                    opt = c
                    if (cmd in (DO, DONT)):
                        self.msg('IAC %s %d', (((cmd == DO) and 'DO') or 'DONT'), ord(opt))
                        if self.option_callback:
                            self.option_callback(self.sock, cmd, opt)
                        else:
                            self.sock.sendall(((IAC + WONT) + opt))
                    elif (cmd in (WILL, WONT)):
                        self.msg('IAC %s %d', (((cmd == WILL) and 'WILL') or 'WONT'), ord(opt))
                        if self.option_callback:
                            self.option_callback(self.sock, cmd, opt)
                        else:
                            self.sock.sendall(((IAC + DONT) + opt))
        except EOFError:
            self.iacseq = b''
            self.sb = 0
            pass
        self.cookedq = (self.cookedq + buf[0])
        self.sbdataq = (self.sbdataq + buf[1])

    def rawq_getchar(self):
        'Get next char from raw queue.\n\n        Block if no data is immediately available.  Raise EOFError\n        when connection is closed.\n\n        '
        if (not self.rawq):
            self.fill_rawq()
            if self.eof:
                raise EOFError
        c = self.rawq[self.irawq:(self.irawq + 1)]
        self.irawq = (self.irawq + 1)
        if (self.irawq >= len(self.rawq)):
            self.rawq = b''
            self.irawq = 0
        return c

    def fill_rawq(self):
        'Fill raw queue from exactly one recv() system call.\n\n        Block if no data is immediately available.  Set self.eof when\n        connection is closed.\n\n        '
        if (self.irawq >= len(self.rawq)):
            self.rawq = b''
            self.irawq = 0
        buf = self.sock.recv(50)
        self.msg('recv %r', buf)
        self.eof = (not buf)
        self.rawq = (self.rawq + buf)

    def sock_avail(self):
        'Test whether data is available on the socket.'
        with _TelnetSelector() as selector:
            selector.register(self, selectors.EVENT_READ)
            return bool(selector.select(0))

    def interact(self):
        'Interaction function, emulates a very dumb telnet client.'
        if (sys.platform == 'win32'):
            self.mt_interact()
            return
        with _TelnetSelector() as selector:
            selector.register(self, selectors.EVENT_READ)
            selector.register(sys.stdin, selectors.EVENT_READ)
            while True:
                for (key, events) in selector.select():
                    if (key.fileobj is self):
                        try:
                            text = self.read_eager()
                        except EOFError:
                            print('*** Connection closed by remote host ***')
                            return
                        if text:
                            sys.stdout.write(text.decode('ascii'))
                            sys.stdout.flush()
                    elif (key.fileobj is sys.stdin):
                        line = sys.stdin.readline().encode('ascii')
                        if (not line):
                            return
                        self.write(line)

    def mt_interact(self):
        'Multithreaded version of interact().'
        import _thread
        _thread.start_new_thread(self.listener, ())
        while 1:
            line = sys.stdin.readline()
            if (not line):
                break
            self.write(line.encode('ascii'))

    def listener(self):
        'Helper for mt_interact() -- this executes in the other thread.'
        while 1:
            try:
                data = self.read_eager()
            except EOFError:
                print('*** Connection closed by remote host ***')
                return
            if data:
                sys.stdout.write(data.decode('ascii'))
            else:
                sys.stdout.flush()

    def expect(self, list, timeout=None):
        "Read until one from a list of a regular expressions matches.\n\n        The first argument is a list of regular expressions, either\n        compiled (re.Pattern instances) or uncompiled (strings).\n        The optional second argument is a timeout, in seconds; default\n        is no timeout.\n\n        Return a tuple of three items: the index in the list of the\n        first regular expression that matches; the re.Match object\n        returned; and the text read up till and including the match.\n\n        If EOF is read and no text was read, raise EOFError.\n        Otherwise, when nothing matches, return (-1, None, text) where\n        text is the text received so far (may be the empty string if a\n        timeout happened).\n\n        If a regular expression ends with a greedy match (e.g. '.*')\n        or if more than one expression can match the same input, the\n        results are undeterministic, and may depend on the I/O timing.\n\n        "
        re = None
        list = list[:]
        indices = range(len(list))
        for i in indices:
            if (not hasattr(list[i], 'search')):
                if (not re):
                    import re
                list[i] = re.compile(list[i])
        if (timeout is not None):
            deadline = (_time() + timeout)
        with _TelnetSelector() as selector:
            selector.register(self, selectors.EVENT_READ)
            while (not self.eof):
                self.process_rawq()
                for i in indices:
                    m = list[i].search(self.cookedq)
                    if m:
                        e = m.end()
                        text = self.cookedq[:e]
                        self.cookedq = self.cookedq[e:]
                        return (i, m, text)
                if (timeout is not None):
                    ready = selector.select(timeout)
                    timeout = (deadline - _time())
                    if (not ready):
                        if (timeout < 0):
                            break
                        else:
                            continue
                self.fill_rawq()
        text = self.read_very_lazy()
        if ((not text) and self.eof):
            raise EOFError
        return ((- 1), None, text)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

def test():
    'Test program for telnetlib.\n\n    Usage: python telnetlib.py [-d] ... [host [port]]\n\n    Default host is localhost; default port is 23.\n\n    '
    debuglevel = 0
    while (sys.argv[1:] and (sys.argv[1] == '-d')):
        debuglevel = (debuglevel + 1)
        del sys.argv[1]
    host = 'localhost'
    if sys.argv[1:]:
        host = sys.argv[1]
    port = 0
    if sys.argv[2:]:
        portstr = sys.argv[2]
        try:
            port = int(portstr)
        except ValueError:
            port = socket.getservbyname(portstr, 'tcp')
    with Telnet() as tn:
        tn.set_debuglevel(debuglevel)
        tn.open(host, port, timeout=0.5)
        tn.interact()
if (__name__ == '__main__'):
    test()
