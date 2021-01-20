
'This test case provides support for checking forking and wait behavior.\n\nTo test different wait behavior, override the wait_impl method.\n\nWe want fork1() semantics -- only the forking thread survives in the\nchild after a fork().\n\nOn some systems (e.g. Solaris without posix threads) we find that all\nactive threads survive in the child after a fork(); this is an error.\n'
import os, sys, time, unittest
import threading
from test import support
from test.support import threading_helper
LONGSLEEP = 2
SHORTSLEEP = 0.5
NUM_THREADS = 4

class ForkWait(unittest.TestCase):

    def setUp(self):
        self._threading_key = threading_helper.threading_setup()
        self.alive = {}
        self.stop = 0
        self.threads = []

    def tearDown(self):
        self.stop = 1
        for thread in self.threads:
            thread.join()
        thread = None
        self.threads.clear()
        threading_helper.threading_cleanup(*self._threading_key)

    def f(self, id):
        while (not self.stop):
            self.alive[id] = os.getpid()
            try:
                time.sleep(SHORTSLEEP)
            except OSError:
                pass

    def wait_impl(self, cpid, *, exitcode):
        support.wait_process(cpid, exitcode=exitcode)

    def test_wait(self):
        for i in range(NUM_THREADS):
            thread = threading.Thread(target=self.f, args=(i,))
            thread.start()
            self.threads.append(thread)
        deadline = (time.monotonic() + support.SHORT_TIMEOUT)
        while (len(self.alive) < NUM_THREADS):
            time.sleep(0.1)
            if (deadline < time.monotonic()):
                break
        a = sorted(self.alive.keys())
        self.assertEqual(a, list(range(NUM_THREADS)))
        prefork_lives = self.alive.copy()
        if (sys.platform in ['unixware7']):
            cpid = os.fork1()
        else:
            cpid = os.fork()
        if (cpid == 0):
            time.sleep(LONGSLEEP)
            n = 0
            for key in self.alive:
                if (self.alive[key] != prefork_lives[key]):
                    n += 1
            os._exit(n)
        else:
            self.wait_impl(cpid, exitcode=0)
