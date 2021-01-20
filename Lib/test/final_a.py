
'\nFodder for module finalization tests in test_module.\n'
import shutil
import test.final_b
x = 'a'

class C():

    def __del__(self):
        print('x =', x)
        print('final_b.x =', test.final_b.x)
        print('shutil.rmtree =', getattr(shutil.rmtree, '__name__', None))
        print('len =', getattr(len, '__name__', None))
c = C()
_underscored = C()
