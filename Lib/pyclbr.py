
"Parse a Python module and describe its classes and functions.\n\nParse enough of a Python file to recognize imports and class and\nfunction definitions, and to find out the superclasses of a class.\n\nThe interface consists of a single function:\n    readmodule_ex(module, path=None)\nwhere module is the name of a Python module, and path is an optional\nlist of directories where the module is to be searched.  If present,\npath is prepended to the system search path sys.path.  The return value\nis a dictionary.  The keys of the dictionary are the names of the\nclasses and functions defined in the module (including classes that are\ndefined via the from XXX import YYY construct).  The values are\ninstances of classes Class and Function.  One special key/value pair is\npresent for packages: the key '__path__' has a list as its value which\ncontains the package search path.\n\nClasses and Functions have a common superclass: _Object.  Every instance\nhas the following attributes:\n    module  -- name of the module;\n    name    -- name of the object;\n    file    -- file in which the object is defined;\n    lineno  -- line in the file where the object's definition starts;\n    parent  -- parent of this object, if any;\n    children -- nested objects contained in this object.\nThe 'children' attribute is a dictionary mapping names to objects.\n\nInstances of Function describe functions with the attributes from _Object.\n\nInstances of Class describe classes with the attributes from _Object,\nplus the following:\n    super   -- list of super classes (Class instances if possible);\n    methods -- mapping of method names to beginning line numbers.\nIf the name of a super class is not recognized, the corresponding\nentry in the list of super classes is not a class instance but a\nstring giving the name of the super class.  Since import statements\nare recognized and imported modules are scanned as well, this\nshouldn't happen often.\n"
import io
import sys
import importlib.util
import tokenize
from token import NAME, DEDENT, OP
__all__ = ['readmodule', 'readmodule_ex', 'Class', 'Function']
_modules = {}

class _Object():
    'Information about Python class or function.'

    def __init__(self, module, name, file, lineno, parent):
        self.module = module
        self.name = name
        self.file = file
        self.lineno = lineno
        self.parent = parent
        self.children = {}

    def _addchild(self, name, obj):
        self.children[name] = obj

class Function(_Object):
    'Information about a Python function, including methods.'

    def __init__(self, module, name, file, lineno, parent=None):
        _Object.__init__(self, module, name, file, lineno, parent)

class Class(_Object):
    'Information about a Python class.'

    def __init__(self, module, name, super, file, lineno, parent=None):
        _Object.__init__(self, module, name, file, lineno, parent)
        self.super = ([] if (super is None) else super)
        self.methods = {}

    def _addmethod(self, name, lineno):
        self.methods[name] = lineno

def _nest_function(ob, func_name, lineno):
    'Return a Function after nesting within ob.'
    newfunc = Function(ob.module, func_name, ob.file, lineno, ob)
    ob._addchild(func_name, newfunc)
    if isinstance(ob, Class):
        ob._addmethod(func_name, lineno)
    return newfunc

def _nest_class(ob, class_name, lineno, super=None):
    'Return a Class after nesting within ob.'
    newclass = Class(ob.module, class_name, super, ob.file, lineno, ob)
    ob._addchild(class_name, newclass)
    return newclass

def readmodule(module, path=None):
    'Return Class objects for the top-level classes in module.\n\n    This is the original interface, before Functions were added.\n    '
    res = {}
    for (key, value) in _readmodule(module, (path or [])).items():
        if isinstance(value, Class):
            res[key] = value
    return res

def readmodule_ex(module, path=None):
    'Return a dictionary with all functions and classes in module.\n\n    Search for module in PATH + sys.path.\n    If possible, include imported superclasses.\n    Do this by reading source, without importing (and executing) it.\n    '
    return _readmodule(module, (path or []))

def _readmodule(module, path, inpackage=None):
    'Do the hard work for readmodule[_ex].\n\n    If inpackage is given, it must be the dotted name of the package in\n    which we are searching for a submodule, and then PATH must be the\n    package search path; otherwise, we are searching for a top-level\n    module, and path is combined with sys.path.\n    '
    if (inpackage is not None):
        fullmodule = ('%s.%s' % (inpackage, module))
    else:
        fullmodule = module
    if (fullmodule in _modules):
        return _modules[fullmodule]
    tree = {}
    if ((module in sys.builtin_module_names) and (inpackage is None)):
        _modules[module] = tree
        return tree
    i = module.rfind('.')
    if (i >= 0):
        package = module[:i]
        submodule = module[(i + 1):]
        parent = _readmodule(package, path, inpackage)
        if (inpackage is not None):
            package = ('%s.%s' % (inpackage, package))
        if (not ('__path__' in parent)):
            raise ImportError('No package named {}'.format(package))
        return _readmodule(submodule, parent['__path__'], package)
    f = None
    if (inpackage is not None):
        search_path = path
    else:
        search_path = (path + sys.path)
    spec = importlib.util._find_spec_from_path(fullmodule, search_path)
    if (spec is None):
        raise ModuleNotFoundError(f'no module named {fullmodule!r}', name=fullmodule)
    _modules[fullmodule] = tree
    if (spec.submodule_search_locations is not None):
        tree['__path__'] = spec.submodule_search_locations
    try:
        source = spec.loader.get_source(fullmodule)
    except (AttributeError, ImportError):
        return tree
    else:
        if (source is None):
            return tree
    fname = spec.loader.get_filename(fullmodule)
    return _create_tree(fullmodule, path, fname, source, tree, inpackage)

def _create_tree(fullmodule, path, fname, source, tree, inpackage):
    "Return the tree for a particular module.\n\n    fullmodule (full module name), inpackage+module, becomes o.module.\n    path is passed to recursive calls of _readmodule.\n    fname becomes o.file.\n    source is tokenized.  Imports cause recursive calls to _readmodule.\n    tree is {} or {'__path__': <submodule search locations>}.\n    inpackage, None or string, is passed to recursive calls of _readmodule.\n\n    The effect of recursive calls is mutation of global _modules.\n    "
    f = io.StringIO(source)
    stack = []
    g = tokenize.generate_tokens(f.readline)
    try:
        for (tokentype, token, start, _end, _line) in g:
            if (tokentype == DEDENT):
                (lineno, thisindent) = start
                while (stack and (stack[(- 1)][1] >= thisindent)):
                    del stack[(- 1)]
            elif (token == 'def'):
                (lineno, thisindent) = start
                while (stack and (stack[(- 1)][1] >= thisindent)):
                    del stack[(- 1)]
                (tokentype, func_name, start) = next(g)[0:3]
                if (tokentype != NAME):
                    continue
                cur_func = None
                if stack:
                    cur_obj = stack[(- 1)][0]
                    cur_func = _nest_function(cur_obj, func_name, lineno)
                else:
                    cur_func = Function(fullmodule, func_name, fname, lineno)
                    tree[func_name] = cur_func
                stack.append((cur_func, thisindent))
            elif (token == 'class'):
                (lineno, thisindent) = start
                while (stack and (stack[(- 1)][1] >= thisindent)):
                    del stack[(- 1)]
                (tokentype, class_name, start) = next(g)[0:3]
                if (tokentype != NAME):
                    continue
                (tokentype, token, start) = next(g)[0:3]
                inherit = None
                if (token == '('):
                    names = []
                    level = 1
                    super = []
                    while True:
                        (tokentype, token, start) = next(g)[0:3]
                        if ((token in (')', ',')) and (level == 1)):
                            n = ''.join(super)
                            if (n in tree):
                                n = tree[n]
                            else:
                                c = n.split('.')
                                if (len(c) > 1):
                                    m = c[(- 2)]
                                    c = c[(- 1)]
                                    if (m in _modules):
                                        d = _modules[m]
                                        if (c in d):
                                            n = d[c]
                            names.append(n)
                            super = []
                        if (token == '('):
                            level += 1
                        elif (token == ')'):
                            level -= 1
                            if (level == 0):
                                break
                        elif ((token == ',') and (level == 1)):
                            pass
                        elif ((tokentype in (NAME, OP)) and (level == 1)):
                            super.append(token)
                    inherit = names
                if stack:
                    cur_obj = stack[(- 1)][0]
                    cur_class = _nest_class(cur_obj, class_name, lineno, inherit)
                else:
                    cur_class = Class(fullmodule, class_name, inherit, fname, lineno)
                    tree[class_name] = cur_class
                stack.append((cur_class, thisindent))
            elif ((token == 'import') and (start[1] == 0)):
                modules = _getnamelist(g)
                for (mod, _mod2) in modules:
                    try:
                        if (inpackage is None):
                            _readmodule(mod, path)
                        else:
                            try:
                                _readmodule(mod, path, inpackage)
                            except ImportError:
                                _readmodule(mod, [])
                    except:
                        pass
            elif ((token == 'from') and (start[1] == 0)):
                (mod, token) = _getname(g)
                if ((not mod) or (token != 'import')):
                    continue
                names = _getnamelist(g)
                try:
                    d = _readmodule(mod, path, inpackage)
                except:
                    continue
                for (n, n2) in names:
                    if (n in d):
                        tree[(n2 or n)] = d[n]
                    elif (n == '*'):
                        for n in d:
                            if (n[0] != '_'):
                                tree[n] = d[n]
    except StopIteration:
        pass
    f.close()
    return tree

def _getnamelist(g):
    "Return list of (dotted-name, as-name or None) tuples for token source g.\n\n    An as-name is the name that follows 'as' in an as clause.\n    "
    names = []
    while True:
        (name, token) = _getname(g)
        if (not name):
            break
        if (token == 'as'):
            (name2, token) = _getname(g)
        else:
            name2 = None
        names.append((name, name2))
        while ((token != ',') and ('\n' not in token)):
            token = next(g)[1]
        if (token != ','):
            break
    return names

def _getname(g):
    'Return (dotted-name or None, next-token) tuple for token source g.'
    parts = []
    (tokentype, token) = next(g)[0:2]
    if ((tokentype != NAME) and (token != '*')):
        return (None, token)
    parts.append(token)
    while True:
        (tokentype, token) = next(g)[0:2]
        if (token != '.'):
            break
        (tokentype, token) = next(g)[0:2]
        if (tokentype != NAME):
            break
        parts.append(token)
    return ('.'.join(parts), token)

def _main():
    'Print module output (default this file) for quick visual check.'
    import os
    try:
        mod = sys.argv[1]
    except:
        mod = __file__
    if os.path.exists(mod):
        path = [os.path.dirname(mod)]
        mod = os.path.basename(mod)
        if mod.lower().endswith('.py'):
            mod = mod[:(- 3)]
    else:
        path = []
    tree = readmodule_ex(mod, path)
    lineno_key = (lambda a: getattr(a, 'lineno', 0))
    objs = sorted(tree.values(), key=lineno_key, reverse=True)
    indent_level = 2
    while objs:
        obj = objs.pop()
        if isinstance(obj, list):
            continue
        if (not hasattr(obj, 'indent')):
            obj.indent = 0
        if isinstance(obj, _Object):
            new_objs = sorted(obj.children.values(), key=lineno_key, reverse=True)
            for ob in new_objs:
                ob.indent = (obj.indent + indent_level)
            objs.extend(new_objs)
        if isinstance(obj, Class):
            print('{}class {} {} {}'.format((' ' * obj.indent), obj.name, obj.super, obj.lineno))
        elif isinstance(obj, Function):
            print('{}def {} {}'.format((' ' * obj.indent), obj.name, obj.lineno))
if (__name__ == '__main__'):
    _main()
