
import itertools

class PseudoStr(str):
    pass

class StrProxy():

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def __bool__(self):
        return bool(self.value)

class Object():

    def __repr__(self):
        return '<object>'

def wrapped_arg_combos(*args, wrappers=(PseudoStr, StrProxy), skip=(lambda w, i, v: (not isinstance(v, str)))):
    'Yield every possible combination of wrapped items for the given args.\n\n    Effectively, the wrappers are applied to the args according to the\n    powerset of the args indicies.  So the result includes the args\n    completely unwrapped.\n\n    If "skip" is supplied (default is to skip all non-str values) and\n    it returns True for a given arg index/value then that arg will\n    remain unwrapped,\n\n    Only unique results are returned.  If an arg was skipped for one\n    of the combinations then it could end up matching one of the other\n    combinations.  In that case only one of them will be yielded.\n    '
    if (not args):
        return
    indices = list(range(len(args)))
    combos = itertools.chain.from_iterable((itertools.combinations(indices, r) for r in range((len(indices) + 1))))
    seen = set()
    for combo in combos:
        for wrap in wrappers:
            indexes = []
            applied = list(args)
            for i in combo:
                arg = args[i]
                if (skip and skip(wrap, i, arg)):
                    continue
                indexes.append(i)
                applied[i] = wrap(arg)
            key = (wrap, tuple(indexes))
            if (key not in seen):
                (yield tuple(applied))
                seen.add(key)
