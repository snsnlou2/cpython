
"distutils.command.bdist_wininst\n\nSuppress the 'bdist_wininst' command, while still allowing\nsetuptools to import it without breaking."
from distutils.core import Command
from distutils.errors import DistutilsPlatformError

class bdist_wininst(Command):
    description = 'create an executable installer for MS Windows'
    _unsupported = True

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        raise DistutilsPlatformError('bdist_wininst is not supported in this Python distribution')
