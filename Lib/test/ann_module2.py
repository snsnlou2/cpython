
'\nSome correct syntax for variable annotation here.\nMore examples are in test_grammar and test_parser.\n'
from typing import no_type_check, ClassVar
i = 1
x = (i / 10)

def f():

    class C():
        ...
    return C()
f().new_attr = object()

class C():

    def __init__(self, x):
        self.x = x
c = C(5)
c.new_attr = 10
__annotations__ = {}

@no_type_check
class NTC():

    def meth(self, param):
        ...

class CV():
CV.var = CV()
