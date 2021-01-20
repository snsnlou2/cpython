
import zipfile
import pathlib
from . import abc

class FileReader(abc.TraversableResources):

    def __init__(self, loader):
        self.path = pathlib.Path(loader.path).parent

    def resource_path(self, resource):
        '\n        Return the file system path to prevent\n        `resources.path()` from creating a temporary\n        copy.\n        '
        return str(self.path.joinpath(resource))

    def files(self):
        return self.path

class ZipReader(abc.TraversableResources):

    def __init__(self, loader, module):
        (_, _, name) = module.rpartition('.')
        prefix = ((loader.prefix.replace('\\', '/') + name) + '/')
        self.path = zipfile.Path(loader.archive, prefix)

    def open_resource(self, resource):
        try:
            return super().open_resource(resource)
        except KeyError as exc:
            raise FileNotFoundError(exc.args[0])

    def is_resource(self, path):
        target = self.files().joinpath(path)
        return (target.is_file() and target.exists())

    def files(self):
        return self.path
