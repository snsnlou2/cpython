
import builtins
import unittest
from test.support import swap_item, swap_attr

class RebindBuiltinsTests(unittest.TestCase):
    'Test all the ways that we can change/shadow globals/builtins.'

    def configure_func(self, func, *args):
        'Perform TestCase-specific configuration on a function before testing.\n\n        By default, this does nothing. Example usage: spinning a function so\n        that a JIT will optimize it. Subclasses should override this as needed.\n\n        Args:\n            func: function to configure.\n            *args: any arguments that should be passed to func, if calling it.\n\n        Returns:\n            Nothing. Work will be performed on func in-place.\n        '
        pass

    def test_globals_shadow_builtins(self):

        def foo():
            return len([1, 2, 3])
        self.configure_func(foo)
        self.assertEqual(foo(), 3)
        with swap_item(globals(), 'len', (lambda x: 7)):
            self.assertEqual(foo(), 7)

    def test_modify_builtins(self):

        def foo():
            return len([1, 2, 3])
        self.configure_func(foo)
        self.assertEqual(foo(), 3)
        with swap_attr(builtins, 'len', (lambda x: 7)):
            self.assertEqual(foo(), 7)

    def test_modify_builtins_while_generator_active(self):

        def foo():
            x = range(3)
            (yield len(x))
            (yield len(x))
        self.configure_func(foo)
        g = foo()
        self.assertEqual(next(g), 3)
        with swap_attr(builtins, 'len', (lambda x: 7)):
            self.assertEqual(next(g), 7)

    def test_modify_builtins_from_leaf_function(self):
        with swap_attr(builtins, 'len', len):

            def bar():
                builtins.len = (lambda x: 4)

            def foo(modifier):
                l = []
                l.append(len(range(7)))
                modifier()
                l.append(len(range(7)))
                return l
            self.configure_func(foo, (lambda : None))
            self.assertEqual(foo(bar), [7, 4])

    def test_cannot_change_globals_or_builtins_with_eval(self):

        def foo():
            return len([1, 2, 3])
        self.configure_func(foo)
        builtins_dict = {'len': (lambda x: 7)}
        globals_dict = {'foo': foo, '__builtins__': builtins_dict, 'len': (lambda x: 8)}
        self.assertEqual(eval('foo()', globals_dict), 3)
        self.assertEqual(eval('foo()', {'foo': foo}), 3)

    def test_cannot_change_globals_or_builtins_with_exec(self):

        def foo():
            return len([1, 2, 3])
        self.configure_func(foo)
        globals_dict = {'foo': foo}
        exec('x = foo()', globals_dict)
        self.assertEqual(globals_dict['x'], 3)
        builtins_dict = {'len': (lambda x: 7)}
        globals_dict = {'foo': foo, '__builtins__': builtins_dict, 'len': (lambda x: 8)}
        exec('x = foo()', globals_dict)
        self.assertEqual(globals_dict['x'], 3)

    def test_cannot_replace_builtins_dict_while_active(self):

        def foo():
            x = range(3)
            (yield len(x))
            (yield len(x))
        self.configure_func(foo)
        g = foo()
        self.assertEqual(next(g), 3)
        with swap_item(globals(), '__builtins__', {'len': (lambda x: 7)}):
            self.assertEqual(next(g), 3)

    def test_cannot_replace_builtins_dict_between_calls(self):

        def foo():
            return len([1, 2, 3])
        self.configure_func(foo)
        self.assertEqual(foo(), 3)
        with swap_item(globals(), '__builtins__', {'len': (lambda x: 7)}):
            self.assertEqual(foo(), 3)

    def test_eval_gives_lambda_custom_globals(self):
        globals_dict = {'len': (lambda x: 7)}
        foo = eval('lambda: len([])', globals_dict)
        self.configure_func(foo)
        self.assertEqual(foo(), 7)
if (__name__ == '__main__'):
    unittest.main()
