
import copy
import os
import sys
import unittest
import pickle
import weakref
import errno
from test.support import captured_stderr, check_impl_detail, cpython_only, gc_collect, no_tracing, script_helper, SuppressCrashReport
from test.support.import_helper import import_module
from test.support.os_helper import TESTFN, unlink
from test.support.warnings_helper import check_warnings
from test import support

class NaiveException(Exception):

    def __init__(self, x):
        self.x = x

class SlottedNaiveException(Exception):
    __slots__ = ('x',)

    def __init__(self, x):
        self.x = x

class BrokenStrException(Exception):

    def __str__(self):
        raise Exception('str() is broken')

class ExceptionTests(unittest.TestCase):

    def raise_catch(self, exc, excname):
        with self.subTest(exc=exc, excname=excname):
            try:
                raise exc('spam')
            except exc as err:
                buf1 = str(err)
            try:
                raise exc('spam')
            except exc as err:
                buf2 = str(err)
            self.assertEqual(buf1, buf2)
            self.assertEqual(exc.__name__, excname)

    def testRaising(self):
        self.raise_catch(AttributeError, 'AttributeError')
        self.assertRaises(AttributeError, getattr, sys, 'undefined_attribute')
        self.raise_catch(EOFError, 'EOFError')
        fp = open(TESTFN, 'w')
        fp.close()
        fp = open(TESTFN, 'r')
        savestdin = sys.stdin
        try:
            try:
                import marshal
                marshal.loads(b'')
            except EOFError:
                pass
        finally:
            sys.stdin = savestdin
            fp.close()
            unlink(TESTFN)
        self.raise_catch(OSError, 'OSError')
        self.assertRaises(OSError, open, 'this file does not exist', 'r')
        self.raise_catch(ImportError, 'ImportError')
        self.assertRaises(ImportError, __import__, 'undefined_module')
        self.raise_catch(IndexError, 'IndexError')
        x = []
        self.assertRaises(IndexError, x.__getitem__, 10)
        self.raise_catch(KeyError, 'KeyError')
        x = {}
        self.assertRaises(KeyError, x.__getitem__, 'key')
        self.raise_catch(KeyboardInterrupt, 'KeyboardInterrupt')
        self.raise_catch(MemoryError, 'MemoryError')
        self.raise_catch(NameError, 'NameError')
        try:
            x = undefined_variable
        except NameError:
            pass
        self.raise_catch(OverflowError, 'OverflowError')
        x = 1
        for dummy in range(128):
            x += x
        self.raise_catch(RuntimeError, 'RuntimeError')
        self.raise_catch(RecursionError, 'RecursionError')
        self.raise_catch(SyntaxError, 'SyntaxError')
        try:
            exec('/\n')
        except SyntaxError:
            pass
        self.raise_catch(IndentationError, 'IndentationError')
        self.raise_catch(TabError, 'TabError')
        try:
            compile('try:\n\t1/0\n    \t1/0\nfinally:\n pass\n', '<string>', 'exec')
        except TabError:
            pass
        else:
            self.fail('TabError not raised')
        self.raise_catch(SystemError, 'SystemError')
        self.raise_catch(SystemExit, 'SystemExit')
        self.assertRaises(SystemExit, sys.exit, 0)
        self.raise_catch(TypeError, 'TypeError')
        try:
            ([] + ())
        except TypeError:
            pass
        self.raise_catch(ValueError, 'ValueError')
        self.assertRaises(ValueError, chr, (17 << 16))
        self.raise_catch(ZeroDivisionError, 'ZeroDivisionError')
        try:
            x = (1 / 0)
        except ZeroDivisionError:
            pass
        self.raise_catch(Exception, 'Exception')
        try:
            x = (1 / 0)
        except Exception as e:
            pass
        self.raise_catch(StopAsyncIteration, 'StopAsyncIteration')

    def testSyntaxErrorMessage(self):

        def ckmsg(src, msg):
            with self.subTest(src=src, msg=msg):
                try:
                    compile(src, '<fragment>', 'exec')
                except SyntaxError as e:
                    if (e.msg != msg):
                        self.fail(('expected %s, got %s' % (msg, e.msg)))
                else:
                    self.fail('failed to get expected SyntaxError')
        s = 'if 1:\n        try:\n            continue\n        except:\n            pass'
        ckmsg(s, "'continue' not properly in loop")
        ckmsg('continue\n', "'continue' not properly in loop")

    def testSyntaxErrorMissingParens(self):

        def ckmsg(src, msg, exception=SyntaxError):
            try:
                compile(src, '<fragment>', 'exec')
            except exception as e:
                if (e.msg != msg):
                    self.fail(('expected %s, got %s' % (msg, e.msg)))
            else:
                self.fail('failed to get expected SyntaxError')
        s = 'print "old style"'
        ckmsg(s, 'Missing parentheses in call to \'print\'. Did you mean print("old style")?')
        s = 'print "old style",'
        ckmsg(s, 'Missing parentheses in call to \'print\'. Did you mean print("old style", end=" ")?')
        s = 'exec "old style"'
        ckmsg(s, "Missing parentheses in call to 'exec'")
        s = 'if True:\nprint "No indent"'
        ckmsg(s, 'expected an indented block', IndentationError)
        s = 'if True:\n        print()\n\texec "mixed tabs and spaces"'
        ckmsg(s, 'inconsistent use of tabs and spaces in indentation', TabError)

    def check(self, src, lineno, offset, encoding='utf-8'):
        with self.subTest(source=src, lineno=lineno, offset=offset):
            with self.assertRaises(SyntaxError) as cm:
                compile(src, '<fragment>', 'exec')
            self.assertEqual(cm.exception.lineno, lineno)
            self.assertEqual(cm.exception.offset, offset)
            if (cm.exception.text is not None):
                if (not isinstance(src, str)):
                    src = src.decode(encoding, 'replace')
                line = src.split('\n')[(lineno - 1)]
                self.assertIn(line, cm.exception.text)

    def testSyntaxErrorOffset(self):
        check = self.check
        check('def fact(x):\n\treturn x!\n', 2, 10)
        check('1 +\n', 1, 4)
        check('def spam():\n  print(1)\n print(2)', 3, 10)
        check('Python = "Python" +', 1, 20)
        check('Python = "Ṕýţĥòñ" +', 1, 20)
        check(b'# -*- coding: cp1251 -*-\nPython = "\xcf\xb3\xf2\xee\xed" +', 2, 19, encoding='cp1251')
        check(b'Python = "\xcf\xb3\xf2\xee\xed" +', 1, 18)
        check('x = "a', 1, 7)
        check('lambda x: x = 2', 1, 1)
        check('class foo:return 1', 1, 11)
        check('def f():\n  continue', 2, 3)
        check('def f():\n  break', 2, 3)
        check('try:\n  pass\nexcept:\n  pass\nexcept ValueError:\n  pass', 2, 3)
        check('(0x+1)', 1, 3)
        check('x = 0xI', 1, 6)
        check('0010 + 2', 1, 4)
        check('x = 32e-+4', 1, 8)
        check('x = 0o9', 1, 6)
        check('α = 0xI', 1, 6)
        check(b'\xce\xb1 = 0xI', 1, 6)
        check(b'# -*- coding: iso8859-7 -*-\n\xe1 = 0xI', 2, 6, encoding='iso8859-7')
        check(b"if 1:\n            def foo():\n                '''\n\n            def bar():\n                pass\n\n            def baz():\n                '''quux'''\n            ", 9, 20)
        check('pass\npass\npass\n(1+)\npass\npass\npass', 4, 4)
        check('(1+)', 1, 4)
        check('x = [(yield i) for i in range(3)]', 1, 5)
        check('def f():\n  from _ import *', 1, 1)
        check('def f(x, x):\n  pass', 1, 1)
        check('def f(x):\n  nonlocal x', 2, 3)
        check('def f(x):\n  x = 1\n  global x', 3, 3)
        check('nonlocal x', 1, 1)
        check('def f():\n  global x\n  nonlocal x', 2, 3)
        check('from __future__ import doesnt_exist', 1, 1)
        check('from __future__ import braces', 1, 1)
        check('x=1\nfrom __future__ import division', 2, 1)
        check('foo(1=2)', 1, 5)
        check('def f():\n  x, y: int', 2, 3)
        check('[*x for x in xs]', 1, 2)
        check('foo(x for x in range(10), 100)', 1, 5)
        check('for 1 in []: pass', 1, 5)
        check('(yield i) = 2', 1, 2)
        check('def f(*):\n  pass', 1, 8)

    @cpython_only
    def testSettingException(self):

        class BadException(Exception):

            def __init__(self_):
                raise RuntimeError("can't instantiate BadException")

        class InvalidException():
            pass

        def test_capi1():
            import _testcapi
            try:
                _testcapi.raise_exception(BadException, 1)
            except TypeError as err:
                (exc, err, tb) = sys.exc_info()
                co = tb.tb_frame.f_code
                self.assertEqual(co.co_name, 'test_capi1')
                self.assertTrue(co.co_filename.endswith('test_exceptions.py'))
            else:
                self.fail('Expected exception')

        def test_capi2():
            import _testcapi
            try:
                _testcapi.raise_exception(BadException, 0)
            except RuntimeError as err:
                (exc, err, tb) = sys.exc_info()
                co = tb.tb_frame.f_code
                self.assertEqual(co.co_name, '__init__')
                self.assertTrue(co.co_filename.endswith('test_exceptions.py'))
                co2 = tb.tb_frame.f_back.f_code
                self.assertEqual(co2.co_name, 'test_capi2')
            else:
                self.fail('Expected exception')

        def test_capi3():
            import _testcapi
            self.assertRaises(SystemError, _testcapi.raise_exception, InvalidException, 1)
        if (not sys.platform.startswith('java')):
            test_capi1()
            test_capi2()
            test_capi3()

    def test_WindowsError(self):
        try:
            WindowsError
        except NameError:
            pass
        else:
            self.assertIs(WindowsError, OSError)
            self.assertEqual(str(OSError(1001)), '1001')
            self.assertEqual(str(OSError(1001, 'message')), '[Errno 1001] message')
            w = OSError(9, 'foo', 'bar')
            self.assertEqual(w.errno, 9)
            self.assertEqual(w.winerror, None)
            self.assertEqual(str(w), "[Errno 9] foo: 'bar'")
            w = OSError(0, 'foo', 'bar', 3)
            self.assertEqual(w.errno, 2)
            self.assertEqual(w.winerror, 3)
            self.assertEqual(w.strerror, 'foo')
            self.assertEqual(w.filename, 'bar')
            self.assertEqual(w.filename2, None)
            self.assertEqual(str(w), "[WinError 3] foo: 'bar'")
            w = OSError(0, 'foo', None, 1001)
            self.assertEqual(w.errno, 22)
            self.assertEqual(w.winerror, 1001)
            self.assertEqual(w.strerror, 'foo')
            self.assertEqual(w.filename, None)
            self.assertEqual(w.filename2, None)
            self.assertEqual(str(w), '[WinError 1001] foo')
            w = OSError('bar', 'foo')
            self.assertEqual(w.errno, 'bar')
            self.assertEqual(w.winerror, None)
            self.assertEqual(w.strerror, 'foo')
            self.assertEqual(w.filename, None)
            self.assertEqual(w.filename2, None)

    @unittest.skipUnless((sys.platform == 'win32'), 'test specific to Windows')
    def test_windows_message(self):
        'Should fill in unknown error code in Windows error message'
        ctypes = import_module('ctypes')
        code = 3765269347
        with self.assertRaisesRegex(OSError, ('Windows Error 0x%x' % code)):
            ctypes.pythonapi.PyErr_SetFromWindowsErr(code)

    def testAttributes(self):
        exceptionList = [(BaseException, (), {'args': ()}), (BaseException, (1,), {'args': (1,)}), (BaseException, ('foo',), {'args': ('foo',)}), (BaseException, ('foo', 1), {'args': ('foo', 1)}), (SystemExit, ('foo',), {'args': ('foo',), 'code': 'foo'}), (OSError, ('foo',), {'args': ('foo',), 'filename': None, 'filename2': None, 'errno': None, 'strerror': None}), (OSError, ('foo', 'bar'), {'args': ('foo', 'bar'), 'filename': None, 'filename2': None, 'errno': 'foo', 'strerror': 'bar'}), (OSError, ('foo', 'bar', 'baz'), {'args': ('foo', 'bar'), 'filename': 'baz', 'filename2': None, 'errno': 'foo', 'strerror': 'bar'}), (OSError, ('foo', 'bar', 'baz', None, 'quux'), {'args': ('foo', 'bar'), 'filename': 'baz', 'filename2': 'quux'}), (OSError, ('errnoStr', 'strErrorStr', 'filenameStr'), {'args': ('errnoStr', 'strErrorStr'), 'strerror': 'strErrorStr', 'errno': 'errnoStr', 'filename': 'filenameStr'}), (OSError, (1, 'strErrorStr', 'filenameStr'), {'args': (1, 'strErrorStr'), 'errno': 1, 'strerror': 'strErrorStr', 'filename': 'filenameStr', 'filename2': None}), (SyntaxError, (), {'msg': None, 'text': None, 'filename': None, 'lineno': None, 'offset': None, 'print_file_and_line': None}), (SyntaxError, ('msgStr',), {'args': ('msgStr',), 'text': None, 'print_file_and_line': None, 'msg': 'msgStr', 'filename': None, 'lineno': None, 'offset': None}), (SyntaxError, ('msgStr', ('filenameStr', 'linenoStr', 'offsetStr', 'textStr')), {'offset': 'offsetStr', 'text': 'textStr', 'args': ('msgStr', ('filenameStr', 'linenoStr', 'offsetStr', 'textStr')), 'print_file_and_line': None, 'msg': 'msgStr', 'filename': 'filenameStr', 'lineno': 'linenoStr'}), (SyntaxError, ('msgStr', 'filenameStr', 'linenoStr', 'offsetStr', 'textStr', 'print_file_and_lineStr'), {'text': None, 'args': ('msgStr', 'filenameStr', 'linenoStr', 'offsetStr', 'textStr', 'print_file_and_lineStr'), 'print_file_and_line': None, 'msg': 'msgStr', 'filename': None, 'lineno': None, 'offset': None}), (UnicodeError, (), {'args': ()}), (UnicodeEncodeError, ('ascii', 'a', 0, 1, 'ordinal not in range'), {'args': ('ascii', 'a', 0, 1, 'ordinal not in range'), 'encoding': 'ascii', 'object': 'a', 'start': 0, 'reason': 'ordinal not in range'}), (UnicodeDecodeError, ('ascii', bytearray(b'\xff'), 0, 1, 'ordinal not in range'), {'args': ('ascii', bytearray(b'\xff'), 0, 1, 'ordinal not in range'), 'encoding': 'ascii', 'object': b'\xff', 'start': 0, 'reason': 'ordinal not in range'}), (UnicodeDecodeError, ('ascii', b'\xff', 0, 1, 'ordinal not in range'), {'args': ('ascii', b'\xff', 0, 1, 'ordinal not in range'), 'encoding': 'ascii', 'object': b'\xff', 'start': 0, 'reason': 'ordinal not in range'}), (UnicodeTranslateError, ('あ', 0, 1, 'ouch'), {'args': ('あ', 0, 1, 'ouch'), 'object': 'あ', 'reason': 'ouch', 'start': 0, 'end': 1}), (NaiveException, ('foo',), {'args': ('foo',), 'x': 'foo'}), (SlottedNaiveException, ('foo',), {'args': ('foo',), 'x': 'foo'})]
        try:
            exceptionList.append((WindowsError, (1, 'strErrorStr', 'filenameStr'), {'args': (1, 'strErrorStr'), 'strerror': 'strErrorStr', 'winerror': None, 'errno': 1, 'filename': 'filenameStr', 'filename2': None}))
        except NameError:
            pass
        for (exc, args, expected) in exceptionList:
            try:
                e = exc(*args)
            except:
                print(('\nexc=%r, args=%r' % (exc, args)), file=sys.stderr)
                raise
            else:
                if (not type(e).__name__.endswith('NaiveException')):
                    self.assertEqual(type(e).__module__, 'builtins')
                s = str(e)
                for checkArgName in expected:
                    value = getattr(e, checkArgName)
                    self.assertEqual(repr(value), repr(expected[checkArgName]), ('%r.%s == %r, expected %r' % (e, checkArgName, value, expected[checkArgName])))
                for p in [pickle]:
                    for protocol in range((p.HIGHEST_PROTOCOL + 1)):
                        s = p.dumps(e, protocol)
                        new = p.loads(s)
                        for checkArgName in expected:
                            got = repr(getattr(new, checkArgName))
                            want = repr(expected[checkArgName])
                            self.assertEqual(got, want, ('pickled "%r", attribute "%s' % (e, checkArgName)))

    def testWithTraceback(self):
        try:
            raise IndexError(4)
        except:
            tb = sys.exc_info()[2]
        e = BaseException().with_traceback(tb)
        self.assertIsInstance(e, BaseException)
        self.assertEqual(e.__traceback__, tb)
        e = IndexError(5).with_traceback(tb)
        self.assertIsInstance(e, IndexError)
        self.assertEqual(e.__traceback__, tb)

        class MyException(Exception):
            pass
        e = MyException().with_traceback(tb)
        self.assertIsInstance(e, MyException)
        self.assertEqual(e.__traceback__, tb)

    def testInvalidTraceback(self):
        try:
            Exception().__traceback__ = 5
        except TypeError as e:
            self.assertIn('__traceback__ must be a traceback', str(e))
        else:
            self.fail('No exception raised')

    def testInvalidAttrs(self):
        self.assertRaises(TypeError, setattr, Exception(), '__cause__', 1)
        self.assertRaises(TypeError, delattr, Exception(), '__cause__')
        self.assertRaises(TypeError, setattr, Exception(), '__context__', 1)
        self.assertRaises(TypeError, delattr, Exception(), '__context__')

    def testNoneClearsTracebackAttr(self):
        try:
            raise IndexError(4)
        except:
            tb = sys.exc_info()[2]
        e = Exception()
        e.__traceback__ = tb
        e.__traceback__ = None
        self.assertEqual(e.__traceback__, None)

    def testChainingAttrs(self):
        e = Exception()
        self.assertIsNone(e.__context__)
        self.assertIsNone(e.__cause__)
        e = TypeError()
        self.assertIsNone(e.__context__)
        self.assertIsNone(e.__cause__)

        class MyException(OSError):
            pass
        e = MyException()
        self.assertIsNone(e.__context__)
        self.assertIsNone(e.__cause__)

    def testChainingDescriptors(self):
        try:
            raise Exception()
        except Exception as exc:
            e = exc
        self.assertIsNone(e.__context__)
        self.assertIsNone(e.__cause__)
        self.assertFalse(e.__suppress_context__)
        e.__context__ = NameError()
        e.__cause__ = None
        self.assertIsInstance(e.__context__, NameError)
        self.assertIsNone(e.__cause__)
        self.assertTrue(e.__suppress_context__)
        e.__suppress_context__ = False
        self.assertFalse(e.__suppress_context__)

    def testKeywordArgs(self):
        self.assertRaises(TypeError, BaseException, a=1)

        class DerivedException(BaseException):

            def __init__(self, fancy_arg):
                BaseException.__init__(self)
                self.fancy_arg = fancy_arg
        x = DerivedException(fancy_arg=42)
        self.assertEqual(x.fancy_arg, 42)

    @no_tracing
    def testInfiniteRecursion(self):

        def f():
            return f()
        self.assertRaises(RecursionError, f)

        def g():
            try:
                return g()
            except ValueError:
                return (- 1)
        self.assertRaises(RecursionError, g)

    def test_str(self):
        self.assertTrue(str(Exception))
        self.assertTrue(str(Exception('a')))
        self.assertTrue(str(Exception('a', 'b')))

    def testExceptionCleanupNames(self):
        try:
            raise Exception()
        except Exception as e:
            self.assertTrue(e)
            del e
        self.assertNotIn('e', locals())

    def testExceptionCleanupState(self):

        class MyException(Exception):

            def __init__(self, obj):
                self.obj = obj

        class MyObj():
            pass

        def inner_raising_func():
            local_ref = obj
            raise MyException(obj)
        obj = MyObj()
        wr = weakref.ref(obj)
        try:
            inner_raising_func()
        except MyException as e:
            pass
        obj = None
        obj = wr()
        self.assertIsNone(obj)
        obj = MyObj()
        wr = weakref.ref(obj)
        try:
            inner_raising_func()
        except MyException:
            pass
        obj = None
        obj = wr()
        self.assertIsNone(obj)
        obj = MyObj()
        wr = weakref.ref(obj)
        try:
            inner_raising_func()
        except:
            pass
        obj = None
        obj = wr()
        self.assertIsNone(obj)
        obj = MyObj()
        wr = weakref.ref(obj)
        for i in [0]:
            try:
                inner_raising_func()
            except:
                break
        obj = None
        obj = wr()
        self.assertIsNone(obj)
        obj = MyObj()
        wr = weakref.ref(obj)
        try:
            try:
                inner_raising_func()
            except:
                raise KeyError
        except KeyError as e:
            e.__context__ = None
            obj = None
            obj = wr()
            if check_impl_detail(cpython=False):
                gc_collect()
            self.assertIsNone(obj)
        obj = MyObj()
        wr = weakref.ref(obj)
        try:
            inner_raising_func()
        except MyException:
            try:
                try:
                    raise
                finally:
                    raise
            except MyException:
                pass
        obj = None
        if check_impl_detail(cpython=False):
            gc_collect()
        obj = wr()
        self.assertIsNone(obj)

        class Context():

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, exc_tb):
                return True
        obj = MyObj()
        wr = weakref.ref(obj)
        with Context():
            inner_raising_func()
        obj = None
        if check_impl_detail(cpython=False):
            gc_collect()
        obj = wr()
        self.assertIsNone(obj)

    def test_exception_target_in_nested_scope(self):

        def print_error():
            e
        try:
            something
        except Exception as e:
            print_error()

    def test_generator_leaking(self):

        def yield_raise():
            try:
                raise KeyError('caught')
            except KeyError:
                (yield sys.exc_info()[0])
                (yield sys.exc_info()[0])
            (yield sys.exc_info()[0])
        g = yield_raise()
        self.assertEqual(next(g), KeyError)
        self.assertEqual(sys.exc_info()[0], None)
        self.assertEqual(next(g), KeyError)
        self.assertEqual(sys.exc_info()[0], None)
        self.assertEqual(next(g), None)
        try:
            raise TypeError('foo')
        except TypeError:
            g = yield_raise()
            self.assertEqual(next(g), KeyError)
            self.assertEqual(sys.exc_info()[0], TypeError)
            self.assertEqual(next(g), KeyError)
            self.assertEqual(sys.exc_info()[0], TypeError)
            self.assertEqual(next(g), TypeError)
            del g
            self.assertEqual(sys.exc_info()[0], TypeError)

    def test_generator_leaking2(self):

        def g():
            (yield)
        try:
            raise RuntimeError
        except RuntimeError:
            it = g()
            next(it)
        try:
            next(it)
        except StopIteration:
            pass
        self.assertEqual(sys.exc_info(), (None, None, None))

    def test_generator_leaking3(self):

        def g():
            try:
                (yield)
            except ZeroDivisionError:
                (yield sys.exc_info()[1])
        it = g()
        next(it)
        try:
            (1 / 0)
        except ZeroDivisionError as e:
            self.assertIs(sys.exc_info()[1], e)
            gen_exc = it.throw(e)
            self.assertIs(sys.exc_info()[1], e)
            self.assertIs(gen_exc, e)
        self.assertEqual(sys.exc_info(), (None, None, None))

    def test_generator_leaking4(self):

        def g():
            try:
                (1 / 0)
            except ZeroDivisionError:
                (yield sys.exc_info()[0])
                raise
        it = g()
        try:
            raise TypeError
        except TypeError:
            tp = next(it)
        self.assertIs(tp, ZeroDivisionError)
        try:
            next(it)
        except ZeroDivisionError as e:
            self.assertIs(sys.exc_info()[1], e)
        self.assertEqual(sys.exc_info(), (None, None, None))

    def test_generator_doesnt_retain_old_exc(self):

        def g():
            self.assertIsInstance(sys.exc_info()[1], RuntimeError)
            (yield)
            self.assertEqual(sys.exc_info(), (None, None, None))
        it = g()
        try:
            raise RuntimeError
        except RuntimeError:
            next(it)
        self.assertRaises(StopIteration, next, it)

    def test_generator_finalizing_and_exc_info(self):

        def simple_gen():
            (yield 1)

        def run_gen():
            gen = simple_gen()
            try:
                raise RuntimeError
            except RuntimeError:
                return next(gen)
        run_gen()
        gc_collect()
        self.assertEqual(sys.exc_info(), (None, None, None))

    def _check_generator_cleanup_exc_state(self, testfunc):

        class MyException(Exception):

            def __init__(self, obj):
                self.obj = obj

        class MyObj():
            pass

        def raising_gen():
            try:
                raise MyException(obj)
            except MyException:
                (yield)
        obj = MyObj()
        wr = weakref.ref(obj)
        g = raising_gen()
        next(g)
        testfunc(g)
        g = obj = None
        obj = wr()
        self.assertIsNone(obj)

    def test_generator_throw_cleanup_exc_state(self):

        def do_throw(g):
            try:
                g.throw(RuntimeError())
            except RuntimeError:
                pass
        self._check_generator_cleanup_exc_state(do_throw)

    def test_generator_close_cleanup_exc_state(self):

        def do_close(g):
            g.close()
        self._check_generator_cleanup_exc_state(do_close)

    def test_generator_del_cleanup_exc_state(self):

        def do_del(g):
            g = None
        self._check_generator_cleanup_exc_state(do_del)

    def test_generator_next_cleanup_exc_state(self):

        def do_next(g):
            try:
                next(g)
            except StopIteration:
                pass
            else:
                self.fail('should have raised StopIteration')
        self._check_generator_cleanup_exc_state(do_next)

    def test_generator_send_cleanup_exc_state(self):

        def do_send(g):
            try:
                g.send(None)
            except StopIteration:
                pass
            else:
                self.fail('should have raised StopIteration')
        self._check_generator_cleanup_exc_state(do_send)

    def test_3114(self):

        class MyObject():

            def __del__(self):
                nonlocal e
                e = sys.exc_info()
        e = ()
        try:
            raise Exception(MyObject())
        except:
            pass
        self.assertEqual(e, (None, None, None))

    def test_unicode_change_attributes(self):
        u = UnicodeEncodeError('baz', 'xxxxx', 1, 5, 'foo')
        self.assertEqual(str(u), "'baz' codec can't encode characters in position 1-4: foo")
        u.end = 2
        self.assertEqual(str(u), "'baz' codec can't encode character '\\x78' in position 1: foo")
        u.end = 5
        u.reason = 965230951443685724997
        self.assertEqual(str(u), "'baz' codec can't encode characters in position 1-4: 965230951443685724997")
        u.encoding = 4000
        self.assertEqual(str(u), "'4000' codec can't encode characters in position 1-4: 965230951443685724997")
        u.start = 1000
        self.assertEqual(str(u), "'4000' codec can't encode characters in position 1000-4: 965230951443685724997")
        u = UnicodeDecodeError('baz', b'xxxxx', 1, 5, 'foo')
        self.assertEqual(str(u), "'baz' codec can't decode bytes in position 1-4: foo")
        u.end = 2
        self.assertEqual(str(u), "'baz' codec can't decode byte 0x78 in position 1: foo")
        u.end = 5
        u.reason = 965230951443685724997
        self.assertEqual(str(u), "'baz' codec can't decode bytes in position 1-4: 965230951443685724997")
        u.encoding = 4000
        self.assertEqual(str(u), "'4000' codec can't decode bytes in position 1-4: 965230951443685724997")
        u.start = 1000
        self.assertEqual(str(u), "'4000' codec can't decode bytes in position 1000-4: 965230951443685724997")
        u = UnicodeTranslateError('xxxx', 1, 5, 'foo')
        self.assertEqual(str(u), "can't translate characters in position 1-4: foo")
        u.end = 2
        self.assertEqual(str(u), "can't translate character '\\x78' in position 1: foo")
        u.end = 5
        u.reason = 965230951443685724997
        self.assertEqual(str(u), "can't translate characters in position 1-4: 965230951443685724997")
        u.start = 1000
        self.assertEqual(str(u), "can't translate characters in position 1000-4: 965230951443685724997")

    def test_unicode_errors_no_object(self):
        klasses = (UnicodeEncodeError, UnicodeDecodeError, UnicodeTranslateError)
        for klass in klasses:
            self.assertEqual(str(klass.__new__(klass)), '')

    @no_tracing
    def test_badisinstance(self):

        class Meta(type):

            def __subclasscheck__(cls, subclass):
                raise ValueError()

        class MyException(Exception, metaclass=Meta):
            pass
        with captured_stderr() as stderr:
            try:
                raise KeyError()
            except MyException as e:
                self.fail('exception should not be a MyException')
            except KeyError:
                pass
            except:
                self.fail('Should have raised KeyError')
            else:
                self.fail('Should have raised KeyError')

        def g():
            try:
                return g()
            except RecursionError:
                return sys.exc_info()
        (e, v, tb) = g()
        self.assertIsInstance(v, RecursionError, type(v))
        self.assertIn('maximum recursion depth exceeded', str(v))

    @cpython_only
    def test_recursion_normalizing_exception(self):
        code = ("if 1:\n            import sys\n            from _testinternalcapi import get_recursion_depth\n\n            class MyException(Exception): pass\n\n            def setrecursionlimit(depth):\n                while 1:\n                    try:\n                        sys.setrecursionlimit(depth)\n                        return depth\n                    except RecursionError:\n                        # sys.setrecursionlimit() raises a RecursionError if\n                        # the new recursion limit is too low (issue #25274).\n                        depth += 1\n\n            def recurse(cnt):\n                cnt -= 1\n                if cnt:\n                    recurse(cnt)\n                else:\n                    generator.throw(MyException)\n\n            def gen():\n                f = open(%a, mode='rb', buffering=0)\n                yield\n\n            generator = gen()\n            next(generator)\n            recursionlimit = sys.getrecursionlimit()\n            depth = get_recursion_depth()\n            try:\n                # Upon the last recursive invocation of recurse(),\n                # tstate->recursion_depth is equal to (recursion_limit - 1)\n                # and is equal to recursion_limit when _gen_throw() calls\n                # PyErr_NormalizeException().\n                recurse(setrecursionlimit(depth + 2) - depth - 1)\n            finally:\n                sys.setrecursionlimit(recursionlimit)\n                print('Done.')\n        " % __file__)
        (rc, out, err) = script_helper.assert_python_failure('-Wd', '-c', code)
        self.assertEqual(rc, 1)
        self.assertIn(b'RecursionError', err)
        self.assertIn(b'ResourceWarning', err)
        self.assertIn(b'Done.', out)

    @cpython_only
    def test_recursion_normalizing_infinite_exception(self):
        code = "if 1:\n            import _testcapi\n            try:\n                raise _testcapi.RecursingInfinitelyError\n            finally:\n                print('Done.')\n        "
        (rc, out, err) = script_helper.assert_python_failure('-c', code)
        self.assertEqual(rc, 1)
        self.assertIn(b'RecursionError: maximum recursion depth exceeded while normalizing an exception', err)
        self.assertIn(b'Done.', out)

    @cpython_only
    def test_recursion_normalizing_with_no_memory(self):
        code = 'if 1:\n            import _testcapi\n            class C(): pass\n            def recurse(cnt):\n                cnt -= 1\n                if cnt:\n                    recurse(cnt)\n                else:\n                    _testcapi.set_nomemory(0)\n                    C()\n            recurse(16)\n        '
        with SuppressCrashReport():
            (rc, out, err) = script_helper.assert_python_failure('-c', code)
            self.assertIn(b'Fatal Python error: _PyErr_NormalizeException: Cannot recover from MemoryErrors while normalizing exceptions.', err)

    @cpython_only
    def test_MemoryError(self):
        import traceback
        from _testcapi import raise_memoryerror

        def raiseMemError():
            try:
                raise_memoryerror()
            except MemoryError as e:
                tb = e.__traceback__
            else:
                self.fail('Should have raises a MemoryError')
            return traceback.format_tb(tb)
        tb1 = raiseMemError()
        tb2 = raiseMemError()
        self.assertEqual(tb1, tb2)

    @cpython_only
    def test_exception_with_doc(self):
        import _testcapi
        doc2 = 'This is a test docstring.'
        doc4 = 'This is another test docstring.'
        self.assertRaises(SystemError, _testcapi.make_exception_with_doc, 'error1')
        error1 = _testcapi.make_exception_with_doc('_testcapi.error1')
        self.assertIs(type(error1), type)
        self.assertTrue(issubclass(error1, Exception))
        self.assertIsNone(error1.__doc__)
        error2 = _testcapi.make_exception_with_doc('_testcapi.error2', doc2)
        self.assertEqual(error2.__doc__, doc2)
        error3 = _testcapi.make_exception_with_doc('_testcapi.error3', base=error2)
        self.assertTrue(issubclass(error3, error2))

        class C(object):
            pass
        error4 = _testcapi.make_exception_with_doc('_testcapi.error4', doc4, (error3, C))
        self.assertTrue(issubclass(error4, error3))
        self.assertTrue(issubclass(error4, C))
        self.assertEqual(error4.__doc__, doc4)
        error5 = _testcapi.make_exception_with_doc('_testcapi.error5', '', error4, {'a': 1})
        self.assertTrue(issubclass(error5, error4))
        self.assertEqual(error5.a, 1)
        self.assertEqual(error5.__doc__, '')

    @cpython_only
    def test_memory_error_cleanup(self):
        from _testcapi import raise_memoryerror

        class C():
            pass
        wr = None

        def inner():
            nonlocal wr
            c = C()
            wr = weakref.ref(c)
            raise_memoryerror()
        try:
            inner()
        except MemoryError as e:
            self.assertNotEqual(wr(), None)
        else:
            self.fail('MemoryError not raised')
        self.assertEqual(wr(), None)

    @no_tracing
    def test_recursion_error_cleanup(self):

        class C():
            pass
        wr = None

        def inner():
            nonlocal wr
            c = C()
            wr = weakref.ref(c)
            inner()
        try:
            inner()
        except RecursionError as e:
            self.assertNotEqual(wr(), None)
        else:
            self.fail('RecursionError not raised')
        self.assertEqual(wr(), None)

    def test_errno_ENOTDIR(self):
        with self.assertRaises(OSError) as cm:
            os.listdir(__file__)
        self.assertEqual(cm.exception.errno, errno.ENOTDIR, cm.exception)

    def test_unraisable(self):

        class BrokenDel():

            def __del__(self):
                exc = ValueError('del is broken')
                raise exc
        obj = BrokenDel()
        with support.catch_unraisable_exception() as cm:
            del obj
            self.assertEqual(cm.unraisable.object, BrokenDel.__del__)
            self.assertIsNotNone(cm.unraisable.exc_traceback)

    def test_unhandled(self):
        for exc_type in (ValueError, BrokenStrException):
            with self.subTest(exc_type):
                try:
                    exc = exc_type('test message')
                    raise exc
                except exc_type:
                    with captured_stderr() as stderr:
                        sys.__excepthook__(*sys.exc_info())
                report = stderr.getvalue()
                self.assertIn('test_exceptions.py', report)
                self.assertIn('raise exc', report)
                self.assertIn(exc_type.__name__, report)
                if (exc_type is BrokenStrException):
                    self.assertIn('<exception str() failed>', report)
                else:
                    self.assertIn('test message', report)
                self.assertTrue(report.endswith('\n'))

    @cpython_only
    def test_memory_error_in_PyErr_PrintEx(self):
        code = 'if 1:\n            import _testcapi\n            class C(): pass\n            _testcapi.set_nomemory(0, %d)\n            C()\n        '
        for i in range(1, 20):
            (rc, out, err) = script_helper.assert_python_failure('-c', (code % i))
            self.assertIn(rc, (1, 120))
            self.assertIn(b'MemoryError', err)

    def test_yield_in_nested_try_excepts(self):

        class MainError(Exception):
            pass

        class SubError(Exception):
            pass

        def main():
            try:
                raise MainError()
            except MainError:
                try:
                    (yield)
                except SubError:
                    pass
                raise
        coro = main()
        coro.send(None)
        with self.assertRaises(MainError):
            coro.throw(SubError())

    def test_generator_doesnt_retain_old_exc2(self):

        def g():
            try:
                raise ValueError
            except ValueError:
                (yield 1)
            self.assertEqual(sys.exc_info(), (None, None, None))
            (yield 2)
        gen = g()
        try:
            raise IndexError
        except IndexError:
            self.assertEqual(next(gen), 1)
        self.assertEqual(next(gen), 2)

    def test_raise_in_generator(self):

        def g():
            (yield 1)
            raise
            (yield 2)
        with self.assertRaises(ZeroDivisionError):
            i = g()
            try:
                (1 / 0)
            except:
                next(i)
                next(i)

    @unittest.skipUnless(__debug__, "Won't work if __debug__ is False")
    def test_assert_shadowing(self):
        global AssertionError
        AssertionError = TypeError
        try:
            assert False, 'hello'
        except BaseException as e:
            del AssertionError
            self.assertIsInstance(e, AssertionError)
            self.assertEqual(str(e), 'hello')
        else:
            del AssertionError
            self.fail('Expected exception')

class ImportErrorTests(unittest.TestCase):

    def test_attributes(self):
        exc = ImportError('test')
        self.assertIsNone(exc.name)
        self.assertIsNone(exc.path)
        exc = ImportError('test', name='somemodule')
        self.assertEqual(exc.name, 'somemodule')
        self.assertIsNone(exc.path)
        exc = ImportError('test', path='somepath')
        self.assertEqual(exc.path, 'somepath')
        self.assertIsNone(exc.name)
        exc = ImportError('test', path='somepath', name='somename')
        self.assertEqual(exc.name, 'somename')
        self.assertEqual(exc.path, 'somepath')
        msg = "'invalid' is an invalid keyword argument for ImportError"
        with self.assertRaisesRegex(TypeError, msg):
            ImportError('test', invalid='keyword')
        with self.assertRaisesRegex(TypeError, msg):
            ImportError('test', name='name', invalid='keyword')
        with self.assertRaisesRegex(TypeError, msg):
            ImportError('test', path='path', invalid='keyword')
        with self.assertRaisesRegex(TypeError, msg):
            ImportError(invalid='keyword')
        with self.assertRaisesRegex(TypeError, msg):
            ImportError('test', invalid='keyword', another=True)

    def test_reset_attributes(self):
        exc = ImportError('test', name='name', path='path')
        self.assertEqual(exc.args, ('test',))
        self.assertEqual(exc.msg, 'test')
        self.assertEqual(exc.name, 'name')
        self.assertEqual(exc.path, 'path')
        exc.__init__()
        self.assertEqual(exc.args, ())
        self.assertEqual(exc.msg, None)
        self.assertEqual(exc.name, None)
        self.assertEqual(exc.path, None)

    def test_non_str_argument(self):
        with check_warnings(('', BytesWarning), quiet=True):
            arg = b'abc'
            exc = ImportError(arg)
            self.assertEqual(str(arg), str(exc))

    def test_copy_pickle(self):
        for kwargs in (dict(), dict(name='somename'), dict(path='somepath'), dict(name='somename', path='somepath')):
            orig = ImportError('test', **kwargs)
            for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
                exc = pickle.loads(pickle.dumps(orig, proto))
                self.assertEqual(exc.args, ('test',))
                self.assertEqual(exc.msg, 'test')
                self.assertEqual(exc.name, orig.name)
                self.assertEqual(exc.path, orig.path)
            for c in (copy.copy, copy.deepcopy):
                exc = c(orig)
                self.assertEqual(exc.args, ('test',))
                self.assertEqual(exc.msg, 'test')
                self.assertEqual(exc.name, orig.name)
                self.assertEqual(exc.path, orig.path)
if (__name__ == '__main__'):
    unittest.main()
