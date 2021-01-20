
'\nThe module for testing variable annotations.\nEmpty lines above are for good reason (testing for correct line numbers)\n'
from typing import Optional
from functools import wraps
__annotations__[1] = 2

class C():
    x = 5
    y = None
from typing import Tuple
x = 5
y = x

class M(type):
    __annotations__['123'] = 123
    o = object
pars = True

class D(C):
    j = 'hi'
    k = 'bye'
from types import new_class
h_class = new_class('H', (C,))
j_class = new_class('J')

class F():
    z = 5

    def __init__(self, x):
        pass

class Y(F):

    def __init__(self):
        super(F, self).__init__(123)

class Meta(type):

    def __new__(meta, name, bases, namespace):
        return super().__new__(meta, name, bases, namespace)

class S(metaclass=Meta):
    x = 'something'
    y = 'something else'

def foo(x=10):

    def bar(y: List[str]):
        x: str = 'yes'
    bar()

def dec(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
