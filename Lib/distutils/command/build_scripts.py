
"distutils.command.build_scripts\n\nImplements the Distutils 'build_scripts' command."
import os, re
from stat import ST_MODE
from distutils import sysconfig
from distutils.core import Command
from distutils.dep_util import newer
from distutils.util import convert_path, Mixin2to3
from distutils import log
import tokenize
first_line_re = re.compile(b'^#!.*python[0-9.]*([ \t].*)?$')

class build_scripts(Command):
    description = '"build" scripts (copy and fixup #! line)'
    user_options = [('build-dir=', 'd', 'directory to "build" (copy) to'), ('force', 'f', 'forcibly build everything (ignore file timestamps'), ('executable=', 'e', 'specify final destination interpreter path')]
    boolean_options = ['force']

    def initialize_options(self):
        self.build_dir = None
        self.scripts = None
        self.force = None
        self.executable = None
        self.outfiles = None

    def finalize_options(self):
        self.set_undefined_options('build', ('build_scripts', 'build_dir'), ('force', 'force'), ('executable', 'executable'))
        self.scripts = self.distribution.scripts

    def get_source_files(self):
        return self.scripts

    def run(self):
        if (not self.scripts):
            return
        self.copy_scripts()

    def copy_scripts(self):
        'Copy each script listed in \'self.scripts\'; if it\'s marked as a\n        Python script in the Unix way (first line matches \'first_line_re\',\n        ie. starts with "\\#!" and contains "python"), then adjust the first\n        line to refer to the current Python interpreter as we copy.\n        '
        self.mkpath(self.build_dir)
        outfiles = []
        updated_files = []
        for script in self.scripts:
            adjust = False
            script = convert_path(script)
            outfile = os.path.join(self.build_dir, os.path.basename(script))
            outfiles.append(outfile)
            if ((not self.force) and (not newer(script, outfile))):
                log.debug('not copying %s (up-to-date)', script)
                continue
            try:
                f = open(script, 'rb')
            except OSError:
                if (not self.dry_run):
                    raise
                f = None
            else:
                (encoding, lines) = tokenize.detect_encoding(f.readline)
                f.seek(0)
                first_line = f.readline()
                if (not first_line):
                    self.warn(('%s is an empty file (skipping)' % script))
                    continue
                match = first_line_re.match(first_line)
                if match:
                    adjust = True
                    post_interp = (match.group(1) or b'')
            if adjust:
                log.info('copying and adjusting %s -> %s', script, self.build_dir)
                updated_files.append(outfile)
                if (not self.dry_run):
                    if (not sysconfig.python_build):
                        executable = self.executable
                    else:
                        executable = os.path.join(sysconfig.get_config_var('BINDIR'), ('python%s%s' % (sysconfig.get_config_var('VERSION'), sysconfig.get_config_var('EXE'))))
                    executable = os.fsencode(executable)
                    shebang = (((b'#!' + executable) + post_interp) + b'\n')
                    try:
                        shebang.decode('utf-8')
                    except UnicodeDecodeError:
                        raise ValueError('The shebang ({!r}) is not decodable from utf-8'.format(shebang))
                    try:
                        shebang.decode(encoding)
                    except UnicodeDecodeError:
                        raise ValueError('The shebang ({!r}) is not decodable from the script encoding ({})'.format(shebang, encoding))
                    with open(outfile, 'wb') as outf:
                        outf.write(shebang)
                        outf.writelines(f.readlines())
                if f:
                    f.close()
            else:
                if f:
                    f.close()
                updated_files.append(outfile)
                self.copy_file(script, outfile)
        if (os.name == 'posix'):
            for file in outfiles:
                if self.dry_run:
                    log.info('changing mode of %s', file)
                else:
                    oldmode = (os.stat(file)[ST_MODE] & 4095)
                    newmode = ((oldmode | 365) & 4095)
                    if (newmode != oldmode):
                        log.info('changing mode of %s from %o to %o', file, oldmode, newmode)
                        os.chmod(file, newmode)
        return (outfiles, updated_files)

class build_scripts_2to3(build_scripts, Mixin2to3):

    def copy_scripts(self):
        (outfiles, updated_files) = build_scripts.copy_scripts(self)
        if (not self.dry_run):
            self.run_2to3(updated_files)
        return (outfiles, updated_files)
