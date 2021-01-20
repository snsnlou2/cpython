
'Generic (shallow and deep) copying operations.\n\nInterface summary:\n\n        import copy\n\n        x = copy.copy(y)        # make a shallow copy of y\n        x = copy.deepcopy(y)    # make a deep copy of y\n\nFor module specific errors, copy.Error is raised.\n\nThe difference between shallow and deep copying is only relevant for\ncompound objects (objects that contain other objects, like lists or\nclass instances).\n\n- A shallow copy constructs a new compound object and then (to the\n  extent possible) inserts *the same objects* into it that the\n  original contains.\n\n- A deep copy constructs a new compound object and then, recursively,\n  inserts *copies* into it of the objects found in the original.\n\nTwo problems often exist with deep copy operations that don\'t exist\nwith shallow copy operations:\n\n a) recursive objects (compound objects that, directly or indirectly,\n    contain a reference to themselves) may cause a recursive loop\n\n b) because deep copy copies *everything* it may copy too much, e.g.\n    administrative data structures that should be shared even between\n    copies\n\nPython\'s deep copy operation avoids these problems by:\n\n a) keeping a table of objects already copied during the current\n    copying pass\n\n b) letting user-defined classes override the copying operation or the\n    set of components copied\n\nThis version does not copy types like module, class, function, method,\nnor stack trace, stack frame, nor file, socket, window, nor array, nor\nany similar types.\n\nClasses can use the same interfaces to control copying that they use\nto control pickling: they can define methods called __getinitargs__(),\n__getstate__() and __setstate__().  See the documentation for module\n"pickle" for information on these methods.\n'
import types
import weakref
from copyreg import dispatch_table

class Error(Exception):
    pass
error = Error
try:
    from org.python.core import PyStringMap
except ImportError:
    PyStringMap = None
__all__ = ['Error', 'copy', 'deepcopy']

def copy(x):
    "Shallow copy operation on arbitrary Python objects.\n\n    See the module's __doc__ string for more info.\n    "
    cls = type(x)
    copier = _copy_dispatch.get(cls)
    if copier:
        return copier(x)
    if issubclass(cls, type):
        return _copy_immutable(x)
    copier = getattr(cls, '__copy__', None)
    if (copier is not None):
        return copier(x)
    reductor = dispatch_table.get(cls)
    if (reductor is not None):
        rv = reductor(x)
    else:
        reductor = getattr(x, '__reduce_ex__', None)
        if (reductor is not None):
            rv = reductor(4)
        else:
            reductor = getattr(x, '__reduce__', None)
            if reductor:
                rv = reductor()
            else:
                raise Error(('un(shallow)copyable object of type %s' % cls))
    if isinstance(rv, str):
        return x
    return _reconstruct(x, None, *rv)
_copy_dispatch = d = {}

def _copy_immutable(x):
    return x
for t in (type(None), int, float, bool, complex, str, tuple, bytes, frozenset, type, range, slice, property, types.BuiltinFunctionType, type(Ellipsis), type(NotImplemented), types.FunctionType, weakref.ref):
    d[t] = _copy_immutable
t = getattr(types, 'CodeType', None)
if (t is not None):
    d[t] = _copy_immutable
d[list] = list.copy
d[dict] = dict.copy
d[set] = set.copy
d[bytearray] = bytearray.copy
if (PyStringMap is not None):
    d[PyStringMap] = PyStringMap.copy
del d, t

def deepcopy(x, memo=None, _nil=[]):
    "Deep copy operation on arbitrary Python objects.\n\n    See the module's __doc__ string for more info.\n    "
    if (memo is None):
        memo = {}
    d = id(x)
    y = memo.get(d, _nil)
    if (y is not _nil):
        return y
    cls = type(x)
    copier = _deepcopy_dispatch.get(cls)
    if (copier is not None):
        y = copier(x, memo)
    elif issubclass(cls, type):
        y = _deepcopy_atomic(x, memo)
    else:
        copier = getattr(x, '__deepcopy__', None)
        if (copier is not None):
            y = copier(memo)
        else:
            reductor = dispatch_table.get(cls)
            if reductor:
                rv = reductor(x)
            else:
                reductor = getattr(x, '__reduce_ex__', None)
                if (reductor is not None):
                    rv = reductor(4)
                else:
                    reductor = getattr(x, '__reduce__', None)
                    if reductor:
                        rv = reductor()
                    else:
                        raise Error(('un(deep)copyable object of type %s' % cls))
            if isinstance(rv, str):
                y = x
            else:
                y = _reconstruct(x, memo, *rv)
    if (y is not x):
        memo[d] = y
        _keep_alive(x, memo)
    return y
_deepcopy_dispatch = d = {}

def _deepcopy_atomic(x, memo):
    return x
d[type(None)] = _deepcopy_atomic
d[type(Ellipsis)] = _deepcopy_atomic
d[type(NotImplemented)] = _deepcopy_atomic
d[int] = _deepcopy_atomic
d[float] = _deepcopy_atomic
d[bool] = _deepcopy_atomic
d[complex] = _deepcopy_atomic
d[bytes] = _deepcopy_atomic
d[str] = _deepcopy_atomic
d[types.CodeType] = _deepcopy_atomic
d[type] = _deepcopy_atomic
d[range] = _deepcopy_atomic
d[types.BuiltinFunctionType] = _deepcopy_atomic
d[types.FunctionType] = _deepcopy_atomic
d[weakref.ref] = _deepcopy_atomic
d[property] = _deepcopy_atomic

def _deepcopy_list(x, memo, deepcopy=deepcopy):
    y = []
    memo[id(x)] = y
    append = y.append
    for a in x:
        append(deepcopy(a, memo))
    return y
d[list] = _deepcopy_list

def _deepcopy_tuple(x, memo, deepcopy=deepcopy):
    y = [deepcopy(a, memo) for a in x]
    try:
        return memo[id(x)]
    except KeyError:
        pass
    for (k, j) in zip(x, y):
        if (k is not j):
            y = tuple(y)
            break
    else:
        y = x
    return y
d[tuple] = _deepcopy_tuple

def _deepcopy_dict(x, memo, deepcopy=deepcopy):
    y = {}
    memo[id(x)] = y
    for (key, value) in x.items():
        y[deepcopy(key, memo)] = deepcopy(value, memo)
    return y
d[dict] = _deepcopy_dict
if (PyStringMap is not None):
    d[PyStringMap] = _deepcopy_dict

def _deepcopy_method(x, memo):
    return type(x)(x.__func__, deepcopy(x.__self__, memo))
d[types.MethodType] = _deepcopy_method
del d

def _keep_alive(x, memo):
    'Keeps a reference to the object x in the memo.\n\n    Because we remember objects by their id, we have\n    to assure that possibly temporary objects are kept\n    alive by referencing them.\n    We store a reference at the id of the memo, which should\n    normally not be used unless someone tries to deepcopy\n    the memo itself...\n    '
    try:
        memo[id(memo)].append(x)
    except KeyError:
        memo[id(memo)] = [x]

def _reconstruct(x, memo, func, args, state=None, listiter=None, dictiter=None, deepcopy=deepcopy):
    deep = (memo is not None)
    if (deep and args):
        args = (deepcopy(arg, memo) for arg in args)
    y = func(*args)
    if deep:
        memo[id(x)] = y
    if (state is not None):
        if deep:
            state = deepcopy(state, memo)
        if hasattr(y, '__setstate__'):
            y.__setstate__(state)
        else:
            if (isinstance(state, tuple) and (len(state) == 2)):
                (state, slotstate) = state
            else:
                slotstate = None
            if (state is not None):
                y.__dict__.update(state)
            if (slotstate is not None):
                for (key, value) in slotstate.items():
                    setattr(y, key, value)
    if (listiter is not None):
        if deep:
            for item in listiter:
                item = deepcopy(item, memo)
                y.append(item)
        else:
            for item in listiter:
                y.append(item)
    if (dictiter is not None):
        if deep:
            for (key, value) in dictiter:
                key = deepcopy(key, memo)
                value = deepcopy(value, memo)
                y[key] = value
        else:
            for (key, value) in dictiter:
                y[key] = value
    return y
del types, weakref, PyStringMap
