
import asyncore
import unittest
import select
import os
import socket
import sys
import time
import errno
import struct
import threading
from test import support
from test.support import os_helper
from test.support import socket_helper
from test.support import threading_helper
from test.support import warnings_helper
from io import BytesIO
if support.PGO:
    raise unittest.SkipTest('test is not helpful for PGO')
HAS_UNIX_SOCKETS = hasattr(socket, 'AF_UNIX')

class dummysocket():

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True

    def fileno(self):
        return 42

class dummychannel():

    def __init__(self):
        self.socket = dummysocket()

    def close(self):
        self.socket.close()

class exitingdummy():

    def __init__(self):
        pass

    def handle_read_event(self):
        raise asyncore.ExitNow()
    handle_write_event = handle_read_event
    handle_close = handle_read_event
    handle_expt_event = handle_read_event

class crashingdummy():

    def __init__(self):
        self.error_handled = False

    def handle_read_event(self):
        raise Exception()
    handle_write_event = handle_read_event
    handle_close = handle_read_event
    handle_expt_event = handle_read_event

    def handle_error(self):
        self.error_handled = True

def capture_server(evt, buf, serv):
    try:
        serv.listen()
        (conn, addr) = serv.accept()
    except socket.timeout:
        pass
    else:
        n = 200
        start = time.monotonic()
        while ((n > 0) and ((time.monotonic() - start) < 3.0)):
            (r, w, e) = select.select([conn], [], [], 0.1)
            if r:
                n -= 1
                data = conn.recv(10)
                buf.write(data.replace(b'\n', b''))
                if (b'\n' in data):
                    break
            time.sleep(0.01)
        conn.close()
    finally:
        serv.close()
        evt.set()

def bind_af_aware(sock, addr):
    'Helper function to bind a socket according to its family.'
    if (HAS_UNIX_SOCKETS and (sock.family == socket.AF_UNIX)):
        os_helper.unlink(addr)
        socket_helper.bind_unix_socket(sock, addr)
    else:
        sock.bind(addr)

class HelperFunctionTests(unittest.TestCase):

    def test_readwriteexc(self):
        tr1 = exitingdummy()
        self.assertRaises(asyncore.ExitNow, asyncore.read, tr1)
        self.assertRaises(asyncore.ExitNow, asyncore.write, tr1)
        self.assertRaises(asyncore.ExitNow, asyncore._exception, tr1)
        tr2 = crashingdummy()
        asyncore.read(tr2)
        self.assertEqual(tr2.error_handled, True)
        tr2 = crashingdummy()
        asyncore.write(tr2)
        self.assertEqual(tr2.error_handled, True)
        tr2 = crashingdummy()
        asyncore._exception(tr2)
        self.assertEqual(tr2.error_handled, True)

    @unittest.skipUnless(hasattr(select, 'poll'), 'select.poll required')
    def test_readwrite(self):
        attributes = ('read', 'expt', 'write', 'closed', 'error_handled')
        expected = ((select.POLLIN, 'read'), (select.POLLPRI, 'expt'), (select.POLLOUT, 'write'), (select.POLLERR, 'closed'), (select.POLLHUP, 'closed'), (select.POLLNVAL, 'closed'))

        class testobj():

            def __init__(self):
                self.read = False
                self.write = False
                self.closed = False
                self.expt = False
                self.error_handled = False

            def handle_read_event(self):
                self.read = True

            def handle_write_event(self):
                self.write = True

            def handle_close(self):
                self.closed = True

            def handle_expt_event(self):
                self.expt = True

            def handle_error(self):
                self.error_handled = True
        for (flag, expectedattr) in expected:
            tobj = testobj()
            self.assertEqual(getattr(tobj, expectedattr), False)
            asyncore.readwrite(tobj, flag)
            for attr in attributes:
                self.assertEqual(getattr(tobj, attr), (attr == expectedattr))
            tr1 = exitingdummy()
            self.assertRaises(asyncore.ExitNow, asyncore.readwrite, tr1, flag)
            tr2 = crashingdummy()
            self.assertEqual(tr2.error_handled, False)
            asyncore.readwrite(tr2, flag)
            self.assertEqual(tr2.error_handled, True)

    def test_closeall(self):
        self.closeall_check(False)

    def test_closeall_default(self):
        self.closeall_check(True)

    def closeall_check(self, usedefault):
        l = []
        testmap = {}
        for i in range(10):
            c = dummychannel()
            l.append(c)
            self.assertEqual(c.socket.closed, False)
            testmap[i] = c
        if usedefault:
            socketmap = asyncore.socket_map
            try:
                asyncore.socket_map = testmap
                asyncore.close_all()
            finally:
                (testmap, asyncore.socket_map) = (asyncore.socket_map, socketmap)
        else:
            asyncore.close_all(testmap)
        self.assertEqual(len(testmap), 0)
        for c in l:
            self.assertEqual(c.socket.closed, True)

    def test_compact_traceback(self):
        try:
            raise Exception("I don't like spam!")
        except:
            (real_t, real_v, real_tb) = sys.exc_info()
            r = asyncore.compact_traceback()
        else:
            self.fail('Expected exception')
        ((f, function, line), t, v, info) = r
        self.assertEqual(os.path.split(f)[(- 1)], 'test_asyncore.py')
        self.assertEqual(function, 'test_compact_traceback')
        self.assertEqual(t, real_t)
        self.assertEqual(v, real_v)
        self.assertEqual(info, ('[%s|%s|%s]' % (f, function, line)))

class DispatcherTests(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        asyncore.close_all()

    def test_basic(self):
        d = asyncore.dispatcher()
        self.assertEqual(d.readable(), True)
        self.assertEqual(d.writable(), True)

    def test_repr(self):
        d = asyncore.dispatcher()
        self.assertEqual(repr(d), ('<asyncore.dispatcher at %#x>' % id(d)))

    def test_log(self):
        d = asyncore.dispatcher()
        l1 = 'Lovely spam! Wonderful spam!'
        l2 = "I don't like spam!"
        with support.captured_stderr() as stderr:
            d.log(l1)
            d.log(l2)
        lines = stderr.getvalue().splitlines()
        self.assertEqual(lines, [('log: %s' % l1), ('log: %s' % l2)])

    def test_log_info(self):
        d = asyncore.dispatcher()
        l1 = 'Have you got anything without spam?'
        l2 = "Why can't she have egg bacon spam and sausage?"
        l3 = "THAT'S got spam in it!"
        with support.captured_stdout() as stdout:
            d.log_info(l1, 'EGGS')
            d.log_info(l2)
            d.log_info(l3, 'SPAM')
        lines = stdout.getvalue().splitlines()
        expected = [('EGGS: %s' % l1), ('info: %s' % l2), ('SPAM: %s' % l3)]
        self.assertEqual(lines, expected)

    def test_unhandled(self):
        d = asyncore.dispatcher()
        d.ignore_log_types = ()
        with support.captured_stdout() as stdout:
            d.handle_expt()
            d.handle_read()
            d.handle_write()
            d.handle_connect()
        lines = stdout.getvalue().splitlines()
        expected = ['warning: unhandled incoming priority event', 'warning: unhandled read event', 'warning: unhandled write event', 'warning: unhandled connect event']
        self.assertEqual(lines, expected)

    def test_strerror(self):
        err = asyncore._strerror(errno.EPERM)
        if hasattr(os, 'strerror'):
            self.assertEqual(err, os.strerror(errno.EPERM))
        err = asyncore._strerror((- 1))
        self.assertTrue((err != ''))

class dispatcherwithsend_noread(asyncore.dispatcher_with_send):

    def readable(self):
        return False

    def handle_connect(self):
        pass

class DispatcherWithSendTests(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        asyncore.close_all()

    @threading_helper.reap_threads
    def test_send(self):
        evt = threading.Event()
        sock = socket.socket()
        sock.settimeout(3)
        port = socket_helper.bind_port(sock)
        cap = BytesIO()
        args = (evt, cap, sock)
        t = threading.Thread(target=capture_server, args=args)
        t.start()
        try:
            time.sleep(0.2)
            data = b"Suppose there isn't a 16-ton weight?"
            d = dispatcherwithsend_noread()
            d.create_socket()
            d.connect((socket_helper.HOST, port))
            time.sleep(0.1)
            d.send(data)
            d.send(data)
            d.send(b'\n')
            n = 1000
            while (d.out_buffer and (n > 0)):
                asyncore.poll()
                n -= 1
            evt.wait()
            self.assertEqual(cap.getvalue(), (data * 2))
        finally:
            threading_helper.join_thread(t)

@unittest.skipUnless(hasattr(asyncore, 'file_wrapper'), 'asyncore.file_wrapper required')
class FileWrapperTest(unittest.TestCase):

    def setUp(self):
        self.d = b"It's not dead, it's sleeping!"
        with open(os_helper.TESTFN, 'wb') as file:
            file.write(self.d)

    def tearDown(self):
        os_helper.unlink(os_helper.TESTFN)

    def test_recv(self):
        fd = os.open(os_helper.TESTFN, os.O_RDONLY)
        w = asyncore.file_wrapper(fd)
        os.close(fd)
        self.assertNotEqual(w.fd, fd)
        self.assertNotEqual(w.fileno(), fd)
        self.assertEqual(w.recv(13), b"It's not dead")
        self.assertEqual(w.read(6), b", it's")
        w.close()
        self.assertRaises(OSError, w.read, 1)

    def test_send(self):
        d1 = b'Come again?'
        d2 = b'I want to buy some cheese.'
        fd = os.open(os_helper.TESTFN, (os.O_WRONLY | os.O_APPEND))
        w = asyncore.file_wrapper(fd)
        os.close(fd)
        w.write(d1)
        w.send(d2)
        w.close()
        with open(os_helper.TESTFN, 'rb') as file:
            self.assertEqual(file.read(), ((self.d + d1) + d2))

    @unittest.skipUnless(hasattr(asyncore, 'file_dispatcher'), 'asyncore.file_dispatcher required')
    def test_dispatcher(self):
        fd = os.open(os_helper.TESTFN, os.O_RDONLY)
        data = []

        class FileDispatcher(asyncore.file_dispatcher):

            def handle_read(self):
                data.append(self.recv(29))
        s = FileDispatcher(fd)
        os.close(fd)
        asyncore.loop(timeout=0.01, use_poll=True, count=2)
        self.assertEqual(b''.join(data), self.d)

    def test_resource_warning(self):
        fd = os.open(os_helper.TESTFN, os.O_RDONLY)
        f = asyncore.file_wrapper(fd)
        os.close(fd)
        with warnings_helper.check_warnings(('', ResourceWarning)):
            f = None
            support.gc_collect()

    def test_close_twice(self):
        fd = os.open(os_helper.TESTFN, os.O_RDONLY)
        f = asyncore.file_wrapper(fd)
        os.close(fd)
        os.close(f.fd)
        with self.assertRaises(OSError):
            f.close()
        self.assertEqual(f.fd, (- 1))
        f.close()

class BaseTestHandler(asyncore.dispatcher):

    def __init__(self, sock=None):
        asyncore.dispatcher.__init__(self, sock)
        self.flag = False

    def handle_accept(self):
        raise Exception('handle_accept not supposed to be called')

    def handle_accepted(self):
        raise Exception('handle_accepted not supposed to be called')

    def handle_connect(self):
        raise Exception('handle_connect not supposed to be called')

    def handle_expt(self):
        raise Exception('handle_expt not supposed to be called')

    def handle_close(self):
        raise Exception('handle_close not supposed to be called')

    def handle_error(self):
        raise

class BaseServer(asyncore.dispatcher):
    'A server which listens on an address and dispatches the\n    connection to a handler.\n    '

    def __init__(self, family, addr, handler=BaseTestHandler):
        asyncore.dispatcher.__init__(self)
        self.create_socket(family)
        self.set_reuse_addr()
        bind_af_aware(self.socket, addr)
        self.listen(5)
        self.handler = handler

    @property
    def address(self):
        return self.socket.getsockname()

    def handle_accepted(self, sock, addr):
        self.handler(sock)

    def handle_error(self):
        raise

class BaseClient(BaseTestHandler):

    def __init__(self, family, address):
        BaseTestHandler.__init__(self)
        self.create_socket(family)
        self.connect(address)

    def handle_connect(self):
        pass

class BaseTestAPI():

    def tearDown(self):
        asyncore.close_all(ignore_all=True)

    def loop_waiting_for_flag(self, instance, timeout=5):
        timeout = (float(timeout) / 100)
        count = 100
        while (asyncore.socket_map and (count > 0)):
            asyncore.loop(timeout=0.01, count=1, use_poll=self.use_poll)
            if instance.flag:
                return
            count -= 1
            time.sleep(timeout)
        self.fail('flag not set')

    def test_handle_connect(self):

        class TestClient(BaseClient):

            def handle_connect(self):
                self.flag = True
        server = BaseServer(self.family, self.addr)
        client = TestClient(self.family, server.address)
        self.loop_waiting_for_flag(client)

    def test_handle_accept(self):

        class TestListener(BaseTestHandler):

            def __init__(self, family, addr):
                BaseTestHandler.__init__(self)
                self.create_socket(family)
                bind_af_aware(self.socket, addr)
                self.listen(5)
                self.address = self.socket.getsockname()

            def handle_accept(self):
                self.flag = True
        server = TestListener(self.family, self.addr)
        client = BaseClient(self.family, server.address)
        self.loop_waiting_for_flag(server)

    def test_handle_accepted(self):

        class TestListener(BaseTestHandler):

            def __init__(self, family, addr):
                BaseTestHandler.__init__(self)
                self.create_socket(family)
                bind_af_aware(self.socket, addr)
                self.listen(5)
                self.address = self.socket.getsockname()

            def handle_accept(self):
                asyncore.dispatcher.handle_accept(self)

            def handle_accepted(self, sock, addr):
                sock.close()
                self.flag = True
        server = TestListener(self.family, self.addr)
        client = BaseClient(self.family, server.address)
        self.loop_waiting_for_flag(server)

    def test_handle_read(self):

        class TestClient(BaseClient):

            def handle_read(self):
                self.flag = True

        class TestHandler(BaseTestHandler):

            def __init__(self, conn):
                BaseTestHandler.__init__(self, conn)
                self.send((b'x' * 1024))
        server = BaseServer(self.family, self.addr, TestHandler)
        client = TestClient(self.family, server.address)
        self.loop_waiting_for_flag(client)

    def test_handle_write(self):

        class TestClient(BaseClient):

            def handle_write(self):
                self.flag = True
        server = BaseServer(self.family, self.addr)
        client = TestClient(self.family, server.address)
        self.loop_waiting_for_flag(client)

    def test_handle_close(self):

        class TestClient(BaseClient):

            def handle_read(self):
                self.recv(1024)

            def handle_close(self):
                self.flag = True
                self.close()

        class TestHandler(BaseTestHandler):

            def __init__(self, conn):
                BaseTestHandler.__init__(self, conn)
                self.close()
        server = BaseServer(self.family, self.addr, TestHandler)
        client = TestClient(self.family, server.address)
        self.loop_waiting_for_flag(client)

    def test_handle_close_after_conn_broken(self):
        data = (b'\x00' * 128)

        class TestClient(BaseClient):

            def handle_write(self):
                self.send(data)

            def handle_close(self):
                self.flag = True
                self.close()

            def handle_expt(self):
                self.flag = True
                self.close()

        class TestHandler(BaseTestHandler):

            def handle_read(self):
                self.recv(len(data))
                self.close()

            def writable(self):
                return False
        server = BaseServer(self.family, self.addr, TestHandler)
        client = TestClient(self.family, server.address)
        self.loop_waiting_for_flag(client)

    @unittest.skipIf(sys.platform.startswith('sunos'), 'OOB support is broken on Solaris')
    def test_handle_expt(self):
        if (HAS_UNIX_SOCKETS and (self.family == socket.AF_UNIX)):
            self.skipTest('Not applicable to AF_UNIX sockets.')
        if ((sys.platform == 'darwin') and self.use_poll):
            self.skipTest('poll may fail on macOS; see issue #28087')

        class TestClient(BaseClient):

            def handle_expt(self):
                self.socket.recv(1024, socket.MSG_OOB)
                self.flag = True

        class TestHandler(BaseTestHandler):

            def __init__(self, conn):
                BaseTestHandler.__init__(self, conn)
                self.socket.send(bytes(chr(244), 'latin-1'), socket.MSG_OOB)
        server = BaseServer(self.family, self.addr, TestHandler)
        client = TestClient(self.family, server.address)
        self.loop_waiting_for_flag(client)

    def test_handle_error(self):

        class TestClient(BaseClient):

            def handle_write(self):
                (1.0 / 0)

            def handle_error(self):
                self.flag = True
                try:
                    raise
                except ZeroDivisionError:
                    pass
                else:
                    raise Exception('exception not raised')
        server = BaseServer(self.family, self.addr)
        client = TestClient(self.family, server.address)
        self.loop_waiting_for_flag(client)

    def test_connection_attributes(self):
        server = BaseServer(self.family, self.addr)
        client = BaseClient(self.family, server.address)
        self.assertFalse(server.connected)
        self.assertTrue(server.accepting)
        self.assertFalse(client.accepting)
        asyncore.loop(timeout=0.01, use_poll=self.use_poll, count=100)
        self.assertFalse(server.connected)
        self.assertTrue(server.accepting)
        self.assertTrue(client.connected)
        self.assertFalse(client.accepting)
        client.close()
        self.assertFalse(server.connected)
        self.assertTrue(server.accepting)
        self.assertFalse(client.connected)
        self.assertFalse(client.accepting)
        server.close()
        self.assertFalse(server.connected)
        self.assertFalse(server.accepting)

    def test_create_socket(self):
        s = asyncore.dispatcher()
        s.create_socket(self.family)
        self.assertEqual(s.socket.type, socket.SOCK_STREAM)
        self.assertEqual(s.socket.family, self.family)
        self.assertEqual(s.socket.gettimeout(), 0)
        self.assertFalse(s.socket.get_inheritable())

    def test_bind(self):
        if (HAS_UNIX_SOCKETS and (self.family == socket.AF_UNIX)):
            self.skipTest('Not applicable to AF_UNIX sockets.')
        s1 = asyncore.dispatcher()
        s1.create_socket(self.family)
        s1.bind(self.addr)
        s1.listen(5)
        port = s1.socket.getsockname()[1]
        s2 = asyncore.dispatcher()
        s2.create_socket(self.family)
        self.assertRaises(OSError, s2.bind, (self.addr[0], port))

    def test_set_reuse_addr(self):
        if (HAS_UNIX_SOCKETS and (self.family == socket.AF_UNIX)):
            self.skipTest('Not applicable to AF_UNIX sockets.')
        with socket.socket(self.family) as sock:
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except OSError:
                unittest.skip('SO_REUSEADDR not supported on this platform')
            else:
                s = asyncore.dispatcher(socket.socket(self.family))
                self.assertFalse(s.socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR))
                s.socket.close()
                s.create_socket(self.family)
                s.set_reuse_addr()
                self.assertTrue(s.socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR))

    @threading_helper.reap_threads
    def test_quick_connect(self):
        if (self.family not in (socket.AF_INET, getattr(socket, 'AF_INET6', object()))):
            self.skipTest('test specific to AF_INET and AF_INET6')
        server = BaseServer(self.family, self.addr)
        t = threading.Thread(target=(lambda : asyncore.loop(timeout=0.1, count=5)))
        t.start()
        try:
            with socket.socket(self.family, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
                try:
                    s.connect(server.address)
                except OSError:
                    pass
        finally:
            threading_helper.join_thread(t)

class TestAPI_UseIPv4Sockets(BaseTestAPI):
    family = socket.AF_INET
    addr = (socket_helper.HOST, 0)

@unittest.skipUnless(socket_helper.IPV6_ENABLED, 'IPv6 support required')
class TestAPI_UseIPv6Sockets(BaseTestAPI):
    family = socket.AF_INET6
    addr = (socket_helper.HOSTv6, 0)

@unittest.skipUnless(HAS_UNIX_SOCKETS, 'Unix sockets required')
class TestAPI_UseUnixSockets(BaseTestAPI):
    if HAS_UNIX_SOCKETS:
        family = socket.AF_UNIX
    addr = os_helper.TESTFN

    def tearDown(self):
        os_helper.unlink(self.addr)
        BaseTestAPI.tearDown(self)

class TestAPI_UseIPv4Select(TestAPI_UseIPv4Sockets, unittest.TestCase):
    use_poll = False

@unittest.skipUnless(hasattr(select, 'poll'), 'select.poll required')
class TestAPI_UseIPv4Poll(TestAPI_UseIPv4Sockets, unittest.TestCase):
    use_poll = True

class TestAPI_UseIPv6Select(TestAPI_UseIPv6Sockets, unittest.TestCase):
    use_poll = False

@unittest.skipUnless(hasattr(select, 'poll'), 'select.poll required')
class TestAPI_UseIPv6Poll(TestAPI_UseIPv6Sockets, unittest.TestCase):
    use_poll = True

class TestAPI_UseUnixSocketsSelect(TestAPI_UseUnixSockets, unittest.TestCase):
    use_poll = False

@unittest.skipUnless(hasattr(select, 'poll'), 'select.poll required')
class TestAPI_UseUnixSocketsPoll(TestAPI_UseUnixSockets, unittest.TestCase):
    use_poll = True
if (__name__ == '__main__'):
    unittest.main()
