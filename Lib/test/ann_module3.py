
'\nCorrect syntax for variable annotation that should fail at runtime\nin a certain manner. More examples are in test_grammar and test_parser.\n'

def f_bad_ann():
    __annotations__[1] = 2

class C_OK():

    def __init__(self, x):
        self.x: no_such_name = x

class D_bad_ann():

    def __init__(self, x):
        sfel.y: int = 0

def g_bad_ann():
    no_such_name.attr: int = 0
