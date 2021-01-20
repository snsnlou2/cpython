
import collections
import configparser
import io
import os
import pathlib
import textwrap
import unittest
import warnings
from test import support
from test.support import os_helper

class SortedDict(collections.UserDict):

    def items(self):
        return sorted(self.data.items())

    def keys(self):
        return sorted(self.data.keys())

    def values(self):
        return [i[1] for i in self.items()]

    def iteritems(self):
        return iter(self.items())

    def iterkeys(self):
        return iter(self.keys())

    def itervalues(self):
        return iter(self.values())
    __iter__ = iterkeys

class CfgParserTestCaseClass():
    allow_no_value = False
    delimiters = ('=', ':')
    comment_prefixes = (';', '#')
    inline_comment_prefixes = (';', '#')
    empty_lines_in_values = True
    dict_type = configparser._default_dict
    strict = False
    default_section = configparser.DEFAULTSECT
    interpolation = configparser._UNSET

    def newconfig(self, defaults=None):
        arguments = dict(defaults=defaults, allow_no_value=self.allow_no_value, delimiters=self.delimiters, comment_prefixes=self.comment_prefixes, inline_comment_prefixes=self.inline_comment_prefixes, empty_lines_in_values=self.empty_lines_in_values, dict_type=self.dict_type, strict=self.strict, default_section=self.default_section, interpolation=self.interpolation)
        instance = self.config_class(**arguments)
        return instance

    def fromstring(self, string, defaults=None):
        cf = self.newconfig(defaults)
        cf.read_string(string)
        return cf

class BasicTestCase(CfgParserTestCaseClass):

    def basic_test(self, cf):
        E = ['Commented Bar', 'Foo Bar', 'Internationalized Stuff', 'Long Line', 'Section\\with$weird%characters[\t', 'Spaces', 'Spacey Bar', 'Spacey Bar From The Beginning', 'Types']
        if self.allow_no_value:
            E.append('NoValue')
        E.sort()
        F = [('baz', 'qwe'), ('foo', 'bar3')]
        L = cf.sections()
        L.sort()
        eq = self.assertEqual
        eq(L, E)
        L = cf.items('Spacey Bar From The Beginning')
        L.sort()
        eq(L, F)
        L = [section for section in cf]
        L.sort()
        E.append(self.default_section)
        E.sort()
        eq(L, E)
        L = cf['Spacey Bar From The Beginning'].items()
        L = sorted(list(L))
        eq(L, F)
        L = cf.items()
        L = sorted(list(L))
        self.assertEqual(len(L), len(E))
        for (name, section) in L:
            eq(name, section.name)
        eq(cf.defaults(), cf[self.default_section])
        eq(cf.get('Foo Bar', 'foo'), 'bar1')
        eq(cf.get('Spacey Bar', 'foo'), 'bar2')
        eq(cf.get('Spacey Bar From The Beginning', 'foo'), 'bar3')
        eq(cf.get('Spacey Bar From The Beginning', 'baz'), 'qwe')
        eq(cf.get('Commented Bar', 'foo'), 'bar4')
        eq(cf.get('Commented Bar', 'baz'), 'qwe')
        eq(cf.get('Spaces', 'key with spaces'), 'value')
        eq(cf.get('Spaces', 'another with spaces'), 'splat!')
        eq(cf.getint('Types', 'int'), 42)
        eq(cf.get('Types', 'int'), '42')
        self.assertAlmostEqual(cf.getfloat('Types', 'float'), 0.44)
        eq(cf.get('Types', 'float'), '0.44')
        eq(cf.getboolean('Types', 'boolean'), False)
        eq(cf.get('Types', '123'), 'strange but acceptable')
        if self.allow_no_value:
            eq(cf.get('NoValue', 'option-without-value'), None)
        eq(cf.get('Foo Bar', 'foo', fallback='baz'), 'bar1')
        eq(cf.get('Foo Bar', 'foo', vars={'foo': 'baz'}), 'baz')
        with self.assertRaises(configparser.NoSectionError):
            cf.get('No Such Foo Bar', 'foo')
        with self.assertRaises(configparser.NoOptionError):
            cf.get('Foo Bar', 'no-such-foo')
        eq(cf.get('No Such Foo Bar', 'foo', fallback='baz'), 'baz')
        eq(cf.get('Foo Bar', 'no-such-foo', fallback='baz'), 'baz')
        eq(cf.get('Spacey Bar', 'foo', fallback=None), 'bar2')
        eq(cf.get('No Such Spacey Bar', 'foo', fallback=None), None)
        eq(cf.getint('Types', 'int', fallback=18), 42)
        eq(cf.getint('Types', 'no-such-int', fallback=18), 18)
        eq(cf.getint('Types', 'no-such-int', fallback='18'), '18')
        with self.assertRaises(configparser.NoOptionError):
            cf.getint('Types', 'no-such-int')
        self.assertAlmostEqual(cf.getfloat('Types', 'float', fallback=0.0), 0.44)
        self.assertAlmostEqual(cf.getfloat('Types', 'no-such-float', fallback=0.0), 0.0)
        eq(cf.getfloat('Types', 'no-such-float', fallback='0.0'), '0.0')
        with self.assertRaises(configparser.NoOptionError):
            cf.getfloat('Types', 'no-such-float')
        eq(cf.getboolean('Types', 'boolean', fallback=True), False)
        eq(cf.getboolean('Types', 'no-such-boolean', fallback='yes'), 'yes')
        eq(cf.getboolean('Types', 'no-such-boolean', fallback=True), True)
        with self.assertRaises(configparser.NoOptionError):
            cf.getboolean('Types', 'no-such-boolean')
        eq(cf.getboolean('No Such Types', 'boolean', fallback=True), True)
        if self.allow_no_value:
            eq(cf.get('NoValue', 'option-without-value', fallback=False), None)
            eq(cf.get('NoValue', 'no-such-option-without-value', fallback=False), False)
        eq(cf['Foo Bar']['foo'], 'bar1')
        eq(cf['Spacey Bar']['foo'], 'bar2')
        section = cf['Spacey Bar From The Beginning']
        eq(section.name, 'Spacey Bar From The Beginning')
        self.assertIs(section.parser, cf)
        with self.assertRaises(AttributeError):
            section.name = 'Name is read-only'
        with self.assertRaises(AttributeError):
            section.parser = 'Parser is read-only'
        eq(section['foo'], 'bar3')
        eq(section['baz'], 'qwe')
        eq(cf['Commented Bar']['foo'], 'bar4')
        eq(cf['Commented Bar']['baz'], 'qwe')
        eq(cf['Spaces']['key with spaces'], 'value')
        eq(cf['Spaces']['another with spaces'], 'splat!')
        eq(cf['Long Line']['foo'], 'this line is much, much longer than my editor\nlikes it.')
        if self.allow_no_value:
            eq(cf['NoValue']['option-without-value'], None)
        eq(cf['Foo Bar'].get('foo', 'baz'), 'bar1')
        eq(cf['Foo Bar'].get('foo', fallback='baz'), 'bar1')
        eq(cf['Foo Bar'].get('foo', vars={'foo': 'baz'}), 'baz')
        with self.assertRaises(KeyError):
            cf['No Such Foo Bar']['foo']
        with self.assertRaises(KeyError):
            cf['Foo Bar']['no-such-foo']
        with self.assertRaises(KeyError):
            cf['No Such Foo Bar'].get('foo', fallback='baz')
        eq(cf['Foo Bar'].get('no-such-foo', 'baz'), 'baz')
        eq(cf['Foo Bar'].get('no-such-foo', fallback='baz'), 'baz')
        eq(cf['Foo Bar'].get('no-such-foo'), None)
        eq(cf['Spacey Bar'].get('foo', None), 'bar2')
        eq(cf['Spacey Bar'].get('foo', fallback=None), 'bar2')
        with self.assertRaises(KeyError):
            cf['No Such Spacey Bar'].get('foo', None)
        eq(cf['Types'].getint('int', 18), 42)
        eq(cf['Types'].getint('int', fallback=18), 42)
        eq(cf['Types'].getint('no-such-int', 18), 18)
        eq(cf['Types'].getint('no-such-int', fallback=18), 18)
        eq(cf['Types'].getint('no-such-int', '18'), '18')
        eq(cf['Types'].getint('no-such-int', fallback='18'), '18')
        eq(cf['Types'].getint('no-such-int'), None)
        self.assertAlmostEqual(cf['Types'].getfloat('float', 0.0), 0.44)
        self.assertAlmostEqual(cf['Types'].getfloat('float', fallback=0.0), 0.44)
        self.assertAlmostEqual(cf['Types'].getfloat('no-such-float', 0.0), 0.0)
        self.assertAlmostEqual(cf['Types'].getfloat('no-such-float', fallback=0.0), 0.0)
        eq(cf['Types'].getfloat('no-such-float', '0.0'), '0.0')
        eq(cf['Types'].getfloat('no-such-float', fallback='0.0'), '0.0')
        eq(cf['Types'].getfloat('no-such-float'), None)
        eq(cf['Types'].getboolean('boolean', True), False)
        eq(cf['Types'].getboolean('boolean', fallback=True), False)
        eq(cf['Types'].getboolean('no-such-boolean', 'yes'), 'yes')
        eq(cf['Types'].getboolean('no-such-boolean', fallback='yes'), 'yes')
        eq(cf['Types'].getboolean('no-such-boolean', True), True)
        eq(cf['Types'].getboolean('no-such-boolean', fallback=True), True)
        eq(cf['Types'].getboolean('no-such-boolean'), None)
        if self.allow_no_value:
            eq(cf['NoValue'].get('option-without-value', False), None)
            eq(cf['NoValue'].get('option-without-value', fallback=False), None)
            eq(cf['NoValue'].get('no-such-option-without-value', False), False)
            eq(cf['NoValue'].get('no-such-option-without-value', fallback=False), False)
        cf[self.default_section]['this_value'] = '1'
        cf[self.default_section]['that_value'] = '2'
        self.assertTrue(cf.remove_section('Spaces'))
        self.assertFalse(cf.has_option('Spaces', 'key with spaces'))
        self.assertFalse(cf.remove_section('Spaces'))
        self.assertFalse(cf.remove_section(self.default_section))
        self.assertTrue(cf.remove_option('Foo Bar', 'foo'), 'remove_option() failed to report existence of option')
        self.assertFalse(cf.has_option('Foo Bar', 'foo'), 'remove_option() failed to remove option')
        self.assertFalse(cf.remove_option('Foo Bar', 'foo'), 'remove_option() failed to report non-existence of option that was removed')
        self.assertTrue(cf.has_option('Foo Bar', 'this_value'))
        self.assertFalse(cf.remove_option('Foo Bar', 'this_value'))
        self.assertTrue(cf.remove_option(self.default_section, 'this_value'))
        self.assertFalse(cf.has_option('Foo Bar', 'this_value'))
        self.assertFalse(cf.remove_option(self.default_section, 'this_value'))
        with self.assertRaises(configparser.NoSectionError) as cm:
            cf.remove_option('No Such Section', 'foo')
        self.assertEqual(cm.exception.args, ('No Such Section',))
        eq(cf.get('Long Line', 'foo'), 'this line is much, much longer than my editor\nlikes it.')
        del cf['Types']
        self.assertFalse(('Types' in cf))
        with self.assertRaises(KeyError):
            del cf['Types']
        with self.assertRaises(ValueError):
            del cf[self.default_section]
        del cf['Spacey Bar']['foo']
        self.assertFalse(('foo' in cf['Spacey Bar']))
        with self.assertRaises(KeyError):
            del cf['Spacey Bar']['foo']
        self.assertTrue(('that_value' in cf['Spacey Bar']))
        with self.assertRaises(KeyError):
            del cf['Spacey Bar']['that_value']
        del cf[self.default_section]['that_value']
        self.assertFalse(('that_value' in cf['Spacey Bar']))
        with self.assertRaises(KeyError):
            del cf[self.default_section]['that_value']
        with self.assertRaises(KeyError):
            del cf['No Such Section']['foo']

    def test_basic(self):
        config_string = '[Foo Bar]\nfoo{0[0]}bar1\n[Spacey Bar]\nfoo {0[0]} bar2\n[Spacey Bar From The Beginning]\n  foo {0[0]} bar3\n  baz {0[0]} qwe\n[Commented Bar]\nfoo{0[1]} bar4 {1[1]} comment\nbaz{0[0]}qwe {1[0]}another one\n[Long Line]\nfoo{0[1]} this line is much, much longer than my editor\n   likes it.\n[Section\\with$weird%characters[\t]\n[Internationalized Stuff]\nfoo[bg]{0[1]} Bulgarian\nfoo{0[0]}Default\nfoo[en]{0[0]}English\nfoo[de]{0[0]}Deutsch\n[Spaces]\nkey with spaces {0[1]} value\nanother with spaces {0[0]} splat!\n[Types]\nint {0[1]} 42\nfloat {0[0]} 0.44\nboolean {0[0]} NO\n123 {0[1]} strange but acceptable\n'.format(self.delimiters, self.comment_prefixes)
        if self.allow_no_value:
            config_string += '[NoValue]\noption-without-value\n'
        cf = self.fromstring(config_string)
        self.basic_test(cf)
        if self.strict:
            with self.assertRaises(configparser.DuplicateOptionError):
                cf.read_string(textwrap.dedent('                    [Duplicate Options Here]\n                    option {0[0]} with a value\n                    option {0[1]} with another value\n                '.format(self.delimiters)))
            with self.assertRaises(configparser.DuplicateSectionError):
                cf.read_string(textwrap.dedent('                    [And Now For Something]\n                    completely different {0[0]} True\n                    [And Now For Something]\n                    the larch {0[1]} 1\n                '.format(self.delimiters)))
        else:
            cf.read_string(textwrap.dedent('                [Duplicate Options Here]\n                option {0[0]} with a value\n                option {0[1]} with another value\n            '.format(self.delimiters)))
            cf.read_string(textwrap.dedent('                [And Now For Something]\n                completely different {0[0]} True\n                [And Now For Something]\n                the larch {0[1]} 1\n            '.format(self.delimiters)))

    def test_basic_from_dict(self):
        config = {'Foo Bar': {'foo': 'bar1'}, 'Spacey Bar': {'foo': 'bar2'}, 'Spacey Bar From The Beginning': {'foo': 'bar3', 'baz': 'qwe'}, 'Commented Bar': {'foo': 'bar4', 'baz': 'qwe'}, 'Long Line': {'foo': 'this line is much, much longer than my editor\nlikes it.'}, 'Section\\with$weird%characters[\t': {}, 'Internationalized Stuff': {'foo[bg]': 'Bulgarian', 'foo': 'Default', 'foo[en]': 'English', 'foo[de]': 'Deutsch'}, 'Spaces': {'key with spaces': 'value', 'another with spaces': 'splat!'}, 'Types': {'int': 42, 'float': 0.44, 'boolean': False, 123: 'strange but acceptable'}}
        if self.allow_no_value:
            config.update({'NoValue': {'option-without-value': None}})
        cf = self.newconfig()
        cf.read_dict(config)
        self.basic_test(cf)
        if self.strict:
            with self.assertRaises(configparser.DuplicateSectionError):
                cf.read_dict({'1': {'key': 'value'}, 1: {'key2': 'value2'}})
            with self.assertRaises(configparser.DuplicateOptionError):
                cf.read_dict({'Duplicate Options Here': {'option': 'with a value', 'OPTION': 'with another value'}})
        else:
            cf.read_dict({'section': {'key': 'value'}, 'SECTION': {'key2': 'value2'}})
            cf.read_dict({'Duplicate Options Here': {'option': 'with a value', 'OPTION': 'with another value'}})

    def test_case_sensitivity(self):
        cf = self.newconfig()
        cf.add_section('A')
        cf.add_section('a')
        cf.add_section('B')
        L = cf.sections()
        L.sort()
        eq = self.assertEqual
        eq(L, ['A', 'B', 'a'])
        cf.set('a', 'B', 'value')
        eq(cf.options('a'), ['b'])
        eq(cf.get('a', 'b'), 'value', 'could not locate option, expecting case-insensitive option names')
        with self.assertRaises(configparser.NoSectionError):
            cf.set('b', 'A', 'value')
        self.assertTrue(cf.has_option('a', 'b'))
        self.assertFalse(cf.has_option('b', 'b'))
        cf.set('A', 'A-B', 'A-B value')
        for opt in ('a-b', 'A-b', 'a-B', 'A-B'):
            self.assertTrue(cf.has_option('A', opt), 'has_option() returned false for option which should exist')
        eq(cf.options('A'), ['a-b'])
        eq(cf.options('a'), ['b'])
        cf.remove_option('a', 'B')
        eq(cf.options('a'), [])
        cf = self.fromstring('[MySection]\nOption{} first line   \n\tsecond line   \n'.format(self.delimiters[0]))
        eq(cf.options('MySection'), ['option'])
        eq(cf.get('MySection', 'Option'), 'first line\nsecond line')
        cf = self.fromstring('[section]\nnekey{}nevalue\n'.format(self.delimiters[0]), defaults={'key': 'value'})
        self.assertTrue(cf.has_option('section', 'Key'))

    def test_case_sensitivity_mapping_access(self):
        cf = self.newconfig()
        cf['A'] = {}
        cf['a'] = {'B': 'value'}
        cf['B'] = {}
        L = [section for section in cf]
        L.sort()
        eq = self.assertEqual
        elem_eq = self.assertCountEqual
        eq(L, sorted(['A', 'B', self.default_section, 'a']))
        eq(cf['a'].keys(), {'b'})
        eq(cf['a']['b'], 'value', 'could not locate option, expecting case-insensitive option names')
        with self.assertRaises(KeyError):
            cf['b']['A'] = 'value'
        self.assertTrue(('b' in cf['a']))
        cf['A']['A-B'] = 'A-B value'
        for opt in ('a-b', 'A-b', 'a-B', 'A-B'):
            self.assertTrue((opt in cf['A']), 'has_option() returned false for option which should exist')
        eq(cf['A'].keys(), {'a-b'})
        eq(cf['a'].keys(), {'b'})
        del cf['a']['B']
        elem_eq(cf['a'].keys(), {})
        cf = self.fromstring('[MySection]\nOption{} first line   \n\tsecond line   \n'.format(self.delimiters[0]))
        eq(cf['MySection'].keys(), {'option'})
        eq(cf['MySection']['Option'], 'first line\nsecond line')
        cf = self.fromstring('[section]\nnekey{}nevalue\n'.format(self.delimiters[0]), defaults={'key': 'value'})
        self.assertTrue(('Key' in cf['section']))

    def test_default_case_sensitivity(self):
        cf = self.newconfig({'foo': 'Bar'})
        self.assertEqual(cf.get(self.default_section, 'Foo'), 'Bar', 'could not locate option, expecting case-insensitive option names')
        cf = self.newconfig({'Foo': 'Bar'})
        self.assertEqual(cf.get(self.default_section, 'Foo'), 'Bar', 'could not locate option, expecting case-insensitive defaults')

    def test_parse_errors(self):
        cf = self.newconfig()
        self.parse_error(cf, configparser.ParsingError, '[Foo]\n{}val-without-opt-name\n'.format(self.delimiters[0]))
        self.parse_error(cf, configparser.ParsingError, '[Foo]\n{}val-without-opt-name\n'.format(self.delimiters[1]))
        e = self.parse_error(cf, configparser.MissingSectionHeaderError, 'No Section!\n')
        self.assertEqual(e.args, ('<???>', 1, 'No Section!\n'))
        if (not self.allow_no_value):
            e = self.parse_error(cf, configparser.ParsingError, '[Foo]\n  wrong-indent\n')
            self.assertEqual(e.args, ('<???>',))
            tricky = support.findfile('cfgparser.3')
            if (self.delimiters[0] == '='):
                error = configparser.ParsingError
                expected = (tricky,)
            else:
                error = configparser.MissingSectionHeaderError
                expected = (tricky, 1, '  # INI with as many tricky parts as possible\n')
            with open(tricky, encoding='utf-8') as f:
                e = self.parse_error(cf, error, f)
            self.assertEqual(e.args, expected)

    def parse_error(self, cf, exc, src):
        if hasattr(src, 'readline'):
            sio = src
        else:
            sio = io.StringIO(src)
        with self.assertRaises(exc) as cm:
            cf.read_file(sio)
        return cm.exception

    def test_query_errors(self):
        cf = self.newconfig()
        self.assertEqual(cf.sections(), [], 'new ConfigParser should have no defined sections')
        self.assertFalse(cf.has_section('Foo'), 'new ConfigParser should have no acknowledged sections')
        with self.assertRaises(configparser.NoSectionError):
            cf.options('Foo')
        with self.assertRaises(configparser.NoSectionError):
            cf.set('foo', 'bar', 'value')
        e = self.get_error(cf, configparser.NoSectionError, 'foo', 'bar')
        self.assertEqual(e.args, ('foo',))
        cf.add_section('foo')
        e = self.get_error(cf, configparser.NoOptionError, 'foo', 'bar')
        self.assertEqual(e.args, ('bar', 'foo'))

    def get_error(self, cf, exc, section, option):
        try:
            cf.get(section, option)
        except exc as e:
            return e
        else:
            self.fail(('expected exception type %s.%s' % (exc.__module__, exc.__qualname__)))

    def test_boolean(self):
        cf = self.fromstring('[BOOLTEST]\nT1{equals}1\nT2{equals}TRUE\nT3{equals}True\nT4{equals}oN\nT5{equals}yes\nF1{equals}0\nF2{equals}FALSE\nF3{equals}False\nF4{equals}oFF\nF5{equals}nO\nE1{equals}2\nE2{equals}foo\nE3{equals}-1\nE4{equals}0.1\nE5{equals}FALSE AND MORE'.format(equals=self.delimiters[0]))
        for x in range(1, 5):
            self.assertTrue(cf.getboolean('BOOLTEST', ('t%d' % x)))
            self.assertFalse(cf.getboolean('BOOLTEST', ('f%d' % x)))
            self.assertRaises(ValueError, cf.getboolean, 'BOOLTEST', ('e%d' % x))

    def test_weird_errors(self):
        cf = self.newconfig()
        cf.add_section('Foo')
        with self.assertRaises(configparser.DuplicateSectionError) as cm:
            cf.add_section('Foo')
        e = cm.exception
        self.assertEqual(str(e), "Section 'Foo' already exists")
        self.assertEqual(e.args, ('Foo', None, None))
        if self.strict:
            with self.assertRaises(configparser.DuplicateSectionError) as cm:
                cf.read_string(textwrap.dedent("                    [Foo]\n                    will this be added{equals}True\n                    [Bar]\n                    what about this{equals}True\n                    [Foo]\n                    oops{equals}this won't\n                ".format(equals=self.delimiters[0])), source='<foo-bar>')
            e = cm.exception
            self.assertEqual(str(e), "While reading from '<foo-bar>' [line  5]: section 'Foo' already exists")
            self.assertEqual(e.args, ('Foo', '<foo-bar>', 5))
            with self.assertRaises(configparser.DuplicateOptionError) as cm:
                cf.read_dict({'Bar': {'opt': 'val', 'OPT': 'is really `opt`'}})
            e = cm.exception
            self.assertEqual(str(e), "While reading from '<dict>': option 'opt' in section 'Bar' already exists")
            self.assertEqual(e.args, ('Bar', 'opt', '<dict>', None))

    def test_write(self):
        config_string = '[Long Line]\nfoo{0[0]} this line is much, much longer than my editor\n   likes it.\n[{default_section}]\nfoo{0[1]} another very\n long line\n[Long Line - With Comments!]\ntest {0[1]} we        {comment} can\n            also      {comment} place\n            comments  {comment} in\n            multiline {comment} values\n'.format(self.delimiters, comment=self.comment_prefixes[0], default_section=self.default_section)
        if self.allow_no_value:
            config_string += '[Valueless]\noption-without-value\n'
        cf = self.fromstring(config_string)
        for space_around_delimiters in (True, False):
            output = io.StringIO()
            cf.write(output, space_around_delimiters=space_around_delimiters)
            delimiter = self.delimiters[0]
            if space_around_delimiters:
                delimiter = ' {} '.format(delimiter)
            expect_string = '[{default_section}]\nfoo{equals}another very\n\tlong line\n\n[Long Line]\nfoo{equals}this line is much, much longer than my editor\n\tlikes it.\n\n[Long Line - With Comments!]\ntest{equals}we\n\talso\n\tcomments\n\tmultiline\n\n'.format(equals=delimiter, default_section=self.default_section)
            if self.allow_no_value:
                expect_string += '[Valueless]\noption-without-value\n\n'
            self.assertEqual(output.getvalue(), expect_string)

    def test_set_string_types(self):
        cf = self.fromstring('[sect]\noption1{eq}foo\n'.format(eq=self.delimiters[0]))

        class mystr(str):
            pass
        cf.set('sect', 'option1', 'splat')
        cf.set('sect', 'option1', mystr('splat'))
        cf.set('sect', 'option2', 'splat')
        cf.set('sect', 'option2', mystr('splat'))
        cf.set('sect', 'option1', 'splat')
        cf.set('sect', 'option2', 'splat')

    def test_read_returns_file_list(self):
        if (self.delimiters[0] != '='):
            self.skipTest('incompatible format')
        file1 = support.findfile('cfgparser.1')
        cf = self.newconfig()
        parsed_files = cf.read([file1, 'nonexistent-file'])
        self.assertEqual(parsed_files, [file1])
        self.assertEqual(cf.get('Foo Bar', 'foo'), 'newbar')
        cf = self.newconfig()
        parsed_files = cf.read(file1)
        self.assertEqual(parsed_files, [file1])
        self.assertEqual(cf.get('Foo Bar', 'foo'), 'newbar')
        cf = self.newconfig()
        parsed_files = cf.read(pathlib.Path(file1))
        self.assertEqual(parsed_files, [file1])
        self.assertEqual(cf.get('Foo Bar', 'foo'), 'newbar')
        cf = self.newconfig()
        parsed_files = cf.read([pathlib.Path(file1), file1])
        self.assertEqual(parsed_files, [file1, file1])
        self.assertEqual(cf.get('Foo Bar', 'foo'), 'newbar')
        cf = self.newconfig()
        parsed_files = cf.read(['nonexistent-file'])
        self.assertEqual(parsed_files, [])
        cf = self.newconfig()
        parsed_files = cf.read([])
        self.assertEqual(parsed_files, [])

    def test_read_returns_file_list_with_bytestring_path(self):
        if (self.delimiters[0] != '='):
            self.skipTest('incompatible format')
        file1_bytestring = support.findfile('cfgparser.1').encode()
        cf = self.newconfig()
        parsed_files = cf.read(file1_bytestring)
        self.assertEqual(parsed_files, [file1_bytestring])
        cf = self.newconfig()
        parsed_files = cf.read(b'nonexistent-file')
        self.assertEqual(parsed_files, [])
        cf = self.newconfig()
        parsed_files = cf.read([file1_bytestring, b'nonexistent-file'])
        self.assertEqual(parsed_files, [file1_bytestring])

    def get_interpolation_config(self):
        return self.fromstring('[Foo]\nbar{equals}something %(with1)s interpolation (1 step)\nbar9{equals}something %(with9)s lots of interpolation (9 steps)\nbar10{equals}something %(with10)s lots of interpolation (10 steps)\nbar11{equals}something %(with11)s lots of interpolation (11 steps)\nwith11{equals}%(with10)s\nwith10{equals}%(with9)s\nwith9{equals}%(with8)s\nwith8{equals}%(With7)s\nwith7{equals}%(WITH6)s\nwith6{equals}%(with5)s\nWith5{equals}%(with4)s\nWITH4{equals}%(with3)s\nwith3{equals}%(with2)s\nwith2{equals}%(with1)s\nwith1{equals}with\n\n[Mutual Recursion]\nfoo{equals}%(bar)s\nbar{equals}%(foo)s\n\n[Interpolation Error]\nname{equals}%(reference)s\n'.format(equals=self.delimiters[0]))

    def check_items_config(self, expected):
        cf = self.fromstring('\n            [section]\n            name {0[0]} %(value)s\n            key{0[1]} |%(name)s|\n            getdefault{0[1]} |%(default)s|\n        '.format(self.delimiters), defaults={'default': '<default>'})
        L = list(cf.items('section', vars={'value': 'value'}))
        L.sort()
        self.assertEqual(L, expected)
        with self.assertRaises(configparser.NoSectionError):
            cf.items('no such section')

    def test_popitem(self):
        cf = self.fromstring('\n            [section1]\n            name1 {0[0]} value1\n            [section2]\n            name2 {0[0]} value2\n            [section3]\n            name3 {0[0]} value3\n        '.format(self.delimiters), defaults={'default': '<default>'})
        self.assertEqual(cf.popitem()[0], 'section1')
        self.assertEqual(cf.popitem()[0], 'section2')
        self.assertEqual(cf.popitem()[0], 'section3')
        with self.assertRaises(KeyError):
            cf.popitem()

    def test_clear(self):
        cf = self.newconfig({'foo': 'Bar'})
        self.assertEqual(cf.get(self.default_section, 'Foo'), 'Bar', 'could not locate option, expecting case-insensitive option names')
        cf['zing'] = {'option1': 'value1', 'option2': 'value2'}
        self.assertEqual(cf.sections(), ['zing'])
        self.assertEqual(set(cf['zing'].keys()), {'option1', 'option2', 'foo'})
        cf.clear()
        self.assertEqual(set(cf.sections()), set())
        self.assertEqual(set(cf[self.default_section].keys()), {'foo'})

    def test_setitem(self):
        cf = self.fromstring('\n            [section1]\n            name1 {0[0]} value1\n            [section2]\n            name2 {0[0]} value2\n            [section3]\n            name3 {0[0]} value3\n        '.format(self.delimiters), defaults={'nameD': 'valueD'})
        self.assertEqual(set(cf['section1'].keys()), {'name1', 'named'})
        self.assertEqual(set(cf['section2'].keys()), {'name2', 'named'})
        self.assertEqual(set(cf['section3'].keys()), {'name3', 'named'})
        self.assertEqual(cf['section1']['name1'], 'value1')
        self.assertEqual(cf['section2']['name2'], 'value2')
        self.assertEqual(cf['section3']['name3'], 'value3')
        self.assertEqual(cf.sections(), ['section1', 'section2', 'section3'])
        cf['section2'] = {'name22': 'value22'}
        self.assertEqual(set(cf['section2'].keys()), {'name22', 'named'})
        self.assertEqual(cf['section2']['name22'], 'value22')
        self.assertNotIn('name2', cf['section2'])
        self.assertEqual(cf.sections(), ['section1', 'section2', 'section3'])
        cf['section3'] = {}
        self.assertEqual(set(cf['section3'].keys()), {'named'})
        self.assertNotIn('name3', cf['section3'])
        self.assertEqual(cf.sections(), ['section1', 'section2', 'section3'])
        cf[self.default_section] = cf[self.default_section]
        self.assertNotEqual(set(cf[self.default_section].keys()), set())
        cf[self.default_section] = {}
        self.assertEqual(set(cf[self.default_section].keys()), set())
        self.assertEqual(set(cf['section1'].keys()), {'name1'})
        self.assertEqual(set(cf['section2'].keys()), {'name22'})
        self.assertEqual(set(cf['section3'].keys()), set())
        self.assertEqual(cf.sections(), ['section1', 'section2', 'section3'])
        cf['section2'] = cf['section2']
        self.assertEqual(set(cf['section2'].keys()), {'name22'})

    def test_invalid_multiline_value(self):
        if self.allow_no_value:
            self.skipTest('if no_value is allowed, ParsingError is not raised')
        invalid = textwrap.dedent('            [DEFAULT]\n            test {0} test\n            invalid'.format(self.delimiters[0]))
        cf = self.newconfig()
        with self.assertRaises(configparser.ParsingError):
            cf.read_string(invalid)
        self.assertEqual(cf.get('DEFAULT', 'test'), 'test')
        self.assertEqual(cf['DEFAULT']['test'], 'test')

class StrictTestCase(BasicTestCase, unittest.TestCase):
    config_class = configparser.RawConfigParser
    strict = True

class ConfigParserTestCase(BasicTestCase, unittest.TestCase):
    config_class = configparser.ConfigParser

    def test_interpolation(self):
        cf = self.get_interpolation_config()
        eq = self.assertEqual
        eq(cf.get('Foo', 'bar'), 'something with interpolation (1 step)')
        eq(cf.get('Foo', 'bar9'), 'something with lots of interpolation (9 steps)')
        eq(cf.get('Foo', 'bar10'), 'something with lots of interpolation (10 steps)')
        e = self.get_error(cf, configparser.InterpolationDepthError, 'Foo', 'bar11')
        if (self.interpolation == configparser._UNSET):
            self.assertEqual(e.args, ('bar11', 'Foo', 'something %(with11)s lots of interpolation (11 steps)'))
        elif isinstance(self.interpolation, configparser.LegacyInterpolation):
            self.assertEqual(e.args, ('bar11', 'Foo', 'something %(with11)s lots of interpolation (11 steps)'))

    def test_interpolation_missing_value(self):
        cf = self.get_interpolation_config()
        e = self.get_error(cf, configparser.InterpolationMissingOptionError, 'Interpolation Error', 'name')
        self.assertEqual(e.reference, 'reference')
        self.assertEqual(e.section, 'Interpolation Error')
        self.assertEqual(e.option, 'name')
        if (self.interpolation == configparser._UNSET):
            self.assertEqual(e.args, ('name', 'Interpolation Error', '%(reference)s', 'reference'))
        elif isinstance(self.interpolation, configparser.LegacyInterpolation):
            self.assertEqual(e.args, ('name', 'Interpolation Error', '%(reference)s', 'reference'))

    def test_items(self):
        self.check_items_config([('default', '<default>'), ('getdefault', '|<default>|'), ('key', '|value|'), ('name', 'value')])

    def test_safe_interpolation(self):
        cf = self.fromstring('[section]\noption1{eq}xxx\noption2{eq}%(option1)s/xxx\nok{eq}%(option1)s/%%s\nnot_ok{eq}%(option2)s/%%s'.format(eq=self.delimiters[0]))
        self.assertEqual(cf.get('section', 'ok'), 'xxx/%s')
        if (self.interpolation == configparser._UNSET):
            self.assertEqual(cf.get('section', 'not_ok'), 'xxx/xxx/%s')
        elif isinstance(self.interpolation, configparser.LegacyInterpolation):
            with self.assertRaises(TypeError):
                cf.get('section', 'not_ok')

    def test_set_malformatted_interpolation(self):
        cf = self.fromstring('[sect]\noption1{eq}foo\n'.format(eq=self.delimiters[0]))
        self.assertEqual(cf.get('sect', 'option1'), 'foo')
        self.assertRaises(ValueError, cf.set, 'sect', 'option1', '%foo')
        self.assertRaises(ValueError, cf.set, 'sect', 'option1', 'foo%')
        self.assertRaises(ValueError, cf.set, 'sect', 'option1', 'f%oo')
        self.assertEqual(cf.get('sect', 'option1'), 'foo')
        cf.set('sect', 'option2', 'foo%%bar')
        self.assertEqual(cf.get('sect', 'option2'), 'foo%bar')

    def test_set_nonstring_types(self):
        cf = self.fromstring('[sect]\noption1{eq}foo\n'.format(eq=self.delimiters[0]))
        self.assertRaises(TypeError, cf.set, 'sect', 'option1', 1)
        self.assertRaises(TypeError, cf.set, 'sect', 'option1', 1.0)
        self.assertRaises(TypeError, cf.set, 'sect', 'option1', object())
        self.assertRaises(TypeError, cf.set, 'sect', 'option2', 1)
        self.assertRaises(TypeError, cf.set, 'sect', 'option2', 1.0)
        self.assertRaises(TypeError, cf.set, 'sect', 'option2', object())
        self.assertRaises(TypeError, cf.set, 'sect', 123, 'invalid opt name!')
        self.assertRaises(TypeError, cf.add_section, 123)

    def test_add_section_default(self):
        cf = self.newconfig()
        self.assertRaises(ValueError, cf.add_section, self.default_section)

    def test_defaults_keyword(self):
        'bpo-23835 fix for ConfigParser'
        cf = self.newconfig(defaults={1: 2.4})
        self.assertEqual(cf[self.default_section]['1'], '2.4')
        self.assertAlmostEqual(cf[self.default_section].getfloat('1'), 2.4)
        cf = self.newconfig(defaults={'A': 5.2})
        self.assertEqual(cf[self.default_section]['a'], '5.2')
        self.assertAlmostEqual(cf[self.default_section].getfloat('a'), 5.2)

class ConfigParserTestCaseNoInterpolation(BasicTestCase, unittest.TestCase):
    config_class = configparser.ConfigParser
    interpolation = None
    ini = textwrap.dedent('\n        [numbers]\n        one = 1\n        two = %(one)s * 2\n        three = ${common:one} * 3\n\n        [hexen]\n        sixteen = ${numbers:two} * 8\n    ').strip()

    def assertMatchesIni(self, cf):
        self.assertEqual(cf['numbers']['one'], '1')
        self.assertEqual(cf['numbers']['two'], '%(one)s * 2')
        self.assertEqual(cf['numbers']['three'], '${common:one} * 3')
        self.assertEqual(cf['hexen']['sixteen'], '${numbers:two} * 8')

    def test_no_interpolation(self):
        cf = self.fromstring(self.ini)
        self.assertMatchesIni(cf)

    def test_empty_case(self):
        cf = self.newconfig()
        self.assertIsNone(cf.read_string(''))

    def test_none_as_default_interpolation(self):

        class CustomConfigParser(configparser.ConfigParser):
            _DEFAULT_INTERPOLATION = None
        cf = CustomConfigParser()
        cf.read_string(self.ini)
        self.assertMatchesIni(cf)

class ConfigParserTestCaseLegacyInterpolation(ConfigParserTestCase):
    config_class = configparser.ConfigParser
    interpolation = configparser.LegacyInterpolation()

    def test_set_malformatted_interpolation(self):
        cf = self.fromstring('[sect]\noption1{eq}foo\n'.format(eq=self.delimiters[0]))
        self.assertEqual(cf.get('sect', 'option1'), 'foo')
        cf.set('sect', 'option1', '%foo')
        self.assertEqual(cf.get('sect', 'option1'), '%foo')
        cf.set('sect', 'option1', 'foo%')
        self.assertEqual(cf.get('sect', 'option1'), 'foo%')
        cf.set('sect', 'option1', 'f%oo')
        self.assertEqual(cf.get('sect', 'option1'), 'f%oo')
        cf.set('sect', 'option2', 'foo%%bar')
        self.assertEqual(cf.get('sect', 'option2'), 'foo%%bar')

class ConfigParserTestCaseNonStandardDelimiters(ConfigParserTestCase):
    delimiters = (':=', '$')
    comment_prefixes = ('//', '"')
    inline_comment_prefixes = ('//', '"')

class ConfigParserTestCaseNonStandardDefaultSection(ConfigParserTestCase):
    default_section = 'general'

class MultilineValuesTestCase(BasicTestCase, unittest.TestCase):
    config_class = configparser.ConfigParser
    wonderful_spam = "I'm having spam spam spam spam spam spam spam beaked beans spam spam spam and spam!".replace(' ', '\t\n')

    def setUp(self):
        cf = self.newconfig()
        for i in range(100):
            s = 'section{}'.format(i)
            cf.add_section(s)
            for j in range(10):
                cf.set(s, 'lovely_spam{}'.format(j), self.wonderful_spam)
        with open(os_helper.TESTFN, 'w') as f:
            cf.write(f)

    def tearDown(self):
        os.unlink(os_helper.TESTFN)

    def test_dominating_multiline_values(self):
        cf_from_file = self.newconfig()
        with open(os_helper.TESTFN) as f:
            cf_from_file.read_file(f)
        self.assertEqual(cf_from_file.get('section8', 'lovely_spam4'), self.wonderful_spam.replace('\t\n', '\n'))

class RawConfigParserTestCase(BasicTestCase, unittest.TestCase):
    config_class = configparser.RawConfigParser

    def test_interpolation(self):
        cf = self.get_interpolation_config()
        eq = self.assertEqual
        eq(cf.get('Foo', 'bar'), 'something %(with1)s interpolation (1 step)')
        eq(cf.get('Foo', 'bar9'), 'something %(with9)s lots of interpolation (9 steps)')
        eq(cf.get('Foo', 'bar10'), 'something %(with10)s lots of interpolation (10 steps)')
        eq(cf.get('Foo', 'bar11'), 'something %(with11)s lots of interpolation (11 steps)')

    def test_items(self):
        self.check_items_config([('default', '<default>'), ('getdefault', '|%(default)s|'), ('key', '|%(name)s|'), ('name', '%(value)s')])

    def test_set_nonstring_types(self):
        cf = self.newconfig()
        cf.add_section('non-string')
        cf.set('non-string', 'int', 1)
        cf.set('non-string', 'list', [0, 1, 1, 2, 3, 5, 8, 13])
        cf.set('non-string', 'dict', {'pi': 3.14159})
        self.assertEqual(cf.get('non-string', 'int'), 1)
        self.assertEqual(cf.get('non-string', 'list'), [0, 1, 1, 2, 3, 5, 8, 13])
        self.assertEqual(cf.get('non-string', 'dict'), {'pi': 3.14159})
        cf.add_section(123)
        cf.set(123, 'this is sick', True)
        self.assertEqual(cf.get(123, 'this is sick'), True)
        if (cf._dict is configparser._default_dict):
            cf.optionxform = (lambda x: x)
            cf.set('non-string', 1, 1)
            self.assertEqual(cf.get('non-string', 1), 1)

    def test_defaults_keyword(self):
        'bpo-23835 legacy behavior for RawConfigParser'
        with self.assertRaises(AttributeError) as ctx:
            self.newconfig(defaults={1: 2.4})
        err = ctx.exception
        self.assertEqual(str(err), "'int' object has no attribute 'lower'")
        cf = self.newconfig(defaults={'A': 5.2})
        self.assertAlmostEqual(cf[self.default_section]['a'], 5.2)

class RawConfigParserTestCaseNonStandardDelimiters(RawConfigParserTestCase):
    delimiters = (':=', '$')
    comment_prefixes = ('//', '"')
    inline_comment_prefixes = ('//', '"')

class RawConfigParserTestSambaConf(CfgParserTestCaseClass, unittest.TestCase):
    config_class = configparser.RawConfigParser
    comment_prefixes = ('#', ';', '----')
    inline_comment_prefixes = ('//',)
    empty_lines_in_values = False

    def test_reading(self):
        smbconf = support.findfile('cfgparser.2')
        cf = self.newconfig()
        parsed_files = cf.read([smbconf, 'nonexistent-file'], encoding='utf-8')
        self.assertEqual(parsed_files, [smbconf])
        sections = ['global', 'homes', 'printers', 'print$', 'pdf-generator', 'tmp', 'Agustin']
        self.assertEqual(cf.sections(), sections)
        self.assertEqual(cf.get('global', 'workgroup'), 'MDKGROUP')
        self.assertEqual(cf.getint('global', 'max log size'), 50)
        self.assertEqual(cf.get('global', 'hosts allow'), '127.')
        self.assertEqual(cf.get('tmp', 'echo command'), 'cat %s; rm %s')

class ConfigParserTestCaseExtendedInterpolation(BasicTestCase, unittest.TestCase):
    config_class = configparser.ConfigParser
    interpolation = configparser.ExtendedInterpolation()
    default_section = 'common'
    strict = True

    def fromstring(self, string, defaults=None, optionxform=None):
        cf = self.newconfig(defaults)
        if optionxform:
            cf.optionxform = optionxform
        cf.read_string(string)
        return cf

    def test_extended_interpolation(self):
        cf = self.fromstring(textwrap.dedent('\n            [common]\n            favourite Beatle = Paul\n            favourite color = green\n\n            [tom]\n            favourite band = ${favourite color} day\n            favourite pope = John ${favourite Beatle} II\n            sequel = ${favourite pope}I\n\n            [ambv]\n            favourite Beatle = George\n            son of Edward VII = ${favourite Beatle} V\n            son of George V = ${son of Edward VII}I\n\n            [stanley]\n            favourite Beatle = ${ambv:favourite Beatle}\n            favourite pope = ${tom:favourite pope}\n            favourite color = black\n            favourite state of mind = paranoid\n            favourite movie = soylent ${common:favourite color}\n            favourite song = ${favourite color} sabbath - ${favourite state of mind}\n        ').strip())
        eq = self.assertEqual
        eq(cf['common']['favourite Beatle'], 'Paul')
        eq(cf['common']['favourite color'], 'green')
        eq(cf['tom']['favourite Beatle'], 'Paul')
        eq(cf['tom']['favourite color'], 'green')
        eq(cf['tom']['favourite band'], 'green day')
        eq(cf['tom']['favourite pope'], 'John Paul II')
        eq(cf['tom']['sequel'], 'John Paul III')
        eq(cf['ambv']['favourite Beatle'], 'George')
        eq(cf['ambv']['favourite color'], 'green')
        eq(cf['ambv']['son of Edward VII'], 'George V')
        eq(cf['ambv']['son of George V'], 'George VI')
        eq(cf['stanley']['favourite Beatle'], 'George')
        eq(cf['stanley']['favourite color'], 'black')
        eq(cf['stanley']['favourite state of mind'], 'paranoid')
        eq(cf['stanley']['favourite movie'], 'soylent green')
        eq(cf['stanley']['favourite pope'], 'John Paul II')
        eq(cf['stanley']['favourite song'], 'black sabbath - paranoid')

    def test_endless_loop(self):
        cf = self.fromstring(textwrap.dedent('\n            [one for you]\n            ping = ${one for me:pong}\n\n            [one for me]\n            pong = ${one for you:ping}\n\n            [selfish]\n            me = ${me}\n        ').strip())
        with self.assertRaises(configparser.InterpolationDepthError):
            cf['one for you']['ping']
        with self.assertRaises(configparser.InterpolationDepthError):
            cf['selfish']['me']

    def test_strange_options(self):
        cf = self.fromstring('\n            [dollars]\n            $var = $$value\n            $var2 = ${$var}\n            ${sick} = cannot interpolate me\n\n            [interpolated]\n            $other = ${dollars:$var}\n            $trying = ${dollars:${sick}}\n        ')
        self.assertEqual(cf['dollars']['$var'], '$value')
        self.assertEqual(cf['interpolated']['$other'], '$value')
        self.assertEqual(cf['dollars']['${sick}'], 'cannot interpolate me')
        exception_class = configparser.InterpolationMissingOptionError
        with self.assertRaises(exception_class) as cm:
            cf['interpolated']['$trying']
        self.assertEqual(cm.exception.reference, 'dollars:${sick')
        self.assertEqual(cm.exception.args[2], '${dollars:${sick}}')

    def test_case_sensitivity_basic(self):
        ini = textwrap.dedent('\n            [common]\n            optionlower = value\n            OptionUpper = Value\n\n            [Common]\n            optionlower = a better ${common:optionlower}\n            OptionUpper = A Better ${common:OptionUpper}\n\n            [random]\n            foolower = ${common:optionlower} redefined\n            FooUpper = ${Common:OptionUpper} Redefined\n        ').strip()
        cf = self.fromstring(ini)
        eq = self.assertEqual
        eq(cf['common']['optionlower'], 'value')
        eq(cf['common']['OptionUpper'], 'Value')
        eq(cf['Common']['optionlower'], 'a better value')
        eq(cf['Common']['OptionUpper'], 'A Better Value')
        eq(cf['random']['foolower'], 'value redefined')
        eq(cf['random']['FooUpper'], 'A Better Value Redefined')

    def test_case_sensitivity_conflicts(self):
        ini = textwrap.dedent('\n            [common]\n            option = value\n            Option = Value\n\n            [Common]\n            option = a better ${common:option}\n            Option = A Better ${common:Option}\n\n            [random]\n            foo = ${common:option} redefined\n            Foo = ${Common:Option} Redefined\n        ').strip()
        with self.assertRaises(configparser.DuplicateOptionError):
            cf = self.fromstring(ini)
        cf = self.fromstring(ini, optionxform=(lambda opt: opt))
        eq = self.assertEqual
        eq(cf['common']['option'], 'value')
        eq(cf['common']['Option'], 'Value')
        eq(cf['Common']['option'], 'a better value')
        eq(cf['Common']['Option'], 'A Better Value')
        eq(cf['random']['foo'], 'value redefined')
        eq(cf['random']['Foo'], 'A Better Value Redefined')

    def test_other_errors(self):
        cf = self.fromstring("\n            [interpolation fail]\n            case1 = ${where's the brace\n            case2 = ${does_not_exist}\n            case3 = ${wrong_section:wrong_value}\n            case4 = ${i:like:colon:characters}\n            case5 = $100 for Fail No 5!\n        ")
        with self.assertRaises(configparser.InterpolationSyntaxError):
            cf['interpolation fail']['case1']
        with self.assertRaises(configparser.InterpolationMissingOptionError):
            cf['interpolation fail']['case2']
        with self.assertRaises(configparser.InterpolationMissingOptionError):
            cf['interpolation fail']['case3']
        with self.assertRaises(configparser.InterpolationSyntaxError):
            cf['interpolation fail']['case4']
        with self.assertRaises(configparser.InterpolationSyntaxError):
            cf['interpolation fail']['case5']
        with self.assertRaises(ValueError):
            cf['interpolation fail']['case6'] = 'BLACK $ABBATH'

class ConfigParserTestCaseNoValue(ConfigParserTestCase):
    allow_no_value = True

class ConfigParserTestCaseTrickyFile(CfgParserTestCaseClass, unittest.TestCase):
    config_class = configparser.ConfigParser
    delimiters = {'='}
    comment_prefixes = {'#'}
    allow_no_value = True

    def test_cfgparser_dot_3(self):
        tricky = support.findfile('cfgparser.3')
        cf = self.newconfig()
        self.assertEqual(len(cf.read(tricky, encoding='utf-8')), 1)
        self.assertEqual(cf.sections(), ['strange', 'corruption', 'yeah, sections can be indented as well', 'another one!', 'no values here', 'tricky interpolation', 'more interpolation'])
        self.assertEqual(cf.getint(self.default_section, 'go', vars={'interpolate': '-1'}), (- 1))
        with self.assertRaises(ValueError):
            cf.getint(self.default_section, 'go', raw=True, vars={'interpolate': '-1'})
        self.assertEqual(len(cf.get('strange', 'other').split('\n')), 4)
        self.assertEqual(len(cf.get('corruption', 'value').split('\n')), 10)
        longname = 'yeah, sections can be indented as well'
        self.assertFalse(cf.getboolean(longname, 'are they subsections'))
        self.assertEqual(cf.get(longname, 'lets use some Unicode'), '片仮名')
        self.assertEqual(len(cf.items('another one!')), 5)
        with self.assertRaises(configparser.InterpolationMissingOptionError):
            cf.items('no values here')
        self.assertEqual(cf.get('tricky interpolation', 'lets'), 'do this')
        self.assertEqual(cf.get('tricky interpolation', 'lets'), cf.get('tricky interpolation', 'go'))
        self.assertEqual(cf.get('more interpolation', 'lets'), 'go shopping')

    def test_unicode_failure(self):
        tricky = support.findfile('cfgparser.3')
        cf = self.newconfig()
        with self.assertRaises(UnicodeDecodeError):
            cf.read(tricky, encoding='ascii')

class Issue7005TestCase(unittest.TestCase):
    'Test output when None is set() as a value and allow_no_value == False.\n\n    http://bugs.python.org/issue7005\n\n    '
    expected_output = '[section]\noption = None\n\n'

    def prepare(self, config_class):
        cp = config_class(allow_no_value=False)
        cp.add_section('section')
        cp.set('section', 'option', None)
        sio = io.StringIO()
        cp.write(sio)
        return sio.getvalue()

    def test_none_as_value_stringified(self):
        cp = configparser.ConfigParser(allow_no_value=False)
        cp.add_section('section')
        with self.assertRaises(TypeError):
            cp.set('section', 'option', None)

    def test_none_as_value_stringified_raw(self):
        output = self.prepare(configparser.RawConfigParser)
        self.assertEqual(output, self.expected_output)

class SortedTestCase(RawConfigParserTestCase):
    dict_type = SortedDict

    def test_sorted(self):
        cf = self.fromstring('[b]\no4=1\no3=2\no2=3\no1=4\n[a]\nk=v\n')
        output = io.StringIO()
        cf.write(output)
        self.assertEqual(output.getvalue(), '[a]\nk = v\n\n[b]\no1 = 4\no2 = 3\no3 = 2\no4 = 1\n\n')

class CompatibleTestCase(CfgParserTestCaseClass, unittest.TestCase):
    config_class = configparser.RawConfigParser
    comment_prefixes = '#;'
    inline_comment_prefixes = ';'

    def test_comment_handling(self):
        config_string = textwrap.dedent('        [Commented Bar]\n        baz=qwe ; a comment\n        foo: bar # not a comment!\n        # but this is a comment\n        ; another comment\n        quirk: this;is not a comment\n        ; a space must precede an inline comment\n        ')
        cf = self.fromstring(config_string)
        self.assertEqual(cf.get('Commented Bar', 'foo'), 'bar # not a comment!')
        self.assertEqual(cf.get('Commented Bar', 'baz'), 'qwe')
        self.assertEqual(cf.get('Commented Bar', 'quirk'), 'this;is not a comment')

class CopyTestCase(BasicTestCase, unittest.TestCase):
    config_class = configparser.ConfigParser

    def fromstring(self, string, defaults=None):
        cf = self.newconfig(defaults)
        cf.read_string(string)
        cf_copy = self.newconfig()
        cf_copy.read_dict(cf)
        for section in cf_copy.values():
            if (section.name == self.default_section):
                continue
            for (default, value) in cf[self.default_section].items():
                if (section[default] == value):
                    del section[default]
        return cf_copy

class FakeFile():

    def __init__(self):
        file_path = support.findfile('cfgparser.1')
        with open(file_path) as f:
            self.lines = f.readlines()
            self.lines.reverse()

    def readline(self):
        if len(self.lines):
            return self.lines.pop()
        return ''

def readline_generator(f):
    'As advised in Doc/library/configparser.rst.'
    line = f.readline()
    while line:
        (yield line)
        line = f.readline()

class ReadFileTestCase(unittest.TestCase):

    def test_file(self):
        file_paths = [support.findfile('cfgparser.1')]
        try:
            file_paths.append(file_paths[0].encode('utf8'))
        except UnicodeEncodeError:
            pass
        for file_path in file_paths:
            parser = configparser.ConfigParser()
            with open(file_path) as f:
                parser.read_file(f)
            self.assertIn('Foo Bar', parser)
            self.assertIn('foo', parser['Foo Bar'])
            self.assertEqual(parser['Foo Bar']['foo'], 'newbar')

    def test_iterable(self):
        lines = textwrap.dedent('\n        [Foo Bar]\n        foo=newbar').strip().split('\n')
        parser = configparser.ConfigParser()
        parser.read_file(lines)
        self.assertIn('Foo Bar', parser)
        self.assertIn('foo', parser['Foo Bar'])
        self.assertEqual(parser['Foo Bar']['foo'], 'newbar')

    def test_readline_generator(self):
        'Issue #11670.'
        parser = configparser.ConfigParser()
        with self.assertRaises(TypeError):
            parser.read_file(FakeFile())
        parser.read_file(readline_generator(FakeFile()))
        self.assertIn('Foo Bar', parser)
        self.assertIn('foo', parser['Foo Bar'])
        self.assertEqual(parser['Foo Bar']['foo'], 'newbar')

    def test_source_as_bytes(self):
        'Issue #18260.'
        lines = textwrap.dedent('\n        [badbad]\n        [badbad]').strip().split('\n')
        parser = configparser.ConfigParser()
        with self.assertRaises(configparser.DuplicateSectionError) as dse:
            parser.read_file(lines, source=b'badbad')
        self.assertEqual(str(dse.exception), "While reading from b'badbad' [line  2]: section 'badbad' already exists")
        lines = textwrap.dedent('\n        [badbad]\n        bad = bad\n        bad = bad').strip().split('\n')
        parser = configparser.ConfigParser()
        with self.assertRaises(configparser.DuplicateOptionError) as dse:
            parser.read_file(lines, source=b'badbad')
        self.assertEqual(str(dse.exception), "While reading from b'badbad' [line  3]: option 'bad' in section 'badbad' already exists")
        lines = textwrap.dedent('\n        [badbad]\n        = bad').strip().split('\n')
        parser = configparser.ConfigParser()
        with self.assertRaises(configparser.ParsingError) as dse:
            parser.read_file(lines, source=b'badbad')
        self.assertEqual(str(dse.exception), "Source contains parsing errors: b'badbad'\n\t[line  2]: '= bad'")
        lines = textwrap.dedent('\n        [badbad\n        bad = bad').strip().split('\n')
        parser = configparser.ConfigParser()
        with self.assertRaises(configparser.MissingSectionHeaderError) as dse:
            parser.read_file(lines, source=b'badbad')
        self.assertEqual(str(dse.exception), "File contains no section headers.\nfile: b'badbad', line: 1\n'[badbad'")

class CoverageOneHundredTestCase(unittest.TestCase):
    'Covers edge cases in the codebase.'

    def test_duplicate_option_error(self):
        error = configparser.DuplicateOptionError('section', 'option')
        self.assertEqual(error.section, 'section')
        self.assertEqual(error.option, 'option')
        self.assertEqual(error.source, None)
        self.assertEqual(error.lineno, None)
        self.assertEqual(error.args, ('section', 'option', None, None))
        self.assertEqual(str(error), "Option 'option' in section 'section' already exists")

    def test_interpolation_depth_error(self):
        error = configparser.InterpolationDepthError('option', 'section', 'rawval')
        self.assertEqual(error.args, ('option', 'section', 'rawval'))
        self.assertEqual(error.option, 'option')
        self.assertEqual(error.section, 'section')

    def test_parsing_error(self):
        with self.assertRaises(ValueError) as cm:
            configparser.ParsingError()
        self.assertEqual(str(cm.exception), "Required argument `source' not given.")
        with self.assertRaises(ValueError) as cm:
            configparser.ParsingError(source='source', filename='filename')
        self.assertEqual(str(cm.exception), "Cannot specify both `filename' and `source'. Use `source'.")
        error = configparser.ParsingError(filename='source')
        self.assertEqual(error.source, 'source')
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always', DeprecationWarning)
            self.assertEqual(error.filename, 'source')
            error.filename = 'filename'
            self.assertEqual(error.source, 'filename')
        for warning in w:
            self.assertTrue((warning.category is DeprecationWarning))

    def test_interpolation_validation(self):
        parser = configparser.ConfigParser()
        parser.read_string('\n            [section]\n            invalid_percent = %\n            invalid_reference = %(()\n            invalid_variable = %(does_not_exist)s\n        ')
        with self.assertRaises(configparser.InterpolationSyntaxError) as cm:
            parser['section']['invalid_percent']
        self.assertEqual(str(cm.exception), "'%' must be followed by '%' or '(', found: '%'")
        with self.assertRaises(configparser.InterpolationSyntaxError) as cm:
            parser['section']['invalid_reference']
        self.assertEqual(str(cm.exception), "bad interpolation variable reference '%(()'")

    def test_readfp_deprecation(self):
        sio = io.StringIO('\n        [section]\n        option = value\n        ')
        parser = configparser.ConfigParser()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always', DeprecationWarning)
            parser.readfp(sio, filename='StringIO')
        for warning in w:
            self.assertTrue((warning.category is DeprecationWarning))
        self.assertEqual(len(parser), 2)
        self.assertEqual(parser['section']['option'], 'value')

    def test_safeconfigparser_deprecation(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always', DeprecationWarning)
            parser = configparser.SafeConfigParser()
        for warning in w:
            self.assertTrue((warning.category is DeprecationWarning))

    def test_sectionproxy_repr(self):
        parser = configparser.ConfigParser()
        parser.read_string('\n            [section]\n            key = value\n        ')
        self.assertEqual(repr(parser['section']), '<Section: section>')

    def test_inconsistent_converters_state(self):
        parser = configparser.ConfigParser()
        import decimal
        parser.converters['decimal'] = decimal.Decimal
        parser.read_string('\n            [s1]\n            one = 1\n            [s2]\n            two = 2\n        ')
        self.assertIn('decimal', parser.converters)
        self.assertEqual(parser.getdecimal('s1', 'one'), 1)
        self.assertEqual(parser.getdecimal('s2', 'two'), 2)
        self.assertEqual(parser['s1'].getdecimal('one'), 1)
        self.assertEqual(parser['s2'].getdecimal('two'), 2)
        del parser.getdecimal
        with self.assertRaises(AttributeError):
            parser.getdecimal('s1', 'one')
        self.assertIn('decimal', parser.converters)
        del parser.converters['decimal']
        self.assertNotIn('decimal', parser.converters)
        with self.assertRaises(AttributeError):
            parser.getdecimal('s1', 'one')
        with self.assertRaises(AttributeError):
            parser['s1'].getdecimal('one')
        with self.assertRaises(AttributeError):
            parser['s2'].getdecimal('two')

class ExceptionPicklingTestCase(unittest.TestCase):
    'Tests for issue #13760: ConfigParser exceptions are not picklable.'

    def test_error(self):
        import pickle
        e1 = configparser.Error('value')
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            pickled = pickle.dumps(e1, proto)
            e2 = pickle.loads(pickled)
            self.assertEqual(e1.message, e2.message)
            self.assertEqual(repr(e1), repr(e2))

    def test_nosectionerror(self):
        import pickle
        e1 = configparser.NoSectionError('section')
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            pickled = pickle.dumps(e1, proto)
            e2 = pickle.loads(pickled)
            self.assertEqual(e1.message, e2.message)
            self.assertEqual(e1.args, e2.args)
            self.assertEqual(e1.section, e2.section)
            self.assertEqual(repr(e1), repr(e2))

    def test_nooptionerror(self):
        import pickle
        e1 = configparser.NoOptionError('option', 'section')
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            pickled = pickle.dumps(e1, proto)
            e2 = pickle.loads(pickled)
            self.assertEqual(e1.message, e2.message)
            self.assertEqual(e1.args, e2.args)
            self.assertEqual(e1.section, e2.section)
            self.assertEqual(e1.option, e2.option)
            self.assertEqual(repr(e1), repr(e2))

    def test_duplicatesectionerror(self):
        import pickle
        e1 = configparser.DuplicateSectionError('section', 'source', 123)
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            pickled = pickle.dumps(e1, proto)
            e2 = pickle.loads(pickled)
            self.assertEqual(e1.message, e2.message)
            self.assertEqual(e1.args, e2.args)
            self.assertEqual(e1.section, e2.section)
            self.assertEqual(e1.source, e2.source)
            self.assertEqual(e1.lineno, e2.lineno)
            self.assertEqual(repr(e1), repr(e2))

    def test_duplicateoptionerror(self):
        import pickle
        e1 = configparser.DuplicateOptionError('section', 'option', 'source', 123)
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            pickled = pickle.dumps(e1, proto)
            e2 = pickle.loads(pickled)
            self.assertEqual(e1.message, e2.message)
            self.assertEqual(e1.args, e2.args)
            self.assertEqual(e1.section, e2.section)
            self.assertEqual(e1.option, e2.option)
            self.assertEqual(e1.source, e2.source)
            self.assertEqual(e1.lineno, e2.lineno)
            self.assertEqual(repr(e1), repr(e2))

    def test_interpolationerror(self):
        import pickle
        e1 = configparser.InterpolationError('option', 'section', 'msg')
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            pickled = pickle.dumps(e1, proto)
            e2 = pickle.loads(pickled)
            self.assertEqual(e1.message, e2.message)
            self.assertEqual(e1.args, e2.args)
            self.assertEqual(e1.section, e2.section)
            self.assertEqual(e1.option, e2.option)
            self.assertEqual(repr(e1), repr(e2))

    def test_interpolationmissingoptionerror(self):
        import pickle
        e1 = configparser.InterpolationMissingOptionError('option', 'section', 'rawval', 'reference')
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            pickled = pickle.dumps(e1, proto)
            e2 = pickle.loads(pickled)
            self.assertEqual(e1.message, e2.message)
            self.assertEqual(e1.args, e2.args)
            self.assertEqual(e1.section, e2.section)
            self.assertEqual(e1.option, e2.option)
            self.assertEqual(e1.reference, e2.reference)
            self.assertEqual(repr(e1), repr(e2))

    def test_interpolationsyntaxerror(self):
        import pickle
        e1 = configparser.InterpolationSyntaxError('option', 'section', 'msg')
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            pickled = pickle.dumps(e1, proto)
            e2 = pickle.loads(pickled)
            self.assertEqual(e1.message, e2.message)
            self.assertEqual(e1.args, e2.args)
            self.assertEqual(e1.section, e2.section)
            self.assertEqual(e1.option, e2.option)
            self.assertEqual(repr(e1), repr(e2))

    def test_interpolationdeptherror(self):
        import pickle
        e1 = configparser.InterpolationDepthError('option', 'section', 'rawval')
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            pickled = pickle.dumps(e1, proto)
            e2 = pickle.loads(pickled)
            self.assertEqual(e1.message, e2.message)
            self.assertEqual(e1.args, e2.args)
            self.assertEqual(e1.section, e2.section)
            self.assertEqual(e1.option, e2.option)
            self.assertEqual(repr(e1), repr(e2))

    def test_parsingerror(self):
        import pickle
        e1 = configparser.ParsingError('source')
        e1.append(1, 'line1')
        e1.append(2, 'line2')
        e1.append(3, 'line3')
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            pickled = pickle.dumps(e1, proto)
            e2 = pickle.loads(pickled)
            self.assertEqual(e1.message, e2.message)
            self.assertEqual(e1.args, e2.args)
            self.assertEqual(e1.source, e2.source)
            self.assertEqual(e1.errors, e2.errors)
            self.assertEqual(repr(e1), repr(e2))
        e1 = configparser.ParsingError(filename='filename')
        e1.append(1, 'line1')
        e1.append(2, 'line2')
        e1.append(3, 'line3')
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            pickled = pickle.dumps(e1, proto)
            e2 = pickle.loads(pickled)
            self.assertEqual(e1.message, e2.message)
            self.assertEqual(e1.args, e2.args)
            self.assertEqual(e1.source, e2.source)
            self.assertEqual(e1.errors, e2.errors)
            self.assertEqual(repr(e1), repr(e2))

    def test_missingsectionheadererror(self):
        import pickle
        e1 = configparser.MissingSectionHeaderError('filename', 123, 'line')
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            pickled = pickle.dumps(e1, proto)
            e2 = pickle.loads(pickled)
            self.assertEqual(e1.message, e2.message)
            self.assertEqual(e1.args, e2.args)
            self.assertEqual(e1.line, e2.line)
            self.assertEqual(e1.source, e2.source)
            self.assertEqual(e1.lineno, e2.lineno)
            self.assertEqual(repr(e1), repr(e2))

class InlineCommentStrippingTestCase(unittest.TestCase):
    "Tests for issue #14590: ConfigParser doesn't strip inline comment when\n    delimiter occurs earlier without preceding space.."

    def test_stripping(self):
        cfg = configparser.ConfigParser(inline_comment_prefixes=(';', '#', '//'))
        cfg.read_string('\n        [section]\n        k1 = v1;still v1\n        k2 = v2 ;a comment\n        k3 = v3 ; also a comment\n        k4 = v4;still v4 ;a comment\n        k5 = v5;still v5 ; also a comment\n        k6 = v6;still v6; and still v6 ;a comment\n        k7 = v7;still v7; and still v7 ; also a comment\n\n        [multiprefix]\n        k1 = v1;still v1 #a comment ; yeah, pretty much\n        k2 = v2 // this already is a comment ; continued\n        k3 = v3;#//still v3# and still v3 ; a comment\n        ')
        s = cfg['section']
        self.assertEqual(s['k1'], 'v1;still v1')
        self.assertEqual(s['k2'], 'v2')
        self.assertEqual(s['k3'], 'v3')
        self.assertEqual(s['k4'], 'v4;still v4')
        self.assertEqual(s['k5'], 'v5;still v5')
        self.assertEqual(s['k6'], 'v6;still v6; and still v6')
        self.assertEqual(s['k7'], 'v7;still v7; and still v7')
        s = cfg['multiprefix']
        self.assertEqual(s['k1'], 'v1;still v1')
        self.assertEqual(s['k2'], 'v2')
        self.assertEqual(s['k3'], 'v3;#//still v3# and still v3')

class ExceptionContextTestCase(unittest.TestCase):
    " Test that implementation details doesn't leak\n    through raising exceptions. "

    def test_get_basic_interpolation(self):
        parser = configparser.ConfigParser()
        parser.read_string('\n        [Paths]\n        home_dir: /Users\n        my_dir: %(home_dir1)s/lumberjack\n        my_pictures: %(my_dir)s/Pictures\n        ')
        cm = self.assertRaises(configparser.InterpolationMissingOptionError)
        with cm:
            parser.get('Paths', 'my_dir')
        self.assertIs(cm.exception.__suppress_context__, True)

    def test_get_extended_interpolation(self):
        parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        parser.read_string('\n        [Paths]\n        home_dir: /Users\n        my_dir: ${home_dir1}/lumberjack\n        my_pictures: ${my_dir}/Pictures\n        ')
        cm = self.assertRaises(configparser.InterpolationMissingOptionError)
        with cm:
            parser.get('Paths', 'my_dir')
        self.assertIs(cm.exception.__suppress_context__, True)

    def test_missing_options(self):
        parser = configparser.ConfigParser()
        parser.read_string('\n        [Paths]\n        home_dir: /Users\n        ')
        with self.assertRaises(configparser.NoSectionError) as cm:
            parser.options('test')
        self.assertIs(cm.exception.__suppress_context__, True)

    def test_missing_section(self):
        config = configparser.ConfigParser()
        with self.assertRaises(configparser.NoSectionError) as cm:
            config.set('Section1', 'an_int', '15')
        self.assertIs(cm.exception.__suppress_context__, True)

    def test_remove_option(self):
        config = configparser.ConfigParser()
        with self.assertRaises(configparser.NoSectionError) as cm:
            config.remove_option('Section1', 'an_int')
        self.assertIs(cm.exception.__suppress_context__, True)

class ConvertersTestCase(BasicTestCase, unittest.TestCase):
    'Introduced in 3.5, issue #18159.'
    config_class = configparser.ConfigParser

    def newconfig(self, defaults=None):
        instance = super().newconfig(defaults=defaults)
        instance.converters['list'] = (lambda v: [e.strip() for e in v.split() if e.strip()])
        return instance

    def test_converters(self):
        cfg = self.newconfig()
        self.assertIn('boolean', cfg.converters)
        self.assertIn('list', cfg.converters)
        self.assertIsNone(cfg.converters['int'])
        self.assertIsNone(cfg.converters['float'])
        self.assertIsNone(cfg.converters['boolean'])
        self.assertIsNotNone(cfg.converters['list'])
        self.assertEqual(len(cfg.converters), 4)
        with self.assertRaises(ValueError):
            cfg.converters[''] = (lambda v: v)
        with self.assertRaises(ValueError):
            cfg.converters[None] = (lambda v: v)
        cfg.read_string('\n        [s]\n        str = string\n        int = 1\n        float = 0.5\n        list = a b c d e f g\n        bool = yes\n        ')
        s = cfg['s']
        self.assertEqual(s['str'], 'string')
        self.assertEqual(s['int'], '1')
        self.assertEqual(s['float'], '0.5')
        self.assertEqual(s['list'], 'a b c d e f g')
        self.assertEqual(s['bool'], 'yes')
        self.assertEqual(cfg.get('s', 'str'), 'string')
        self.assertEqual(cfg.get('s', 'int'), '1')
        self.assertEqual(cfg.get('s', 'float'), '0.5')
        self.assertEqual(cfg.get('s', 'list'), 'a b c d e f g')
        self.assertEqual(cfg.get('s', 'bool'), 'yes')
        self.assertEqual(cfg.get('s', 'str'), 'string')
        self.assertEqual(cfg.getint('s', 'int'), 1)
        self.assertEqual(cfg.getfloat('s', 'float'), 0.5)
        self.assertEqual(cfg.getlist('s', 'list'), ['a', 'b', 'c', 'd', 'e', 'f', 'g'])
        self.assertEqual(cfg.getboolean('s', 'bool'), True)
        self.assertEqual(s.get('str'), 'string')
        self.assertEqual(s.getint('int'), 1)
        self.assertEqual(s.getfloat('float'), 0.5)
        self.assertEqual(s.getlist('list'), ['a', 'b', 'c', 'd', 'e', 'f', 'g'])
        self.assertEqual(s.getboolean('bool'), True)
        with self.assertRaises(AttributeError):
            cfg.getdecimal('s', 'float')
        with self.assertRaises(AttributeError):
            s.getdecimal('float')
        import decimal
        cfg.converters['decimal'] = decimal.Decimal
        self.assertIn('decimal', cfg.converters)
        self.assertIsNotNone(cfg.converters['decimal'])
        self.assertEqual(len(cfg.converters), 5)
        dec0_5 = decimal.Decimal('0.5')
        self.assertEqual(cfg.getdecimal('s', 'float'), dec0_5)
        self.assertEqual(s.getdecimal('float'), dec0_5)
        del cfg.converters['decimal']
        self.assertNotIn('decimal', cfg.converters)
        self.assertEqual(len(cfg.converters), 4)
        with self.assertRaises(AttributeError):
            cfg.getdecimal('s', 'float')
        with self.assertRaises(AttributeError):
            s.getdecimal('float')
        with self.assertRaises(KeyError):
            del cfg.converters['decimal']
        with self.assertRaises(KeyError):
            del cfg.converters['']
        with self.assertRaises(KeyError):
            del cfg.converters[None]

class BlatantOverrideConvertersTestCase(unittest.TestCase):
    'What if somebody overrode a getboolean()? We want to make sure that in\n    this case the automatic converters do not kick in.'
    config = '\n        [one]\n        one = false\n        two = false\n        three = long story short\n\n        [two]\n        one = false\n        two = false\n        three = four\n    '

    def test_converters_at_init(self):
        cfg = configparser.ConfigParser(converters={'len': len})
        cfg.read_string(self.config)
        self._test_len(cfg)
        self.assertIsNotNone(cfg.converters['len'])

    def test_inheritance(self):

        class StrangeConfigParser(configparser.ConfigParser):
            gettysburg = 'a historic borough in south central Pennsylvania'

            def getboolean(self, section, option, *, raw=False, vars=None, fallback=configparser._UNSET):
                if (section == option):
                    return True
                return super().getboolean(section, option, raw=raw, vars=vars, fallback=fallback)

            def getlen(self, section, option, *, raw=False, vars=None, fallback=configparser._UNSET):
                return self._get_conv(section, option, len, raw=raw, vars=vars, fallback=fallback)
        cfg = StrangeConfigParser()
        cfg.read_string(self.config)
        self._test_len(cfg)
        self.assertIsNone(cfg.converters['len'])
        self.assertTrue(cfg.getboolean('one', 'one'))
        self.assertTrue(cfg.getboolean('two', 'two'))
        self.assertFalse(cfg.getboolean('one', 'two'))
        self.assertFalse(cfg.getboolean('two', 'one'))
        cfg.converters['boolean'] = cfg._convert_to_boolean
        self.assertFalse(cfg.getboolean('one', 'one'))
        self.assertFalse(cfg.getboolean('two', 'two'))
        self.assertFalse(cfg.getboolean('one', 'two'))
        self.assertFalse(cfg.getboolean('two', 'one'))

    def _test_len(self, cfg):
        self.assertEqual(len(cfg.converters), 4)
        self.assertIn('boolean', cfg.converters)
        self.assertIn('len', cfg.converters)
        self.assertNotIn('tysburg', cfg.converters)
        self.assertIsNone(cfg.converters['int'])
        self.assertIsNone(cfg.converters['float'])
        self.assertIsNone(cfg.converters['boolean'])
        self.assertEqual(cfg.getlen('one', 'one'), 5)
        self.assertEqual(cfg.getlen('one', 'two'), 5)
        self.assertEqual(cfg.getlen('one', 'three'), 16)
        self.assertEqual(cfg.getlen('two', 'one'), 5)
        self.assertEqual(cfg.getlen('two', 'two'), 5)
        self.assertEqual(cfg.getlen('two', 'three'), 4)
        self.assertEqual(cfg.getlen('two', 'four', fallback=0), 0)
        with self.assertRaises(configparser.NoOptionError):
            cfg.getlen('two', 'four')
        self.assertEqual(cfg['one'].getlen('one'), 5)
        self.assertEqual(cfg['one'].getlen('two'), 5)
        self.assertEqual(cfg['one'].getlen('three'), 16)
        self.assertEqual(cfg['two'].getlen('one'), 5)
        self.assertEqual(cfg['two'].getlen('two'), 5)
        self.assertEqual(cfg['two'].getlen('three'), 4)
        self.assertEqual(cfg['two'].getlen('four', 0), 0)
        self.assertEqual(cfg['two'].getlen('four'), None)

    def test_instance_assignment(self):
        cfg = configparser.ConfigParser()
        cfg.getboolean = (lambda section, option: True)
        cfg.getlen = (lambda section, option: len(cfg[section][option]))
        cfg.read_string(self.config)
        self.assertEqual(len(cfg.converters), 3)
        self.assertIn('boolean', cfg.converters)
        self.assertNotIn('len', cfg.converters)
        self.assertIsNone(cfg.converters['int'])
        self.assertIsNone(cfg.converters['float'])
        self.assertIsNone(cfg.converters['boolean'])
        self.assertTrue(cfg.getboolean('one', 'one'))
        self.assertTrue(cfg.getboolean('two', 'two'))
        self.assertTrue(cfg.getboolean('one', 'two'))
        self.assertTrue(cfg.getboolean('two', 'one'))
        cfg.converters['boolean'] = cfg._convert_to_boolean
        self.assertFalse(cfg.getboolean('one', 'one'))
        self.assertFalse(cfg.getboolean('two', 'two'))
        self.assertFalse(cfg.getboolean('one', 'two'))
        self.assertFalse(cfg.getboolean('two', 'one'))
        self.assertEqual(cfg.getlen('one', 'one'), 5)
        self.assertEqual(cfg.getlen('one', 'two'), 5)
        self.assertEqual(cfg.getlen('one', 'three'), 16)
        self.assertEqual(cfg.getlen('two', 'one'), 5)
        self.assertEqual(cfg.getlen('two', 'two'), 5)
        self.assertEqual(cfg.getlen('two', 'three'), 4)
        with self.assertRaises(AttributeError):
            self.assertEqual(cfg['one'].getlen('one'), 5)
        with self.assertRaises(AttributeError):
            self.assertEqual(cfg['two'].getlen('one'), 5)

class MiscTestCase(unittest.TestCase):

    def test__all__(self):
        support.check__all__(self, configparser, not_exported={'Error'})
if (__name__ == '__main__'):
    unittest.main()
