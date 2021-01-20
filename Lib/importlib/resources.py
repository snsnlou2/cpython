
import os
from . import _common
from ._common import as_file, files
from contextlib import contextmanager, suppress
from importlib.abc import ResourceLoader
from io import BytesIO, TextIOWrapper
from pathlib import Path
from types import ModuleType
from typing import ContextManager, Iterable, Union
from typing import cast
from typing.io import BinaryIO, TextIO
__all__ = ['Package', 'Resource', 'as_file', 'contents', 'files', 'is_resource', 'open_binary', 'open_text', 'path', 'read_binary', 'read_text']
Package = Union[(str, ModuleType)]
Resource = Union[(str, os.PathLike)]

def open_binary(package, resource):
    'Return a file-like object opened for binary reading of the resource.'
    resource = _common.normalize_path(resource)
    package = _common.get_package(package)
    reader = _common.get_resource_reader(package)
    if (reader is not None):
        return reader.open_resource(resource)
    absolute_package_path = os.path.abspath((package.__spec__.origin or 'non-existent file'))
    package_path = os.path.dirname(absolute_package_path)
    full_path = os.path.join(package_path, resource)
    try:
        return open(full_path, mode='rb')
    except OSError:
        loader = cast(ResourceLoader, package.__spec__.loader)
        data = None
        if hasattr(package.__spec__.loader, 'get_data'):
            with suppress(OSError):
                data = loader.get_data(full_path)
        if (data is None):
            package_name = package.__spec__.name
            message = '{!r} resource not found in {!r}'.format(resource, package_name)
            raise FileNotFoundError(message)
        return BytesIO(data)

def open_text(package, resource, encoding='utf-8', errors='strict'):
    'Return a file-like object opened for text reading of the resource.'
    return TextIOWrapper(open_binary(package, resource), encoding=encoding, errors=errors)

def read_binary(package, resource):
    'Return the binary contents of the resource.'
    with open_binary(package, resource) as fp:
        return fp.read()

def read_text(package, resource, encoding='utf-8', errors='strict'):
    'Return the decoded string of the resource.\n\n    The decoding-related arguments have the same semantics as those of\n    bytes.decode().\n    '
    with open_text(package, resource, encoding, errors) as fp:
        return fp.read()

def path(package, resource):
    'A context manager providing a file path object to the resource.\n\n    If the resource does not already exist on its own on the file system,\n    a temporary file will be created. If the file was created, the file\n    will be deleted upon exiting the context manager (no exception is\n    raised if the file was deleted prior to the context manager\n    exiting).\n    '
    reader = _common.get_resource_reader(_common.get_package(package))
    return (_path_from_reader(reader, resource) if reader else _common.as_file(_common.files(package).joinpath(_common.normalize_path(resource))))

@contextmanager
def _path_from_reader(reader, resource):
    norm_resource = _common.normalize_path(resource)
    with suppress(FileNotFoundError):
        (yield Path(reader.resource_path(norm_resource)))
        return
    opener_reader = reader.open_resource(norm_resource)
    with _common._tempfile(opener_reader.read, suffix=norm_resource) as res:
        (yield res)

def is_resource(package, name):
    "True if 'name' is a resource inside 'package'.\n\n    Directories are *not* resources.\n    "
    package = _common.get_package(package)
    _common.normalize_path(name)
    reader = _common.get_resource_reader(package)
    if (reader is not None):
        return reader.is_resource(name)
    package_contents = set(contents(package))
    if (name not in package_contents):
        return False
    return (_common.from_package(package) / name).is_file()

def contents(package):
    "Return an iterable of entries in 'package'.\n\n    Note that not all entries are resources.  Specifically, directories are\n    not considered resources.  Use `is_resource()` on each entry returned here\n    to check if it is a resource or not.\n    "
    package = _common.get_package(package)
    reader = _common.get_resource_reader(package)
    if (reader is not None):
        return reader.contents()
    namespace = ((package.__spec__.origin is None) or (package.__spec__.origin == 'namespace'))
    if (namespace or (not package.__spec__.has_location)):
        return ()
    return list((item.name for item in _common.from_package(package).iterdir()))
