
import os
import unittest
import collections
import email
from email.message import Message
from email._policybase import compat32
from test.support import load_package_tests
from test.test_email import __file__ as landmark

def load_tests(*args):
    return load_package_tests(os.path.dirname(__file__), *args)

def openfile(filename, *args, **kws):
    path = os.path.join(os.path.dirname(landmark), 'data', filename)
    return open(path, *args, **kws)

class TestEmailBase(unittest.TestCase):
    maxDiff = None
    policy = compat32
    message = Message

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.addTypeEqualityFunc(bytes, self.assertBytesEqual)
    ndiffAssertEqual = unittest.TestCase.assertEqual

    def _msgobj(self, filename):
        with openfile(filename) as fp:
            return email.message_from_file(fp, policy=self.policy)

    def _str_msg(self, string, message=None, policy=None):
        if (policy is None):
            policy = self.policy
        if (message is None):
            message = self.message
        return email.message_from_string(string, message, policy=policy)

    def _bytes_msg(self, bytestring, message=None, policy=None):
        if (policy is None):
            policy = self.policy
        if (message is None):
            message = self.message
        return email.message_from_bytes(bytestring, message, policy=policy)

    def _make_message(self):
        return self.message(policy=self.policy)

    def _bytes_repr(self, b):
        return [repr(x) for x in b.splitlines(keepends=True)]

    def assertBytesEqual(self, first, second, msg):
        'Our byte strings are really encoded strings; improve diff output'
        self.assertEqual(self._bytes_repr(first), self._bytes_repr(second))

    def assertDefectsEqual(self, actual, expected):
        self.assertEqual(len(actual), len(expected), actual)
        for i in range(len(actual)):
            self.assertIsInstance(actual[i], expected[i], 'item {}'.format(i))

def parameterize(cls):
    "A test method parameterization class decorator.\n\n    Parameters are specified as the value of a class attribute that ends with\n    the string '_params'.  Call the portion before '_params' the prefix.  Then\n    a method to be parameterized must have the same prefix, the string\n    '_as_', and an arbitrary suffix.\n\n    The value of the _params attribute may be either a dictionary or a list.\n    The values in the dictionary and the elements of the list may either be\n    single values, or a list.  If single values, they are turned into single\n    element tuples.  However derived, the resulting sequence is passed via\n    *args to the parameterized test function.\n\n    In a _params dictionary, the keys become part of the name of the generated\n    tests.  In a _params list, the values in the list are converted into a\n    string by joining the string values of the elements of the tuple by '_' and\n    converting any blanks into '_'s, and this become part of the name.\n    The  full name of a generated test is a 'test_' prefix, the portion of the\n    test function name after the  '_as_' separator, plus an '_', plus the name\n    derived as explained above.\n\n    For example, if we have:\n\n        count_params = range(2)\n\n        def count_as_foo_arg(self, foo):\n            self.assertEqual(foo+1, myfunc(foo))\n\n    we will get parameterized test methods named:\n        test_foo_arg_0\n        test_foo_arg_1\n        test_foo_arg_2\n\n    Or we could have:\n\n        example_params = {'foo': ('bar', 1), 'bing': ('bang', 2)}\n\n        def example_as_myfunc_input(self, name, count):\n            self.assertEqual(name+str(count), myfunc(name, count))\n\n    and get:\n        test_myfunc_input_foo\n        test_myfunc_input_bing\n\n    Note: if and only if the generated test name is a valid identifier can it\n    be used to select the test individually from the unittest command line.\n\n    The values in the params dict can be a single value, a tuple, or a\n    dict.  If a single value of a tuple, it is passed to the test function\n    as positional arguments.  If a dict, it is a passed via **kw.\n\n    "
    paramdicts = {}
    testers = collections.defaultdict(list)
    for (name, attr) in cls.__dict__.items():
        if name.endswith('_params'):
            if (not hasattr(attr, 'keys')):
                d = {}
                for x in attr:
                    if (not hasattr(x, '__iter__')):
                        x = (x,)
                    n = '_'.join((str(v) for v in x)).replace(' ', '_')
                    d[n] = x
                attr = d
            paramdicts[(name[:(- 7)] + '_as_')] = attr
        if ('_as_' in name):
            testers[(name.split('_as_')[0] + '_as_')].append(name)
    testfuncs = {}
    for name in paramdicts:
        if (name not in testers):
            raise ValueError('No tester found for {}'.format(name))
    for name in testers:
        if (name not in paramdicts):
            raise ValueError('No params found for {}'.format(name))
    for (name, attr) in cls.__dict__.items():
        for (paramsname, paramsdict) in paramdicts.items():
            if name.startswith(paramsname):
                testnameroot = ('test_' + name[len(paramsname):])
                for (paramname, params) in paramsdict.items():
                    if hasattr(params, 'keys'):
                        test = (lambda self, name=name, params=params: getattr(self, name)(**params))
                    else:
                        test = (lambda self, name=name, params=params: getattr(self, name)(*params))
                    testname = ((testnameroot + '_') + paramname)
                    test.__name__ = testname
                    testfuncs[testname] = test
    for (key, value) in testfuncs.items():
        setattr(cls, key, value)
    return cls
