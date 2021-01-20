
import io
import textwrap
import unittest
from email import message_from_string, message_from_bytes
from email.message import EmailMessage
from email.generator import Generator, BytesGenerator
from email.headerregistry import Address
from email import policy
from test.test_email import TestEmailBase, parameterize

@parameterize
class TestGeneratorBase():
    policy = policy.default

    def msgmaker(self, msg, policy=None):
        policy = (self.policy if (policy is None) else policy)
        return self.msgfunc(msg, policy=policy)
    refold_long_expected = {0: textwrap.dedent('            To: whom_it_may_concern@example.com\n            From: nobody_you_want_to_know@example.com\n            Subject: We the willing led by the unknowing are doing the\n             impossible for the ungrateful. We have done so much for so long with so little\n             we are now qualified to do anything with nothing.\n\n            None\n            '), 40: textwrap.dedent('            To: whom_it_may_concern@example.com\n            From:\n             nobody_you_want_to_know@example.com\n            Subject: We the willing led by the\n             unknowing are doing the impossible for\n             the ungrateful. We have done so much\n             for so long with so little we are now\n             qualified to do anything with nothing.\n\n            None\n            '), 20: textwrap.dedent('            To:\n             whom_it_may_concern@example.com\n            From:\n             nobody_you_want_to_know@example.com\n            Subject: We the\n             willing led by the\n             unknowing are doing\n             the impossible for\n             the ungrateful. We\n             have done so much\n             for so long with so\n             little we are now\n             qualified to do\n             anything with\n             nothing.\n\n            None\n            ')}
    refold_long_expected[100] = refold_long_expected[0]
    refold_all_expected = refold_long_expected.copy()
    refold_all_expected[0] = 'To: whom_it_may_concern@example.com\nFrom: nobody_you_want_to_know@example.com\nSubject: We the willing led by the unknowing are doing the impossible for the ungrateful. We have done so much for so long with so little we are now qualified to do anything with nothing.\n\nNone\n'
    refold_all_expected[100] = 'To: whom_it_may_concern@example.com\nFrom: nobody_you_want_to_know@example.com\nSubject: We the willing led by the unknowing are doing the impossible for the ungrateful. We have\n done so much for so long with so little we are now qualified to do anything with nothing.\n\nNone\n'
    length_params = [n for n in refold_long_expected]

    def length_as_maxheaderlen_parameter(self, n):
        msg = self.msgmaker(self.typ(self.refold_long_expected[0]))
        s = self.ioclass()
        g = self.genclass(s, maxheaderlen=n, policy=self.policy)
        g.flatten(msg)
        self.assertEqual(s.getvalue(), self.typ(self.refold_long_expected[n]))

    def length_as_max_line_length_policy(self, n):
        msg = self.msgmaker(self.typ(self.refold_long_expected[0]))
        s = self.ioclass()
        g = self.genclass(s, policy=self.policy.clone(max_line_length=n))
        g.flatten(msg)
        self.assertEqual(s.getvalue(), self.typ(self.refold_long_expected[n]))

    def length_as_maxheaderlen_parm_overrides_policy(self, n):
        msg = self.msgmaker(self.typ(self.refold_long_expected[0]))
        s = self.ioclass()
        g = self.genclass(s, maxheaderlen=n, policy=self.policy.clone(max_line_length=10))
        g.flatten(msg)
        self.assertEqual(s.getvalue(), self.typ(self.refold_long_expected[n]))

    def length_as_max_line_length_with_refold_none_does_not_fold(self, n):
        msg = self.msgmaker(self.typ(self.refold_long_expected[0]))
        s = self.ioclass()
        g = self.genclass(s, policy=self.policy.clone(refold_source='none', max_line_length=n))
        g.flatten(msg)
        self.assertEqual(s.getvalue(), self.typ(self.refold_long_expected[0]))

    def length_as_max_line_length_with_refold_all_folds(self, n):
        msg = self.msgmaker(self.typ(self.refold_long_expected[0]))
        s = self.ioclass()
        g = self.genclass(s, policy=self.policy.clone(refold_source='all', max_line_length=n))
        g.flatten(msg)
        self.assertEqual(s.getvalue(), self.typ(self.refold_all_expected[n]))

    def test_crlf_control_via_policy(self):
        source = 'Subject: test\r\n\r\ntest body\r\n'
        expected = source
        msg = self.msgmaker(self.typ(source))
        s = self.ioclass()
        g = self.genclass(s, policy=policy.SMTP)
        g.flatten(msg)
        self.assertEqual(s.getvalue(), self.typ(expected))

    def test_flatten_linesep_overrides_policy(self):
        source = 'Subject: test\n\ntest body\n'
        expected = source
        msg = self.msgmaker(self.typ(source))
        s = self.ioclass()
        g = self.genclass(s, policy=policy.SMTP)
        g.flatten(msg, linesep='\n')
        self.assertEqual(s.getvalue(), self.typ(expected))

    def test_set_mangle_from_via_policy(self):
        source = textwrap.dedent('            Subject: test that\n             from is mangled in the body!\n\n            From time to time I write a rhyme.\n            ')
        variants = ((None, True), (policy.compat32, True), (policy.default, False), (policy.default.clone(mangle_from_=True), True))
        for (p, mangle) in variants:
            expected = (source.replace('From ', '>From ') if mangle else source)
            with self.subTest(policy=p, mangle_from_=mangle):
                msg = self.msgmaker(self.typ(source))
                s = self.ioclass()
                g = self.genclass(s, policy=p)
                g.flatten(msg)
                self.assertEqual(s.getvalue(), self.typ(expected))

    def test_compat32_max_line_length_does_not_fold_when_none(self):
        msg = self.msgmaker(self.typ(self.refold_long_expected[0]))
        s = self.ioclass()
        g = self.genclass(s, policy=policy.compat32.clone(max_line_length=None))
        g.flatten(msg)
        self.assertEqual(s.getvalue(), self.typ(self.refold_long_expected[0]))

    def test_rfc2231_wrapping(self):
        msg = self.msgmaker(self.typ(textwrap.dedent('            To: nobody\n            Content-Disposition: attachment;\n             filename="afilenamelongenoghtowraphere"\n\n            None\n            ')))
        expected = textwrap.dedent("            To: nobody\n            Content-Disposition: attachment;\n             filename*0*=us-ascii''afilename;\n             filename*1*=longenoghtowraphere\n\n            None\n            ")
        s = self.ioclass()
        g = self.genclass(s, policy=self.policy.clone(max_line_length=33))
        g.flatten(msg)
        self.assertEqual(s.getvalue(), self.typ(expected))

    def test_rfc2231_wrapping_switches_to_default_len_if_too_narrow(self):
        msg = self.msgmaker(self.typ(textwrap.dedent('            To: nobody\n            Content-Disposition: attachment;\n             filename="afilenamelongenoghtowraphere"\n\n            None\n            ')))
        expected = textwrap.dedent("            To: nobody\n            Content-Disposition:\n             attachment;\n             filename*0*=us-ascii''afilenamelongenoghtowraphere\n\n            None\n            ")
        s = self.ioclass()
        g = self.genclass(s, policy=self.policy.clone(max_line_length=20))
        g.flatten(msg)
        self.assertEqual(s.getvalue(), self.typ(expected))

class TestGenerator(TestGeneratorBase, TestEmailBase):
    msgfunc = staticmethod(message_from_string)
    genclass = Generator
    ioclass = io.StringIO
    typ = str

class TestBytesGenerator(TestGeneratorBase, TestEmailBase):
    msgfunc = staticmethod(message_from_bytes)
    genclass = BytesGenerator
    ioclass = io.BytesIO
    typ = (lambda self, x: x.encode('ascii'))

    def test_cte_type_7bit_handles_unknown_8bit(self):
        source = 'Subject: Maintenant je vous présente mon collègue\n\n'.encode('utf-8')
        expected = 'Subject: Maintenant je vous =?unknown-8bit?q?pr=C3=A9sente_mon_coll=C3=A8gue?=\n\n'.encode('ascii')
        msg = message_from_bytes(source)
        s = io.BytesIO()
        g = BytesGenerator(s, policy=self.policy.clone(cte_type='7bit'))
        g.flatten(msg)
        self.assertEqual(s.getvalue(), expected)

    def test_cte_type_7bit_transforms_8bit_cte(self):
        source = textwrap.dedent('            From: foo@bar.com\n            To: Dinsdale\n            Subject: Nudge nudge, wink, wink\n            Mime-Version: 1.0\n            Content-Type: text/plain; charset="latin-1"\n            Content-Transfer-Encoding: 8bit\n\n            oh là là, know what I mean, know what I mean?\n            ').encode('latin1')
        msg = message_from_bytes(source)
        expected = textwrap.dedent('            From: foo@bar.com\n            To: Dinsdale\n            Subject: Nudge nudge, wink, wink\n            Mime-Version: 1.0\n            Content-Type: text/plain; charset="iso-8859-1"\n            Content-Transfer-Encoding: quoted-printable\n\n            oh l=E0 l=E0, know what I mean, know what I mean?\n            ').encode('ascii')
        s = io.BytesIO()
        g = BytesGenerator(s, policy=self.policy.clone(cte_type='7bit', linesep='\n'))
        g.flatten(msg)
        self.assertEqual(s.getvalue(), expected)

    def test_smtputf8_policy(self):
        msg = EmailMessage()
        msg['From'] = 'Páolo <főo@bar.com>'
        msg['To'] = 'Dinsdale'
        msg['Subject'] = 'Nudge nudge, wink, wink ὠ9'
        msg.set_content('oh là là, know what I mean, know what I mean?')
        expected = textwrap.dedent('            From: Páolo <főo@bar.com>\n            To: Dinsdale\n            Subject: Nudge nudge, wink, wink ὠ9\n            Content-Type: text/plain; charset="utf-8"\n            Content-Transfer-Encoding: 8bit\n            MIME-Version: 1.0\n\n            oh là là, know what I mean, know what I mean?\n            ').encode('utf-8').replace(b'\n', b'\r\n')
        s = io.BytesIO()
        g = BytesGenerator(s, policy=policy.SMTPUTF8)
        g.flatten(msg)
        self.assertEqual(s.getvalue(), expected)

    def test_smtp_policy(self):
        msg = EmailMessage()
        msg['From'] = Address(addr_spec='foo@bar.com', display_name='Páolo')
        msg['To'] = Address(addr_spec='bar@foo.com', display_name='Dinsdale')
        msg['Subject'] = 'Nudge nudge, wink, wink'
        msg.set_content('oh boy, know what I mean, know what I mean?')
        expected = textwrap.dedent('            From: =?utf-8?q?P=C3=A1olo?= <foo@bar.com>\n            To: Dinsdale <bar@foo.com>\n            Subject: Nudge nudge, wink, wink\n            Content-Type: text/plain; charset="utf-8"\n            Content-Transfer-Encoding: 7bit\n            MIME-Version: 1.0\n\n            oh boy, know what I mean, know what I mean?\n            ').encode().replace(b'\n', b'\r\n')
        s = io.BytesIO()
        g = BytesGenerator(s, policy=policy.SMTP)
        g.flatten(msg)
        self.assertEqual(s.getvalue(), expected)
if (__name__ == '__main__'):
    unittest.main()
