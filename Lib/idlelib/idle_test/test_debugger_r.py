
'Test debugger_r, coverage 30%.'
from idlelib import debugger_r
import unittest
from test.support import requires
from tkinter import Tk

class Test(unittest.TestCase):

    def test_init(self):
        self.assertTrue(True)
if (__name__ == '__main__'):
    unittest.main(verbosity=2)
