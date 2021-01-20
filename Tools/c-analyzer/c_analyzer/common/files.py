
import glob
import os
import os.path
C_SOURCE_SUFFIXES = ('.c', '.h')

def _walk_tree(root, *, _walk=os.walk):
    for (parent, _, names) in _walk(root):
        for name in names:
            (yield os.path.join(parent, name))

def walk_tree(root, *, suffix=None, walk=_walk_tree):
    'Yield each file in the tree under the given directory name.\n\n    If "suffix" is provided then only files with that suffix will\n    be included.\n    '
    if (suffix and (not isinstance(suffix, str))):
        raise ValueError('suffix must be a string')
    for filename in walk(root):
        if (suffix and (not filename.endswith(suffix))):
            continue
        (yield filename)

def glob_tree(root, *, suffix=None, _glob=glob.iglob, _escape=glob.escape, _join=os.path.join):
    'Yield each file in the tree under the given directory name.\n\n    If "suffix" is provided then only files with that suffix will\n    be included.\n    '
    suffix = (suffix or '')
    if (not isinstance(suffix, str)):
        raise ValueError('suffix must be a string')
    for filename in _glob(_join(_escape(root), f'*{suffix}')):
        (yield filename)
    for filename in _glob(_join(_escape(root), f'**/*{suffix}')):
        (yield filename)

def iter_files(root, suffix=None, relparent=None, *, get_files=os.walk, _glob=glob_tree, _walk=walk_tree):
    'Yield each file in the tree under the given directory name.\n\n    If "root" is a non-string iterable then do the same for each of\n    those trees.\n\n    If "suffix" is provided then only files with that suffix will\n    be included.\n\n    if "relparent" is provided then it is used to resolve each\n    filename as a relative path.\n    '
    if (not isinstance(root, str)):
        roots = root
        for root in roots:
            (yield from iter_files(root, suffix, relparent, get_files=get_files, _glob=_glob, _walk=_walk))
        return
    if (get_files in (glob.glob, glob.iglob, glob_tree)):
        get_files = _glob
    else:
        _files = (_walk_tree if (get_files in (os.walk, walk_tree)) else get_files)
        get_files = (lambda *a, **k: _walk(*a, walk=_files, **k))
    if (suffix and (not isinstance(suffix, str))):
        filenames = get_files(root)
        suffix = tuple(suffix)
    else:
        filenames = get_files(root, suffix=suffix)
        suffix = None
    for filename in filenames:
        if (suffix and (not isinstance(suffix, str))):
            if (not filename.endswith(suffix)):
                continue
        if relparent:
            filename = os.path.relpath(filename, relparent)
        (yield filename)

def iter_files_by_suffix(root, suffixes, relparent=None, *, walk=walk_tree, _iter_files=iter_files):
    'Yield each file in the tree that has the given suffixes.\n\n    Unlike iter_files(), the results are in the original suffix order.\n    '
    if isinstance(suffixes, str):
        suffixes = [suffixes]
    for suffix in suffixes:
        (yield from _iter_files(root, suffix, relparent))
