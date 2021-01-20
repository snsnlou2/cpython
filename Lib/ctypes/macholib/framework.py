
'\nGeneric framework path manipulation\n'
import re
__all__ = ['framework_info']
STRICT_FRAMEWORK_RE = re.compile('(?x)\n(?P<location>^.*)(?:^|/)\n(?P<name>\n    (?P<shortname>\\w+).framework/\n    (?:Versions/(?P<version>[^/]+)/)?\n    (?P=shortname)\n    (?:_(?P<suffix>[^_]+))?\n)$\n')

def framework_info(filename):
    "\n    A framework name can take one of the following four forms:\n        Location/Name.framework/Versions/SomeVersion/Name_Suffix\n        Location/Name.framework/Versions/SomeVersion/Name\n        Location/Name.framework/Name_Suffix\n        Location/Name.framework/Name\n\n    returns None if not found, or a mapping equivalent to:\n        dict(\n            location='Location',\n            name='Name.framework/Versions/SomeVersion/Name_Suffix',\n            shortname='Name',\n            version='SomeVersion',\n            suffix='Suffix',\n        )\n\n    Note that SomeVersion and Suffix are optional and may be None\n    if not present\n    "
    is_framework = STRICT_FRAMEWORK_RE.match(filename)
    if (not is_framework):
        return None
    return is_framework.groupdict()

def test_framework_info():

    def d(location=None, name=None, shortname=None, version=None, suffix=None):
        return dict(location=location, name=name, shortname=shortname, version=version, suffix=suffix)
    assert (framework_info('completely/invalid') is None)
    assert (framework_info('completely/invalid/_debug') is None)
    assert (framework_info('P/F.framework') is None)
    assert (framework_info('P/F.framework/_debug') is None)
    assert (framework_info('P/F.framework/F') == d('P', 'F.framework/F', 'F'))
    assert (framework_info('P/F.framework/F_debug') == d('P', 'F.framework/F_debug', 'F', suffix='debug'))
    assert (framework_info('P/F.framework/Versions') is None)
    assert (framework_info('P/F.framework/Versions/A') is None)
    assert (framework_info('P/F.framework/Versions/A/F') == d('P', 'F.framework/Versions/A/F', 'F', 'A'))
    assert (framework_info('P/F.framework/Versions/A/F_debug') == d('P', 'F.framework/Versions/A/F_debug', 'F', 'A', 'debug'))
if (__name__ == '__main__'):
    test_framework_info()
