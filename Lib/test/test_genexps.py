
doctests = '\n\nTest simple loop with conditional\n\n    >>> sum(i*i for i in range(100) if i&1 == 1)\n    166650\n\nTest simple nesting\n\n    >>> list((i,j) for i in range(3) for j in range(4) )\n    [(0, 0), (0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2), (2, 3)]\n\nTest nesting with the inner expression dependent on the outer\n\n    >>> list((i,j) for i in range(4) for j in range(i) )\n    [(1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (3, 2)]\n\nTest the idiom for temporary variable assignment in comprehensions.\n\n    >>> list((j*j for i in range(4) for j in [i+1]))\n    [1, 4, 9, 16]\n    >>> list((j*k for i in range(4) for j in [i+1] for k in [j+1]))\n    [2, 6, 12, 20]\n    >>> list((j*k for i in range(4) for j, k in [(i+1, i+2)]))\n    [2, 6, 12, 20]\n\nNot assignment\n\n    >>> list((i*i for i in [*range(4)]))\n    [0, 1, 4, 9]\n    >>> list((i*i for i in (*range(4),)))\n    [0, 1, 4, 9]\n\nMake sure the induction variable is not exposed\n\n    >>> i = 20\n    >>> sum(i*i for i in range(100))\n    328350\n    >>> i\n    20\n\nTest first class\n\n    >>> g = (i*i for i in range(4))\n    >>> type(g)\n    <class \'generator\'>\n    >>> list(g)\n    [0, 1, 4, 9]\n\nTest direct calls to next()\n\n    >>> g = (i*i for i in range(3))\n    >>> next(g)\n    0\n    >>> next(g)\n    1\n    >>> next(g)\n    4\n    >>> next(g)\n    Traceback (most recent call last):\n      File "<pyshell#21>", line 1, in -toplevel-\n        next(g)\n    StopIteration\n\nDoes it stay stopped?\n\n    >>> next(g)\n    Traceback (most recent call last):\n      File "<pyshell#21>", line 1, in -toplevel-\n        next(g)\n    StopIteration\n    >>> list(g)\n    []\n\nTest running gen when defining function is out of scope\n\n    >>> def f(n):\n    ...     return (i*i for i in range(n))\n    >>> list(f(10))\n    [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]\n\n    >>> def f(n):\n    ...     return ((i,j) for i in range(3) for j in range(n))\n    >>> list(f(4))\n    [(0, 0), (0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2), (2, 3)]\n    >>> def f(n):\n    ...     return ((i,j) for i in range(3) for j in range(4) if j in range(n))\n    >>> list(f(4))\n    [(0, 0), (0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2), (2, 3)]\n    >>> list(f(2))\n    [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)]\n\nVerify that parenthesis are required in a statement\n\n    >>> def f(n):\n    ...     return i*i for i in range(n)\n    Traceback (most recent call last):\n       ...\n    SyntaxError: invalid syntax\n\nVerify that parenthesis are required when used as a keyword argument value\n\n    >>> dict(a = i for i in range(10))\n    Traceback (most recent call last):\n       ...\n    SyntaxError: invalid syntax\n\nVerify that parenthesis are required when used as a keyword argument value\n\n    >>> dict(a = (i for i in range(10))) #doctest: +ELLIPSIS\n    {\'a\': <generator object <genexpr> at ...>}\n\nVerify early binding for the outermost for-expression\n\n    >>> x=10\n    >>> g = (i*i for i in range(x))\n    >>> x = 5\n    >>> list(g)\n    [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]\n\nVerify that the outermost for-expression makes an immediate check\nfor iterability\n\n    >>> (i for i in 6)\n    Traceback (most recent call last):\n      File "<pyshell#4>", line 1, in -toplevel-\n        (i for i in 6)\n    TypeError: \'int\' object is not iterable\n\nVerify late binding for the outermost if-expression\n\n    >>> include = (2,4,6,8)\n    >>> g = (i*i for i in range(10) if i in include)\n    >>> include = (1,3,5,7,9)\n    >>> list(g)\n    [1, 9, 25, 49, 81]\n\nVerify late binding for the innermost for-expression\n\n    >>> g = ((i,j) for i in range(3) for j in range(x))\n    >>> x = 4\n    >>> list(g)\n    [(0, 0), (0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2), (2, 3)]\n\nVerify re-use of tuples (a side benefit of using genexps over listcomps)\n\n    >>> tupleids = list(map(id, ((i,i) for i in range(10))))\n    >>> int(max(tupleids) - min(tupleids))\n    0\n\nVerify that syntax error\'s are raised for genexps used as lvalues\n\n    >>> (y for y in (1,2)) = 10\n    Traceback (most recent call last):\n       ...\n    SyntaxError: cannot assign to generator expression\n\n    >>> (y for y in (1,2)) += 10\n    Traceback (most recent call last):\n       ...\n    SyntaxError: \'generator expression\' is an illegal expression for augmented assignment\n\n\n########### Tests borrowed from or inspired by test_generators.py ############\n\nMake a generator that acts like range()\n\n    >>> yrange = lambda n:  (i for i in range(n))\n    >>> list(yrange(10))\n    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]\n\nGenerators always return to the most recent caller:\n\n    >>> def creator():\n    ...     r = yrange(5)\n    ...     print("creator", next(r))\n    ...     return r\n    >>> def caller():\n    ...     r = creator()\n    ...     for i in r:\n    ...             print("caller", i)\n    >>> caller()\n    creator 0\n    caller 1\n    caller 2\n    caller 3\n    caller 4\n\nGenerators can call other generators:\n\n    >>> def zrange(n):\n    ...     for i in yrange(n):\n    ...         yield i\n    >>> list(zrange(5))\n    [0, 1, 2, 3, 4]\n\n\nVerify that a gen exp cannot be resumed while it is actively running:\n\n    >>> g = (next(me) for i in range(10))\n    >>> me = g\n    >>> next(me)\n    Traceback (most recent call last):\n      File "<pyshell#30>", line 1, in -toplevel-\n        next(me)\n      File "<pyshell#28>", line 1, in <generator expression>\n        g = (next(me) for i in range(10))\n    ValueError: generator already executing\n\nVerify exception propagation\n\n    >>> g = (10 // i for i in (5, 0, 2))\n    >>> next(g)\n    2\n    >>> next(g)\n    Traceback (most recent call last):\n      File "<pyshell#37>", line 1, in -toplevel-\n        next(g)\n      File "<pyshell#35>", line 1, in <generator expression>\n        g = (10 // i for i in (5, 0, 2))\n    ZeroDivisionError: integer division or modulo by zero\n    >>> next(g)\n    Traceback (most recent call last):\n      File "<pyshell#38>", line 1, in -toplevel-\n        next(g)\n    StopIteration\n\nMake sure that None is a valid return value\n\n    >>> list(None for i in range(10))\n    [None, None, None, None, None, None, None, None, None, None]\n\nCheck that generator attributes are present\n\n    >>> g = (i*i for i in range(3))\n    >>> expected = set([\'gi_frame\', \'gi_running\'])\n    >>> set(attr for attr in dir(g) if not attr.startswith(\'__\')) >= expected\n    True\n\n    >>> from test.support import HAVE_DOCSTRINGS\n    >>> print(g.__next__.__doc__ if HAVE_DOCSTRINGS else \'Implement next(self).\')\n    Implement next(self).\n    >>> import types\n    >>> isinstance(g, types.GeneratorType)\n    True\n\nCheck the __iter__ slot is defined to return self\n\n    >>> iter(g) is g\n    True\n\nVerify that the running flag is set properly\n\n    >>> g = (me.gi_running for i in (0,1))\n    >>> me = g\n    >>> me.gi_running\n    0\n    >>> next(me)\n    1\n    >>> me.gi_running\n    0\n\nVerify that genexps are weakly referencable\n\n    >>> import weakref\n    >>> g = (i*i for i in range(4))\n    >>> wr = weakref.ref(g)\n    >>> wr() is g\n    True\n    >>> p = weakref.proxy(g)\n    >>> list(p)\n    [0, 1, 4, 9]\n\n\n'
import sys
if (hasattr(sys, 'gettrace') and sys.gettrace()):
    __test__ = {}
else:
    __test__ = {'doctests': doctests}

def test_main(verbose=None):
    from test import support
    from test import test_genexps
    support.run_doctest(test_genexps, verbose)
    if (verbose and hasattr(sys, 'gettotalrefcount')):
        import gc
        counts = ([None] * 5)
        for i in range(len(counts)):
            support.run_doctest(test_genexps, verbose)
            gc.collect()
            counts[i] = sys.gettotalrefcount()
        print(counts)
if (__name__ == '__main__'):
    test_main(verbose=True)
