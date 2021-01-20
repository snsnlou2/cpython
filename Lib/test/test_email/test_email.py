
import re
import time
import base64
import unittest
import textwrap
from io import StringIO, BytesIO
from itertools import chain
from random import choice
from threading import Thread
from unittest.mock import patch
import email
import email.policy
from email.charset import Charset
from email.header import Header, decode_header, make_header
from email.parser import Parser, HeaderParser
from email.generator import Generator, DecodedGenerator, BytesGenerator
from email.message import Message
from email.mime.application import MIMEApplication
from email.mime.audio import MIMEAudio
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email.mime.message import MIMEMessage
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
from email import utils
from email import errors
from email import encoders
from email import iterators
from email import base64mime
from email import quoprimime
from test.support import threading_helper
from test.support.os_helper import unlink
from test.test_email import openfile, TestEmailBase
from email.parser import FeedParser, BytesFeedParser
NL = '\n'
EMPTYSTRING = ''
SPACE = ' '

class TestMessageAPI(TestEmailBase):

    def test_get_all(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_20.txt')
        eq(msg.get_all('cc'), ['ccc@zzz.org', 'ddd@zzz.org', 'eee@zzz.org'])
        eq(msg.get_all('xx', 'n/a'), 'n/a')

    def test_getset_charset(self):
        eq = self.assertEqual
        msg = Message()
        eq(msg.get_charset(), None)
        charset = Charset('iso-8859-1')
        msg.set_charset(charset)
        eq(msg['mime-version'], '1.0')
        eq(msg.get_content_type(), 'text/plain')
        eq(msg['content-type'], 'text/plain; charset="iso-8859-1"')
        eq(msg.get_param('charset'), 'iso-8859-1')
        eq(msg['content-transfer-encoding'], 'quoted-printable')
        eq(msg.get_charset().input_charset, 'iso-8859-1')
        msg.set_charset(None)
        eq(msg.get_charset(), None)
        eq(msg['content-type'], 'text/plain')
        msg = Message()
        msg['MIME-Version'] = '2.0'
        msg['Content-Type'] = 'text/x-weird'
        msg['Content-Transfer-Encoding'] = 'quinted-puntable'
        msg.set_charset(charset)
        eq(msg['mime-version'], '2.0')
        eq(msg['content-type'], 'text/x-weird; charset="iso-8859-1"')
        eq(msg['content-transfer-encoding'], 'quinted-puntable')

    def test_set_charset_from_string(self):
        eq = self.assertEqual
        msg = Message()
        msg.set_charset('us-ascii')
        eq(msg.get_charset().input_charset, 'us-ascii')
        eq(msg['content-type'], 'text/plain; charset="us-ascii"')

    def test_set_payload_with_charset(self):
        msg = Message()
        charset = Charset('iso-8859-1')
        msg.set_payload('This is a string payload', charset)
        self.assertEqual(msg.get_charset().input_charset, 'iso-8859-1')

    def test_set_payload_with_8bit_data_and_charset(self):
        data = b'\xd0\x90\xd0\x91\xd0\x92'
        charset = Charset('utf-8')
        msg = Message()
        msg.set_payload(data, charset)
        self.assertEqual(msg['content-transfer-encoding'], 'base64')
        self.assertEqual(msg.get_payload(decode=True), data)
        self.assertEqual(msg.get_payload(), '0JDQkdCS\n')

    def test_set_payload_with_non_ascii_and_charset_body_encoding_none(self):
        data = b'\xd0\x90\xd0\x91\xd0\x92'
        charset = Charset('utf-8')
        charset.body_encoding = None
        msg = Message()
        msg.set_payload(data.decode('utf-8'), charset)
        self.assertEqual(msg['content-transfer-encoding'], '8bit')
        self.assertEqual(msg.get_payload(decode=True), data)

    def test_set_payload_with_8bit_data_and_charset_body_encoding_none(self):
        data = b'\xd0\x90\xd0\x91\xd0\x92'
        charset = Charset('utf-8')
        charset.body_encoding = None
        msg = Message()
        msg.set_payload(data, charset)
        self.assertEqual(msg['content-transfer-encoding'], '8bit')
        self.assertEqual(msg.get_payload(decode=True), data)

    def test_set_payload_to_list(self):
        msg = Message()
        msg.set_payload([])
        self.assertEqual(msg.get_payload(), [])

    def test_attach_when_payload_is_string(self):
        msg = Message()
        msg['Content-Type'] = 'multipart/mixed'
        msg.set_payload('string payload')
        sub_msg = MIMEMessage(Message())
        self.assertRaisesRegex(TypeError, '[Aa]ttach.*non-multipart', msg.attach, sub_msg)

    def test_get_charsets(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_08.txt')
        charsets = msg.get_charsets()
        eq(charsets, [None, 'us-ascii', 'iso-8859-1', 'iso-8859-2', 'koi8-r'])
        msg = self._msgobj('msg_09.txt')
        charsets = msg.get_charsets('dingbat')
        eq(charsets, ['dingbat', 'us-ascii', 'iso-8859-1', 'dingbat', 'koi8-r'])
        msg = self._msgobj('msg_12.txt')
        charsets = msg.get_charsets()
        eq(charsets, [None, 'us-ascii', 'iso-8859-1', None, 'iso-8859-2', 'iso-8859-3', 'us-ascii', 'koi8-r'])

    def test_get_filename(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_04.txt')
        filenames = [p.get_filename() for p in msg.get_payload()]
        eq(filenames, ['msg.txt', 'msg.txt'])
        msg = self._msgobj('msg_07.txt')
        subpart = msg.get_payload(1)
        eq(subpart.get_filename(), 'dingusfish.gif')

    def test_get_filename_with_name_parameter(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_44.txt')
        filenames = [p.get_filename() for p in msg.get_payload()]
        eq(filenames, ['msg.txt', 'msg.txt'])

    def test_get_boundary(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_07.txt')
        eq(msg.get_boundary(), 'BOUNDARY')

    def test_set_boundary(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_01.txt')
        msg.set_boundary('BOUNDARY')
        (header, value) = msg.items()[4]
        eq(header.lower(), 'content-type')
        eq(value, 'text/plain; charset="us-ascii"; boundary="BOUNDARY"')
        msg = self._msgobj('msg_04.txt')
        msg.set_boundary('BOUNDARY')
        (header, value) = msg.items()[4]
        eq(header.lower(), 'content-type')
        eq(value, 'multipart/mixed; boundary="BOUNDARY"')
        msg = self._msgobj('msg_03.txt')
        self.assertRaises(errors.HeaderParseError, msg.set_boundary, 'BOUNDARY')

    def test_make_boundary(self):
        msg = MIMEMultipart('form-data')
        self.assertEqual(msg.items()[0][1], 'multipart/form-data')
        msg.as_string()
        self.assertEqual(msg.items()[0][1][:33], 'multipart/form-data; boundary="==')

    def test_message_rfc822_only(self):
        with openfile('msg_46.txt') as fp:
            msgdata = fp.read()
        parser = HeaderParser()
        msg = parser.parsestr(msgdata)
        out = StringIO()
        gen = Generator(out, True, 0)
        gen.flatten(msg, False)
        self.assertEqual(out.getvalue(), msgdata)

    def test_byte_message_rfc822_only(self):
        with openfile('msg_46.txt') as fp:
            msgdata = fp.read().encode('ascii')
        parser = email.parser.BytesHeaderParser()
        msg = parser.parsebytes(msgdata)
        out = BytesIO()
        gen = email.generator.BytesGenerator(out)
        gen.flatten(msg)
        self.assertEqual(out.getvalue(), msgdata)

    def test_get_decoded_payload(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_10.txt')
        eq(msg.get_payload(decode=True), None)
        eq(msg.get_payload(0).get_payload(decode=True), b'This is a 7bit encoded message.\n')
        eq(msg.get_payload(1).get_payload(decode=True), b'\xa1This is a Quoted Printable encoded message!\n')
        eq(msg.get_payload(2).get_payload(decode=True), b'This is a Base64 encoded message.')
        eq(msg.get_payload(3).get_payload(decode=True), b'This is a Base64 encoded message.\n')
        eq(msg.get_payload(4).get_payload(decode=True), b'This has no Content-Transfer-Encoding: header.\n')

    def test_get_decoded_uu_payload(self):
        eq = self.assertEqual
        msg = Message()
        msg.set_payload('begin 666 -\n+:&5L;&\\@=V]R;&0 \n \nend\n')
        for cte in ('x-uuencode', 'uuencode', 'uue', 'x-uue'):
            msg['content-transfer-encoding'] = cte
            eq(msg.get_payload(decode=True), b'hello world')
        msg.set_payload('foo')
        eq(msg.get_payload(decode=True), b'foo')

    def test_get_payload_n_raises_on_non_multipart(self):
        msg = Message()
        self.assertRaises(TypeError, msg.get_payload, 1)

    def test_decoded_generator(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_07.txt')
        with openfile('msg_17.txt') as fp:
            text = fp.read()
        s = StringIO()
        g = DecodedGenerator(s)
        g.flatten(msg)
        eq(s.getvalue(), text)

    def test__contains__(self):
        msg = Message()
        msg['From'] = 'Me'
        msg['to'] = 'You'
        self.assertIn('from', msg)
        self.assertIn('From', msg)
        self.assertIn('FROM', msg)
        self.assertIn('to', msg)
        self.assertIn('To', msg)
        self.assertIn('TO', msg)

    def test_as_string(self):
        msg = self._msgobj('msg_01.txt')
        with openfile('msg_01.txt') as fp:
            text = fp.read()
        self.assertEqual(text, str(msg))
        fullrepr = msg.as_string(unixfrom=True)
        lines = fullrepr.split('\n')
        self.assertTrue(lines[0].startswith('From '))
        self.assertEqual(text, NL.join(lines[1:]))

    def test_as_string_policy(self):
        msg = self._msgobj('msg_01.txt')
        newpolicy = msg.policy.clone(linesep='\r\n')
        fullrepr = msg.as_string(policy=newpolicy)
        s = StringIO()
        g = Generator(s, policy=newpolicy)
        g.flatten(msg)
        self.assertEqual(fullrepr, s.getvalue())

    def test_as_bytes(self):
        msg = self._msgobj('msg_01.txt')
        with openfile('msg_01.txt') as fp:
            data = fp.read().encode('ascii')
        self.assertEqual(data, bytes(msg))
        fullrepr = msg.as_bytes(unixfrom=True)
        lines = fullrepr.split(b'\n')
        self.assertTrue(lines[0].startswith(b'From '))
        self.assertEqual(data, b'\n'.join(lines[1:]))

    def test_as_bytes_policy(self):
        msg = self._msgobj('msg_01.txt')
        newpolicy = msg.policy.clone(linesep='\r\n')
        fullrepr = msg.as_bytes(policy=newpolicy)
        s = BytesIO()
        g = BytesGenerator(s, policy=newpolicy)
        g.flatten(msg)
        self.assertEqual(fullrepr, s.getvalue())

    def test_bad_param(self):
        msg = email.message_from_string('Content-Type: blarg; baz; boo\n')
        self.assertEqual(msg.get_param('baz'), '')

    def test_missing_filename(self):
        msg = email.message_from_string('From: foo\n')
        self.assertEqual(msg.get_filename(), None)

    def test_bogus_filename(self):
        msg = email.message_from_string('Content-Disposition: blarg; filename\n')
        self.assertEqual(msg.get_filename(), '')

    def test_missing_boundary(self):
        msg = email.message_from_string('From: foo\n')
        self.assertEqual(msg.get_boundary(), None)

    def test_get_params(self):
        eq = self.assertEqual
        msg = email.message_from_string('X-Header: foo=one; bar=two; baz=three\n')
        eq(msg.get_params(header='x-header'), [('foo', 'one'), ('bar', 'two'), ('baz', 'three')])
        msg = email.message_from_string('X-Header: foo; bar=one; baz=two\n')
        eq(msg.get_params(header='x-header'), [('foo', ''), ('bar', 'one'), ('baz', 'two')])
        eq(msg.get_params(), None)
        msg = email.message_from_string('X-Header: foo; bar="one"; baz=two\n')
        eq(msg.get_params(header='x-header'), [('foo', ''), ('bar', 'one'), ('baz', 'two')])

    def test_get_param_liberal(self):
        msg = Message()
        msg['Content-Type'] = 'Content-Type: Multipart/mixed; boundary = "CPIMSSMTPC06p5f3tG"'
        self.assertEqual(msg.get_param('boundary'), 'CPIMSSMTPC06p5f3tG')

    def test_get_param(self):
        eq = self.assertEqual
        msg = email.message_from_string('X-Header: foo=one; bar=two; baz=three\n')
        eq(msg.get_param('bar', header='x-header'), 'two')
        eq(msg.get_param('quuz', header='x-header'), None)
        eq(msg.get_param('quuz'), None)
        msg = email.message_from_string('X-Header: foo; bar="one"; baz=two\n')
        eq(msg.get_param('foo', header='x-header'), '')
        eq(msg.get_param('bar', header='x-header'), 'one')
        eq(msg.get_param('baz', header='x-header'), 'two')

    def test_get_param_funky_continuation_lines(self):
        msg = self._msgobj('msg_22.txt')
        self.assertEqual(msg.get_payload(1).get_param('name'), 'wibble.JPG')

    def test_get_param_with_semis_in_quotes(self):
        msg = email.message_from_string('Content-Type: image/pjpeg; name="Jim&amp;&amp;Jill"\n')
        self.assertEqual(msg.get_param('name'), 'Jim&amp;&amp;Jill')
        self.assertEqual(msg.get_param('name', unquote=False), '"Jim&amp;&amp;Jill"')

    def test_get_param_with_quotes(self):
        msg = email.message_from_string('Content-Type: foo; bar*0="baz\\"foobar"; bar*1="\\"baz"')
        self.assertEqual(msg.get_param('bar'), 'baz"foobar"baz')
        msg = email.message_from_string('Content-Type: foo; bar*0="baz\\"foobar"; bar*1="\\"baz"')
        self.assertEqual(msg.get_param('bar'), 'baz"foobar"baz')

    def test_field_containment(self):
        msg = email.message_from_string('Header: exists')
        self.assertIn('header', msg)
        self.assertIn('Header', msg)
        self.assertIn('HEADER', msg)
        self.assertNotIn('headerx', msg)

    def test_set_param(self):
        eq = self.assertEqual
        msg = Message()
        msg.set_param('charset', 'iso-2022-jp')
        eq(msg.get_param('charset'), 'iso-2022-jp')
        msg.set_param('importance', 'high value')
        eq(msg.get_param('importance'), 'high value')
        eq(msg.get_param('importance', unquote=False), '"high value"')
        eq(msg.get_params(), [('text/plain', ''), ('charset', 'iso-2022-jp'), ('importance', 'high value')])
        eq(msg.get_params(unquote=False), [('text/plain', ''), ('charset', '"iso-2022-jp"'), ('importance', '"high value"')])
        msg.set_param('charset', 'iso-9999-xx', header='X-Jimmy')
        eq(msg.get_param('charset', header='X-Jimmy'), 'iso-9999-xx')

    def test_del_param(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_05.txt')
        eq(msg.get_params(), [('multipart/report', ''), ('report-type', 'delivery-status'), ('boundary', 'D1690A7AC1.996856090/mail.example.com')])
        old_val = msg.get_param('report-type')
        msg.del_param('report-type')
        eq(msg.get_params(), [('multipart/report', ''), ('boundary', 'D1690A7AC1.996856090/mail.example.com')])
        msg.set_param('report-type', old_val)
        eq(msg.get_params(), [('multipart/report', ''), ('boundary', 'D1690A7AC1.996856090/mail.example.com'), ('report-type', old_val)])

    def test_del_param_on_other_header(self):
        msg = Message()
        msg.add_header('Content-Disposition', 'attachment', filename='bud.gif')
        msg.del_param('filename', 'content-disposition')
        self.assertEqual(msg['content-disposition'], 'attachment')

    def test_del_param_on_nonexistent_header(self):
        msg = Message()
        msg.del_param('filename', 'content-disposition')

    def test_del_nonexistent_param(self):
        msg = Message()
        msg.add_header('Content-Type', 'text/plain', charset='utf-8')
        existing_header = msg['Content-Type']
        msg.del_param('foobar', header='Content-Type')
        self.assertEqual(msg['Content-Type'], existing_header)

    def test_set_type(self):
        eq = self.assertEqual
        msg = Message()
        self.assertRaises(ValueError, msg.set_type, 'text')
        msg.set_type('text/plain')
        eq(msg['content-type'], 'text/plain')
        msg.set_param('charset', 'us-ascii')
        eq(msg['content-type'], 'text/plain; charset="us-ascii"')
        msg.set_type('text/html')
        eq(msg['content-type'], 'text/html; charset="us-ascii"')

    def test_set_type_on_other_header(self):
        msg = Message()
        msg['X-Content-Type'] = 'text/plain'
        msg.set_type('application/octet-stream', 'X-Content-Type')
        self.assertEqual(msg['x-content-type'], 'application/octet-stream')

    def test_get_content_type_missing(self):
        msg = Message()
        self.assertEqual(msg.get_content_type(), 'text/plain')

    def test_get_content_type_missing_with_default_type(self):
        msg = Message()
        msg.set_default_type('message/rfc822')
        self.assertEqual(msg.get_content_type(), 'message/rfc822')

    def test_get_content_type_from_message_implicit(self):
        msg = self._msgobj('msg_30.txt')
        self.assertEqual(msg.get_payload(0).get_content_type(), 'message/rfc822')

    def test_get_content_type_from_message_explicit(self):
        msg = self._msgobj('msg_28.txt')
        self.assertEqual(msg.get_payload(0).get_content_type(), 'message/rfc822')

    def test_get_content_type_from_message_text_plain_implicit(self):
        msg = self._msgobj('msg_03.txt')
        self.assertEqual(msg.get_content_type(), 'text/plain')

    def test_get_content_type_from_message_text_plain_explicit(self):
        msg = self._msgobj('msg_01.txt')
        self.assertEqual(msg.get_content_type(), 'text/plain')

    def test_get_content_maintype_missing(self):
        msg = Message()
        self.assertEqual(msg.get_content_maintype(), 'text')

    def test_get_content_maintype_missing_with_default_type(self):
        msg = Message()
        msg.set_default_type('message/rfc822')
        self.assertEqual(msg.get_content_maintype(), 'message')

    def test_get_content_maintype_from_message_implicit(self):
        msg = self._msgobj('msg_30.txt')
        self.assertEqual(msg.get_payload(0).get_content_maintype(), 'message')

    def test_get_content_maintype_from_message_explicit(self):
        msg = self._msgobj('msg_28.txt')
        self.assertEqual(msg.get_payload(0).get_content_maintype(), 'message')

    def test_get_content_maintype_from_message_text_plain_implicit(self):
        msg = self._msgobj('msg_03.txt')
        self.assertEqual(msg.get_content_maintype(), 'text')

    def test_get_content_maintype_from_message_text_plain_explicit(self):
        msg = self._msgobj('msg_01.txt')
        self.assertEqual(msg.get_content_maintype(), 'text')

    def test_get_content_subtype_missing(self):
        msg = Message()
        self.assertEqual(msg.get_content_subtype(), 'plain')

    def test_get_content_subtype_missing_with_default_type(self):
        msg = Message()
        msg.set_default_type('message/rfc822')
        self.assertEqual(msg.get_content_subtype(), 'rfc822')

    def test_get_content_subtype_from_message_implicit(self):
        msg = self._msgobj('msg_30.txt')
        self.assertEqual(msg.get_payload(0).get_content_subtype(), 'rfc822')

    def test_get_content_subtype_from_message_explicit(self):
        msg = self._msgobj('msg_28.txt')
        self.assertEqual(msg.get_payload(0).get_content_subtype(), 'rfc822')

    def test_get_content_subtype_from_message_text_plain_implicit(self):
        msg = self._msgobj('msg_03.txt')
        self.assertEqual(msg.get_content_subtype(), 'plain')

    def test_get_content_subtype_from_message_text_plain_explicit(self):
        msg = self._msgobj('msg_01.txt')
        self.assertEqual(msg.get_content_subtype(), 'plain')

    def test_get_content_maintype_error(self):
        msg = Message()
        msg['Content-Type'] = 'no-slash-in-this-string'
        self.assertEqual(msg.get_content_maintype(), 'text')

    def test_get_content_subtype_error(self):
        msg = Message()
        msg['Content-Type'] = 'no-slash-in-this-string'
        self.assertEqual(msg.get_content_subtype(), 'plain')

    def test_replace_header(self):
        eq = self.assertEqual
        msg = Message()
        msg.add_header('First', 'One')
        msg.add_header('Second', 'Two')
        msg.add_header('Third', 'Three')
        eq(msg.keys(), ['First', 'Second', 'Third'])
        eq(msg.values(), ['One', 'Two', 'Three'])
        msg.replace_header('Second', 'Twenty')
        eq(msg.keys(), ['First', 'Second', 'Third'])
        eq(msg.values(), ['One', 'Twenty', 'Three'])
        msg.add_header('First', 'Eleven')
        msg.replace_header('First', 'One Hundred')
        eq(msg.keys(), ['First', 'Second', 'Third', 'First'])
        eq(msg.values(), ['One Hundred', 'Twenty', 'Three', 'Eleven'])
        self.assertRaises(KeyError, msg.replace_header, 'Fourth', 'Missing')

    def test_get_content_disposition(self):
        msg = Message()
        self.assertIsNone(msg.get_content_disposition())
        msg.add_header('Content-Disposition', 'attachment', filename='random.avi')
        self.assertEqual(msg.get_content_disposition(), 'attachment')
        msg.replace_header('Content-Disposition', 'inline')
        self.assertEqual(msg.get_content_disposition(), 'inline')
        msg.replace_header('Content-Disposition', 'InlinE')
        self.assertEqual(msg.get_content_disposition(), 'inline')

    def test_broken_base64_payload(self):
        x = 'AwDp0P7//y6LwKEAcPa/6Q=9'
        msg = Message()
        msg['content-type'] = 'audio/x-midi'
        msg['content-transfer-encoding'] = 'base64'
        msg.set_payload(x)
        self.assertEqual(msg.get_payload(decode=True), b'\x03\x00\xe9\xd0\xfe\xff\xff.\x8b\xc0\xa1\x00p\xf6\xbf\xe9\x0f')
        self.assertIsInstance(msg.defects[0], errors.InvalidBase64CharactersDefect)

    def test_broken_unicode_payload(self):
        x = 'this is a bröken thing to do'
        msg = Message()
        msg['content-type'] = 'text/plain'
        msg['content-transfer-encoding'] = '8bit'
        msg.set_payload(x)
        self.assertEqual(msg.get_payload(decode=True), bytes(x, 'raw-unicode-escape'))

    def test_questionable_bytes_payload(self):
        x = 'this is a quéstionable thing to do'.encode('utf-8')
        msg = Message()
        msg['content-type'] = 'text/plain; charset="utf-8"'
        msg['content-transfer-encoding'] = '8bit'
        msg._payload = x
        self.assertEqual(msg.get_payload(decode=True), x)

    def test_ascii_add_header(self):
        msg = Message()
        msg.add_header('Content-Disposition', 'attachment', filename='bud.gif')
        self.assertEqual('attachment; filename="bud.gif"', msg['Content-Disposition'])

    def test_noascii_add_header(self):
        msg = Message()
        msg.add_header('Content-Disposition', 'attachment', filename='Fußballer.ppt')
        self.assertEqual("attachment; filename*=utf-8''Fu%C3%9Fballer.ppt", msg['Content-Disposition'])

    def test_nonascii_add_header_via_triple(self):
        msg = Message()
        msg.add_header('Content-Disposition', 'attachment', filename=('iso-8859-1', '', 'Fußballer.ppt'))
        self.assertEqual("attachment; filename*=iso-8859-1''Fu%DFballer.ppt", msg['Content-Disposition'])

    def test_ascii_add_header_with_tspecial(self):
        msg = Message()
        msg.add_header('Content-Disposition', 'attachment', filename='windows [filename].ppt')
        self.assertEqual('attachment; filename="windows [filename].ppt"', msg['Content-Disposition'])

    def test_nonascii_add_header_with_tspecial(self):
        msg = Message()
        msg.add_header('Content-Disposition', 'attachment', filename='Fußballer [filename].ppt')
        self.assertEqual("attachment; filename*=utf-8''Fu%C3%9Fballer%20%5Bfilename%5D.ppt", msg['Content-Disposition'])

    def test_binary_quopri_payload(self):
        for charset in ('latin-1', 'ascii'):
            msg = Message()
            msg['content-type'] = ('text/plain; charset=%s' % charset)
            msg['content-transfer-encoding'] = 'quoted-printable'
            msg.set_payload(b'foo=e6=96=87bar')
            self.assertEqual(msg.get_payload(decode=True), b'foo\xe6\x96\x87bar', ('get_payload returns wrong result with charset %s.' % charset))

    def test_binary_base64_payload(self):
        for charset in ('latin-1', 'ascii'):
            msg = Message()
            msg['content-type'] = ('text/plain; charset=%s' % charset)
            msg['content-transfer-encoding'] = 'base64'
            msg.set_payload(b'Zm9v5paHYmFy')
            self.assertEqual(msg.get_payload(decode=True), b'foo\xe6\x96\x87bar', ('get_payload returns wrong result with charset %s.' % charset))

    def test_binary_uuencode_payload(self):
        for charset in ('latin-1', 'ascii'):
            for encoding in ('x-uuencode', 'uuencode', 'uue', 'x-uue'):
                msg = Message()
                msg['content-type'] = ('text/plain; charset=%s' % charset)
                msg['content-transfer-encoding'] = encoding
                msg.set_payload(b"begin 666 -\n)9F]OYI:'8F%R\n \nend\n")
                self.assertEqual(msg.get_payload(decode=True), b'foo\xe6\x96\x87bar', str(('get_payload returns wrong result ', 'with charset {0} and encoding {1}.')).format(charset, encoding))

    def test_add_header_with_name_only_param(self):
        msg = Message()
        msg.add_header('Content-Disposition', 'inline', foo_bar=None)
        self.assertEqual('inline; foo-bar', msg['Content-Disposition'])

    def test_add_header_with_no_value(self):
        msg = Message()
        msg.add_header('X-Status', None)
        self.assertEqual('', msg['X-Status'])

    def test_embedded_header_via_Header_rejected(self):
        msg = Message()
        msg['Dummy'] = Header('dummy\nX-Injected-Header: test')
        self.assertRaises(errors.HeaderParseError, msg.as_string)

    def test_embedded_header_via_string_rejected(self):
        msg = Message()
        msg['Dummy'] = 'dummy\nX-Injected-Header: test'
        self.assertRaises(errors.HeaderParseError, msg.as_string)

    def test_unicode_header_defaults_to_utf8_encoding(self):
        m = MIMEText('abc\n')
        m['Subject'] = 'É test'
        self.assertEqual(str(m), textwrap.dedent('            Content-Type: text/plain; charset="us-ascii"\n            MIME-Version: 1.0\n            Content-Transfer-Encoding: 7bit\n            Subject: =?utf-8?q?=C3=89_test?=\n\n            abc\n            '))

    def test_unicode_body_defaults_to_utf8_encoding(self):
        m = MIMEText('É testabc\n')
        self.assertEqual(str(m), textwrap.dedent('            Content-Type: text/plain; charset="utf-8"\n            MIME-Version: 1.0\n            Content-Transfer-Encoding: base64\n\n            w4kgdGVzdGFiYwo=\n            '))

class TestEncoders(unittest.TestCase):

    def test_EncodersEncode_base64(self):
        with openfile('PyBanner048.gif', 'rb') as fp:
            bindata = fp.read()
        mimed = email.mime.image.MIMEImage(bindata)
        base64ed = mimed.get_payload()
        lines = base64ed.split('\n')
        self.assertLessEqual(max([len(x) for x in lines]), 76)

    def test_encode_empty_payload(self):
        eq = self.assertEqual
        msg = Message()
        msg.set_charset('us-ascii')
        eq(msg['content-transfer-encoding'], '7bit')

    def test_default_cte(self):
        eq = self.assertEqual
        msg = MIMEText('hello world')
        eq(msg['content-transfer-encoding'], '7bit')
        msg = MIMEText('hello ø world')
        eq(msg['content-transfer-encoding'], 'base64')
        msg = MIMEText('hello ø world', _charset='iso-8859-1')
        eq(msg['content-transfer-encoding'], 'quoted-printable')

    def test_encode7or8bit(self):
        eq = self.assertEqual
        msg = MIMEText('文\n', _charset='euc-jp')
        eq(msg['content-transfer-encoding'], '7bit')
        eq(msg.as_string(), textwrap.dedent('            MIME-Version: 1.0\n            Content-Type: text/plain; charset="iso-2022-jp"\n            Content-Transfer-Encoding: 7bit\n\n            \x1b$BJ8\x1b(B\n            '))

    def test_qp_encode_latin1(self):
        msg = MIMEText('áö\n', 'text', 'ISO-8859-1')
        self.assertEqual(str(msg), textwrap.dedent('            MIME-Version: 1.0\n            Content-Type: text/text; charset="iso-8859-1"\n            Content-Transfer-Encoding: quoted-printable\n\n            =E1=F6\n            '))

    def test_qp_encode_non_latin1(self):
        msg = MIMEText('ż\n', 'text', 'ISO-8859-2')
        self.assertEqual(str(msg), textwrap.dedent('            MIME-Version: 1.0\n            Content-Type: text/text; charset="iso-8859-2"\n            Content-Transfer-Encoding: quoted-printable\n\n            =BF\n            '))

class TestLongHeaders(TestEmailBase):
    maxDiff = None

    def test_split_long_continuation(self):
        eq = self.ndiffAssertEqual
        msg = email.message_from_string('Subject: bug demonstration\n\t12345678911234567892123456789312345678941234567895123456789612345678971234567898112345678911234567892123456789112345678911234567892123456789\n\tmore text\n\ntest\n')
        sfp = StringIO()
        g = Generator(sfp)
        g.flatten(msg)
        eq(sfp.getvalue(), 'Subject: bug demonstration\n\t12345678911234567892123456789312345678941234567895123456789612345678971234567898112345678911234567892123456789112345678911234567892123456789\n\tmore text\n\ntest\n')

    def test_another_long_almost_unsplittable_header(self):
        eq = self.ndiffAssertEqual
        hstr = 'bug demonstration\n\t12345678911234567892123456789312345678941234567895123456789612345678971234567898112345678911234567892123456789112345678911234567892123456789\n\tmore text'
        h = Header(hstr, continuation_ws='\t')
        eq(h.encode(), 'bug demonstration\n\t12345678911234567892123456789312345678941234567895123456789612345678971234567898112345678911234567892123456789112345678911234567892123456789\n\tmore text')
        h = Header(hstr.replace('\t', ' '))
        eq(h.encode(), 'bug demonstration\n 12345678911234567892123456789312345678941234567895123456789612345678971234567898112345678911234567892123456789112345678911234567892123456789\n more text')

    def test_long_nonstring(self):
        eq = self.ndiffAssertEqual
        g = Charset('iso-8859-1')
        cz = Charset('iso-8859-2')
        utf8 = Charset('utf-8')
        g_head = b'Die Mieter treten hier ein werden mit einem Foerderband komfortabel den Korridor entlang, an s\xfcdl\xfcndischen Wandgem\xe4lden vorbei, gegen die rotierenden Klingen bef\xf6rdert. '
        cz_head = b'Finan\xe8ni metropole se hroutily pod tlakem jejich d\xf9vtipu.. '
        utf8_head = '正確に言うと翻訳はされていません。一部はドイツ語ですが、あとはでたらめです。実際には「Wenn ist das Nunstuck git und Slotermeyer? Ja! Beiherhund das Oder die Flipperwaldt gersput.」と言っています。'
        h = Header(g_head, g, header_name='Subject')
        h.append(cz_head, cz)
        h.append(utf8_head, utf8)
        msg = Message()
        msg['Subject'] = h
        sfp = StringIO()
        g = Generator(sfp)
        g.flatten(msg)
        eq(sfp.getvalue(), 'Subject: =?iso-8859-1?q?Die_Mieter_treten_hier_ein_werden_mit_einem_Foerderb?=\n =?iso-8859-1?q?and_komfortabel_den_Korridor_entlang=2C_an_s=FCdl=FCndischen?=\n =?iso-8859-1?q?_Wandgem=E4lden_vorbei=2C_gegen_die_rotierenden_Klingen_bef?=\n =?iso-8859-1?q?=F6rdert=2E_?= =?iso-8859-2?q?Finan=E8ni_metropole_se_hrouti?=\n =?iso-8859-2?q?ly_pod_tlakem_jejich_d=F9vtipu=2E=2E_?= =?utf-8?b?5q2j56K6?=\n =?utf-8?b?44Gr6KiA44GG44Go57+76Kiz44Gv44GV44KM44Gm44GE44G+44Gb44KT44CC5LiA?=\n =?utf-8?b?6YOo44Gv44OJ44Kk44OE6Kqe44Gn44GZ44GM44CB44GC44Go44Gv44Gn44Gf44KJ?=\n =?utf-8?b?44KB44Gn44GZ44CC5a6f6Zqb44Gr44Gv44CMV2VubiBpc3QgZGFzIE51bnN0dWNr?=\n =?utf-8?b?IGdpdCB1bmQgU2xvdGVybWV5ZXI/IEphISBCZWloZXJodW5kIGRhcyBPZGVyIGRp?=\n =?utf-8?b?ZSBGbGlwcGVyd2FsZHQgZ2Vyc3B1dC7jgI3jgajoqIDjgaPjgabjgYTjgb7jgZk=?=\n =?utf-8?b?44CC?=\n\n')
        eq(h.encode(maxlinelen=76), '=?iso-8859-1?q?Die_Mieter_treten_hier_ein_werden_mit_einem_Foerde?=\n =?iso-8859-1?q?rband_komfortabel_den_Korridor_entlang=2C_an_s=FCdl=FCndis?=\n =?iso-8859-1?q?chen_Wandgem=E4lden_vorbei=2C_gegen_die_rotierenden_Klinge?=\n =?iso-8859-1?q?n_bef=F6rdert=2E_?= =?iso-8859-2?q?Finan=E8ni_metropole_se?=\n =?iso-8859-2?q?_hroutily_pod_tlakem_jejich_d=F9vtipu=2E=2E_?=\n =?utf-8?b?5q2j56K644Gr6KiA44GG44Go57+76Kiz44Gv44GV44KM44Gm44GE44G+44Gb?=\n =?utf-8?b?44KT44CC5LiA6YOo44Gv44OJ44Kk44OE6Kqe44Gn44GZ44GM44CB44GC44Go?=\n =?utf-8?b?44Gv44Gn44Gf44KJ44KB44Gn44GZ44CC5a6f6Zqb44Gr44Gv44CMV2VubiBp?=\n =?utf-8?b?c3QgZGFzIE51bnN0dWNrIGdpdCB1bmQgU2xvdGVybWV5ZXI/IEphISBCZWlo?=\n =?utf-8?b?ZXJodW5kIGRhcyBPZGVyIGRpZSBGbGlwcGVyd2FsZHQgZ2Vyc3B1dC7jgI0=?=\n =?utf-8?b?44Go6KiA44Gj44Gm44GE44G+44GZ44CC?=')

    def test_long_header_encode(self):
        eq = self.ndiffAssertEqual
        h = Header('wasnipoop; giraffes="very-long-necked-animals"; spooge="yummy"; hippos="gargantuan"; marshmallows="gooey"', header_name='X-Foobar-Spoink-Defrobnit')
        eq(h.encode(), 'wasnipoop; giraffes="very-long-necked-animals";\n spooge="yummy"; hippos="gargantuan"; marshmallows="gooey"')

    def test_long_header_encode_with_tab_continuation_is_just_a_hint(self):
        eq = self.ndiffAssertEqual
        h = Header('wasnipoop; giraffes="very-long-necked-animals"; spooge="yummy"; hippos="gargantuan"; marshmallows="gooey"', header_name='X-Foobar-Spoink-Defrobnit', continuation_ws='\t')
        eq(h.encode(), 'wasnipoop; giraffes="very-long-necked-animals";\n spooge="yummy"; hippos="gargantuan"; marshmallows="gooey"')

    def test_long_header_encode_with_tab_continuation(self):
        eq = self.ndiffAssertEqual
        h = Header('wasnipoop; giraffes="very-long-necked-animals";\tspooge="yummy"; hippos="gargantuan"; marshmallows="gooey"', header_name='X-Foobar-Spoink-Defrobnit', continuation_ws='\t')
        eq(h.encode(), 'wasnipoop; giraffes="very-long-necked-animals";\n\tspooge="yummy"; hippos="gargantuan"; marshmallows="gooey"')

    def test_header_encode_with_different_output_charset(self):
        h = Header('文', 'euc-jp')
        self.assertEqual(h.encode(), '=?iso-2022-jp?b?GyRCSjgbKEI=?=')

    def test_long_header_encode_with_different_output_charset(self):
        h = Header(b'test-ja \xa4\xd8\xc5\xea\xb9\xc6\xa4\xb5\xa4\xec\xa4\xbf\xa5\xe1\xa1\xbc\xa5\xeb\xa4\xcf\xbb\xca\xb2\xf1\xbc\xd4\xa4\xce\xbe\xb5\xc7\xa7\xa4\xf2\xc2\xd4\xa4\xc3\xa4\xc6\xa4\xa4\xa4\xde\xa4\xb9'.decode('euc-jp'), 'euc-jp')
        res = '=?iso-2022-jp?b?dGVzdC1qYSAbJEIkWEVqOUYkNSRsJD8lYSE8JWskTztKMnE8VCROPjUbKEI=?=\n =?iso-2022-jp?b?GyRCRyckckJUJEMkRiQkJF4kORsoQg==?='
        self.assertEqual(h.encode(), res)

    def test_header_splitter(self):
        eq = self.ndiffAssertEqual
        msg = MIMEText('')
        msg['X-Foobar-Spoink-Defrobnit'] = 'wasnipoop; giraffes="very-long-necked-animals"; spooge="yummy"; hippos="gargantuan"; marshmallows="gooey"'
        sfp = StringIO()
        g = Generator(sfp)
        g.flatten(msg)
        eq(sfp.getvalue(), 'Content-Type: text/plain; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\nX-Foobar-Spoink-Defrobnit: wasnipoop; giraffes="very-long-necked-animals";\n spooge="yummy"; hippos="gargantuan"; marshmallows="gooey"\n\n')

    def test_no_semis_header_splitter(self):
        eq = self.ndiffAssertEqual
        msg = Message()
        msg['From'] = 'test@dom.ain'
        msg['References'] = SPACE.join((('<%d@dom.ain>' % i) for i in range(10)))
        msg.set_payload('Test')
        sfp = StringIO()
        g = Generator(sfp)
        g.flatten(msg)
        eq(sfp.getvalue(), 'From: test@dom.ain\nReferences: <0@dom.ain> <1@dom.ain> <2@dom.ain> <3@dom.ain> <4@dom.ain>\n <5@dom.ain> <6@dom.ain> <7@dom.ain> <8@dom.ain> <9@dom.ain>\n\nTest')

    def test_last_split_chunk_does_not_fit(self):
        eq = self.ndiffAssertEqual
        h = Header('Subject: the first part of this is short, but_the_second_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself')
        eq(h.encode(), 'Subject: the first part of this is short,\n but_the_second_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself')

    def test_splittable_leading_char_followed_by_overlong_unsplittable(self):
        eq = self.ndiffAssertEqual
        h = Header(', but_the_second_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself')
        eq(h.encode(), ',\n but_the_second_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself')

    def test_multiple_splittable_leading_char_followed_by_overlong_unsplittable(self):
        eq = self.ndiffAssertEqual
        h = Header(', , but_the_second_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself')
        eq(h.encode(), ', ,\n but_the_second_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself')

    def test_trailing_splittable_on_overlong_unsplittable(self):
        eq = self.ndiffAssertEqual
        h = Header('this_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself;')
        eq(h.encode(), 'this_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself;')

    def test_trailing_splittable_on_overlong_unsplittable_with_leading_splittable(self):
        eq = self.ndiffAssertEqual
        h = Header('; this_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself; ')
        eq(h.encode(), ';\n this_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself; ')

    def test_long_header_with_multiple_sequential_split_chars(self):
        eq = self.ndiffAssertEqual
        h = Header('This is a long line that has two whitespaces  in a row.  This used to cause truncation of the header when folded')
        eq(h.encode(), 'This is a long line that has two whitespaces  in a row.  This used to cause\n truncation of the header when folded')

    def test_splitter_split_on_punctuation_only_if_fws_with_header(self):
        eq = self.ndiffAssertEqual
        h = Header('thisverylongheaderhas;semicolons;and,commas,butthey;arenotlegal;fold,points')
        eq(h.encode(), 'thisverylongheaderhas;semicolons;and,commas,butthey;arenotlegal;fold,points')

    def test_leading_splittable_in_the_middle_just_before_overlong_last_part(self):
        eq = self.ndiffAssertEqual
        h = Header('this is a  test where we need to have more than one line before; our final line that is just too big to fit;; this_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself;')
        eq(h.encode(), 'this is a  test where we need to have more than one line before;\n our final line that is just too big to fit;;\n this_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself;')

    def test_overlong_last_part_followed_by_split_point(self):
        eq = self.ndiffAssertEqual
        h = Header('this_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself ')
        eq(h.encode(), 'this_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself ')

    def test_multiline_with_overlong_parts_separated_by_two_split_points(self):
        eq = self.ndiffAssertEqual
        h = Header('this_is_a__test_where_we_need_to_have_more_than_one_line_before_our_final_line_; ; this_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself; ')
        eq(h.encode(), 'this_is_a__test_where_we_need_to_have_more_than_one_line_before_our_final_line_;\n ;\n this_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself; ')

    def test_multiline_with_overlong_last_part_followed_by_split_point(self):
        eq = self.ndiffAssertEqual
        h = Header('this is a test where we need to have more than one line before our final line; ; this_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself; ')
        eq(h.encode(), 'this is a test where we need to have more than one line before our final line;\n ;\n this_part_does_not_fit_within_maxlinelen_and_thus_should_be_on_a_line_all_by_itself; ')

    def test_long_header_with_whitespace_runs(self):
        eq = self.ndiffAssertEqual
        msg = Message()
        msg['From'] = 'test@dom.ain'
        msg['References'] = SPACE.join((['<foo@dom.ain>  '] * 10))
        msg.set_payload('Test')
        sfp = StringIO()
        g = Generator(sfp)
        g.flatten(msg)
        eq(sfp.getvalue(), 'From: test@dom.ain\nReferences: <foo@dom.ain>   <foo@dom.ain>   <foo@dom.ain>   <foo@dom.ain>\n   <foo@dom.ain>   <foo@dom.ain>   <foo@dom.ain>   <foo@dom.ain>\n   <foo@dom.ain>   <foo@dom.ain>  \n\nTest')

    def test_long_run_with_semi_header_splitter(self):
        eq = self.ndiffAssertEqual
        msg = Message()
        msg['From'] = 'test@dom.ain'
        msg['References'] = (SPACE.join((['<foo@dom.ain>'] * 10)) + '; abc')
        msg.set_payload('Test')
        sfp = StringIO()
        g = Generator(sfp)
        g.flatten(msg)
        eq(sfp.getvalue(), 'From: test@dom.ain\nReferences: <foo@dom.ain> <foo@dom.ain> <foo@dom.ain> <foo@dom.ain>\n <foo@dom.ain> <foo@dom.ain> <foo@dom.ain> <foo@dom.ain> <foo@dom.ain>\n <foo@dom.ain>; abc\n\nTest')

    def test_splitter_split_on_punctuation_only_if_fws(self):
        eq = self.ndiffAssertEqual
        msg = Message()
        msg['From'] = 'test@dom.ain'
        msg['References'] = 'thisverylongheaderhas;semicolons;and,commas,butthey;arenotlegal;fold,points'
        msg.set_payload('Test')
        sfp = StringIO()
        g = Generator(sfp)
        g.flatten(msg)
        eq(sfp.getvalue(), 'From: test@dom.ain\nReferences: \n thisverylongheaderhas;semicolons;and,commas,butthey;arenotlegal;fold,points\n\nTest')

    def test_no_split_long_header(self):
        eq = self.ndiffAssertEqual
        hstr = ('References: ' + ('x' * 80))
        h = Header(hstr)
        eq(h.encode(), 'References:\n xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
        h = Header(('x' * 80))
        eq(h.encode(), 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')

    def test_splitting_multiple_long_lines(self):
        eq = self.ndiffAssertEqual
        hstr = 'from babylon.socal-raves.org (localhost [127.0.0.1]); by babylon.socal-raves.org (Postfix) with ESMTP id B570E51B81; for <mailman-admin@babylon.socal-raves.org>; Sat, 2 Feb 2002 17:00:06 -0800 (PST)\n\tfrom babylon.socal-raves.org (localhost [127.0.0.1]); by babylon.socal-raves.org (Postfix) with ESMTP id B570E51B81; for <mailman-admin@babylon.socal-raves.org>; Sat, 2 Feb 2002 17:00:06 -0800 (PST)\n\tfrom babylon.socal-raves.org (localhost [127.0.0.1]); by babylon.socal-raves.org (Postfix) with ESMTP id B570E51B81; for <mailman-admin@babylon.socal-raves.org>; Sat, 2 Feb 2002 17:00:06 -0800 (PST)\n'
        h = Header(hstr, continuation_ws='\t')
        eq(h.encode(), 'from babylon.socal-raves.org (localhost [127.0.0.1]);\n by babylon.socal-raves.org (Postfix) with ESMTP id B570E51B81;\n for <mailman-admin@babylon.socal-raves.org>;\n Sat, 2 Feb 2002 17:00:06 -0800 (PST)\n\tfrom babylon.socal-raves.org (localhost [127.0.0.1]);\n by babylon.socal-raves.org (Postfix) with ESMTP id B570E51B81;\n for <mailman-admin@babylon.socal-raves.org>;\n Sat, 2 Feb 2002 17:00:06 -0800 (PST)\n\tfrom babylon.socal-raves.org (localhost [127.0.0.1]);\n by babylon.socal-raves.org (Postfix) with ESMTP id B570E51B81;\n for <mailman-admin@babylon.socal-raves.org>;\n Sat, 2 Feb 2002 17:00:06 -0800 (PST)')

    def test_splitting_first_line_only_is_long(self):
        eq = self.ndiffAssertEqual
        hstr = 'from modemcable093.139-201-24.que.mc.videotron.ca ([24.201.139.93] helo=cthulhu.gerg.ca)\n\tby kronos.mems-exchange.org with esmtp (Exim 4.05)\n\tid 17k4h5-00034i-00\n\tfor test@mems-exchange.org; Wed, 28 Aug 2002 11:25:20 -0400'
        h = Header(hstr, maxlinelen=78, header_name='Received', continuation_ws='\t')
        eq(h.encode(), 'from modemcable093.139-201-24.que.mc.videotron.ca ([24.201.139.93]\n helo=cthulhu.gerg.ca)\n\tby kronos.mems-exchange.org with esmtp (Exim 4.05)\n\tid 17k4h5-00034i-00\n\tfor test@mems-exchange.org; Wed, 28 Aug 2002 11:25:20 -0400')

    def test_long_8bit_header(self):
        eq = self.ndiffAssertEqual
        msg = Message()
        h = Header('Britische Regierung gibt', 'iso-8859-1', header_name='Subject')
        h.append('grünes Licht für Offshore-Windkraftprojekte')
        eq(h.encode(maxlinelen=76), '=?iso-8859-1?q?Britische_Regierung_gibt_gr=FCnes_Licht_f=FCr_Offs?=\n =?iso-8859-1?q?hore-Windkraftprojekte?=')
        msg['Subject'] = h
        eq(msg.as_string(maxheaderlen=76), 'Subject: =?iso-8859-1?q?Britische_Regierung_gibt_gr=FCnes_Licht_f=FCr_Offs?=\n =?iso-8859-1?q?hore-Windkraftprojekte?=\n\n')
        eq(msg.as_string(maxheaderlen=0), 'Subject: =?iso-8859-1?q?Britische_Regierung_gibt_gr=FCnes_Licht_f=FCr_Offshore-Windkraftprojekte?=\n\n')

    def test_long_8bit_header_no_charset(self):
        eq = self.ndiffAssertEqual
        msg = Message()
        header_string = 'Britische Regierung gibt grünes Licht für Offshore-Windkraftprojekte <a-very-long-address@example.com>'
        msg['Reply-To'] = header_string
        eq(msg.as_string(maxheaderlen=78), 'Reply-To: =?utf-8?q?Britische_Regierung_gibt_gr=C3=BCnes_Licht_f=C3=BCr_Offs?=\n =?utf-8?q?hore-Windkraftprojekte_=3Ca-very-long-address=40example=2Ecom=3E?=\n\n')
        msg = Message()
        msg['Reply-To'] = Header(header_string, header_name='Reply-To')
        eq(msg.as_string(maxheaderlen=78), 'Reply-To: =?utf-8?q?Britische_Regierung_gibt_gr=C3=BCnes_Licht_f=C3=BCr_Offs?=\n =?utf-8?q?hore-Windkraftprojekte_=3Ca-very-long-address=40example=2Ecom=3E?=\n\n')

    def test_long_to_header(self):
        eq = self.ndiffAssertEqual
        to = '"Someone Test #A" <someone@eecs.umich.edu>,<someone@eecs.umich.edu>, "Someone Test #B" <someone@umich.edu>, "Someone Test #C" <someone@eecs.umich.edu>, "Someone Test #D" <someone@eecs.umich.edu>'
        msg = Message()
        msg['To'] = to
        eq(msg.as_string(maxheaderlen=78), 'To: "Someone Test #A" <someone@eecs.umich.edu>,<someone@eecs.umich.edu>,\n "Someone Test #B" <someone@umich.edu>,\n "Someone Test #C" <someone@eecs.umich.edu>,\n "Someone Test #D" <someone@eecs.umich.edu>\n\n')

    def test_long_line_after_append(self):
        eq = self.ndiffAssertEqual
        s = 'This is an example of string which has almost the limit of header length.'
        h = Header(s)
        h.append('Add another line.')
        eq(h.encode(maxlinelen=76), 'This is an example of string which has almost the limit of header length.\n Add another line.')

    def test_shorter_line_with_append(self):
        eq = self.ndiffAssertEqual
        s = 'This is a shorter line.'
        h = Header(s)
        h.append('Add another sentence. (Surprise?)')
        eq(h.encode(), 'This is a shorter line. Add another sentence. (Surprise?)')

    def test_long_field_name(self):
        eq = self.ndiffAssertEqual
        fn = 'X-Very-Very-Very-Long-Header-Name'
        gs = 'Die Mieter treten hier ein werden mit einem Foerderband komfortabel den Korridor entlang, an südlündischen Wandgemälden vorbei, gegen die rotierenden Klingen befördert. '
        h = Header(gs, 'iso-8859-1', header_name=fn)
        eq(h.encode(maxlinelen=76), '=?iso-8859-1?q?Die_Mieter_treten_hier_e?=\n =?iso-8859-1?q?in_werden_mit_einem_Foerderband_komfortabel_den_Korridor_e?=\n =?iso-8859-1?q?ntlang=2C_an_s=FCdl=FCndischen_Wandgem=E4lden_vorbei=2C_ge?=\n =?iso-8859-1?q?gen_die_rotierenden_Klingen_bef=F6rdert=2E_?=')

    def test_long_received_header(self):
        h = 'from FOO.TLD (vizworld.acl.foo.tld [123.452.678.9]) by hrothgar.la.mastaler.com (tmda-ofmipd) with ESMTP; Wed, 05 Mar 2003 18:10:18 -0700'
        msg = Message()
        msg['Received-1'] = Header(h, continuation_ws='\t')
        msg['Received-2'] = h
        self.ndiffAssertEqual(msg.as_string(maxheaderlen=78), 'Received-1: from FOO.TLD (vizworld.acl.foo.tld [123.452.678.9]) by\n hrothgar.la.mastaler.com (tmda-ofmipd) with ESMTP;\n Wed, 05 Mar 2003 18:10:18 -0700\nReceived-2: from FOO.TLD (vizworld.acl.foo.tld [123.452.678.9]) by\n hrothgar.la.mastaler.com (tmda-ofmipd) with ESMTP;\n Wed, 05 Mar 2003 18:10:18 -0700\n\n')

    def test_string_headerinst_eq(self):
        h = '<15975.17901.207240.414604@sgigritzmann1.mathematik.tu-muenchen.de> (David Bremner\'s message of "Thu, 6 Mar 2003 13:58:21 +0100")'
        msg = Message()
        msg['Received-1'] = Header(h, header_name='Received-1', continuation_ws='\t')
        msg['Received-2'] = h
        self.ndiffAssertEqual(msg.as_string(maxheaderlen=78), 'Received-1: \n <15975.17901.207240.414604@sgigritzmann1.mathematik.tu-muenchen.de> (David\n Bremner\'s message of "Thu, 6 Mar 2003 13:58:21 +0100")\nReceived-2: \n <15975.17901.207240.414604@sgigritzmann1.mathematik.tu-muenchen.de> (David\n Bremner\'s message of "Thu, 6 Mar 2003 13:58:21 +0100")\n\n')

    def test_long_unbreakable_lines_with_continuation(self):
        eq = self.ndiffAssertEqual
        msg = Message()
        t = 'iVBORw0KGgoAAAANSUhEUgAAADAAAAAwBAMAAAClLOS0AAAAGFBMVEUAAAAkHiJeRUIcGBi9\n locQDQ4zJykFBAXJfWDjAAACYUlEQVR4nF2TQY/jIAyFc6lydlG5x8Nyp1Y69wj1PN2I5gzp'
        msg['Face-1'] = t
        msg['Face-2'] = Header(t, header_name='Face-2')
        msg['Face-3'] = (' ' + t)
        eq(msg.as_string(maxheaderlen=78), 'Face-1: \n iVBORw0KGgoAAAANSUhEUgAAADAAAAAwBAMAAAClLOS0AAAAGFBMVEUAAAAkHiJeRUIcGBi9\n locQDQ4zJykFBAXJfWDjAAACYUlEQVR4nF2TQY/jIAyFc6lydlG5x8Nyp1Y69wj1PN2I5gzp\nFace-2: \n iVBORw0KGgoAAAANSUhEUgAAADAAAAAwBAMAAAClLOS0AAAAGFBMVEUAAAAkHiJeRUIcGBi9\n locQDQ4zJykFBAXJfWDjAAACYUlEQVR4nF2TQY/jIAyFc6lydlG5x8Nyp1Y69wj1PN2I5gzp\nFace-3: \n iVBORw0KGgoAAAANSUhEUgAAADAAAAAwBAMAAAClLOS0AAAAGFBMVEUAAAAkHiJeRUIcGBi9\n locQDQ4zJykFBAXJfWDjAAACYUlEQVR4nF2TQY/jIAyFc6lydlG5x8Nyp1Y69wj1PN2I5gzp\n\n')

    def test_another_long_multiline_header(self):
        eq = self.ndiffAssertEqual
        m = 'Received: from siimage.com ([172.25.1.3]) by zima.siliconimage.com with Microsoft SMTPSVC(5.0.2195.4905); Wed, 16 Oct 2002 07:41:11 -0700'
        msg = email.message_from_string(m)
        eq(msg.as_string(maxheaderlen=78), 'Received: from siimage.com ([172.25.1.3]) by zima.siliconimage.com with\n Microsoft SMTPSVC(5.0.2195.4905); Wed, 16 Oct 2002 07:41:11 -0700\n\n')

    def test_long_lines_with_different_header(self):
        eq = self.ndiffAssertEqual
        h = 'List-Unsubscribe: <http://lists.sourceforge.net/lists/listinfo/spamassassin-talk>,        <mailto:spamassassin-talk-request@lists.sourceforge.net?subject=unsubscribe>'
        msg = Message()
        msg['List'] = h
        msg['List'] = Header(h, header_name='List')
        eq(msg.as_string(maxheaderlen=78), 'List: List-Unsubscribe:\n <http://lists.sourceforge.net/lists/listinfo/spamassassin-talk>,\n        <mailto:spamassassin-talk-request@lists.sourceforge.net?subject=unsubscribe>\nList: List-Unsubscribe:\n <http://lists.sourceforge.net/lists/listinfo/spamassassin-talk>,\n        <mailto:spamassassin-talk-request@lists.sourceforge.net?subject=unsubscribe>\n\n')

    def test_long_rfc2047_header_with_embedded_fws(self):
        h = Header(textwrap.dedent("            We're going to pretend this header is in a non-ascii character set\n            \tto see if line wrapping with encoded words and embedded\n               folding white space works"), charset='utf-8', header_name='Test')
        self.assertEqual((h.encode() + '\n'), (textwrap.dedent('            =?utf-8?q?We=27re_going_to_pretend_this_header_is_in_a_non-ascii_chara?=\n             =?utf-8?q?cter_set?=\n             =?utf-8?q?_to_see_if_line_wrapping_with_encoded_words_and_embedded?=\n             =?utf-8?q?_folding_white_space_works?=') + '\n'))

class TestFromMangling(unittest.TestCase):

    def setUp(self):
        self.msg = Message()
        self.msg['From'] = 'aaa@bbb.org'
        self.msg.set_payload('From the desk of A.A.A.:\nBlah blah blah\n')

    def test_mangled_from(self):
        s = StringIO()
        g = Generator(s, mangle_from_=True)
        g.flatten(self.msg)
        self.assertEqual(s.getvalue(), 'From: aaa@bbb.org\n\n>From the desk of A.A.A.:\nBlah blah blah\n')

    def test_dont_mangle_from(self):
        s = StringIO()
        g = Generator(s, mangle_from_=False)
        g.flatten(self.msg)
        self.assertEqual(s.getvalue(), 'From: aaa@bbb.org\n\nFrom the desk of A.A.A.:\nBlah blah blah\n')

    def test_mangle_from_in_preamble_and_epilog(self):
        s = StringIO()
        g = Generator(s, mangle_from_=True)
        msg = email.message_from_string(textwrap.dedent('            From: foo@bar.com\n            Mime-Version: 1.0\n            Content-Type: multipart/mixed; boundary=XXX\n\n            From somewhere unknown\n\n            --XXX\n            Content-Type: text/plain\n\n            foo\n\n            --XXX--\n\n            From somewhere unknowable\n            '))
        g.flatten(msg)
        self.assertEqual(len([1 for x in s.getvalue().split('\n') if x.startswith('>From ')]), 2)

    def test_mangled_from_with_bad_bytes(self):
        source = textwrap.dedent('            Content-Type: text/plain; charset="utf-8"\n            MIME-Version: 1.0\n            Content-Transfer-Encoding: 8bit\n            From: aaa@bbb.org\n\n        ').encode('utf-8')
        msg = email.message_from_bytes((source + b'From R\xc3\xb6lli\n'))
        b = BytesIO()
        g = BytesGenerator(b, mangle_from_=True)
        g.flatten(msg)
        self.assertEqual(b.getvalue(), (source + b'>From R\xc3\xb6lli\n'))

    def test_multipart_with_bad_bytes_in_cte(self):
        source = textwrap.dedent('            From: aperson@example.com\n            Content-Type: multipart/mixed; boundary="1"\n            Content-Transfer-Encoding: È\n        ').encode('utf-8')
        msg = email.message_from_bytes(source)

class TestMIMEAudio(unittest.TestCase):

    def setUp(self):
        with openfile('audiotest.au', 'rb') as fp:
            self._audiodata = fp.read()
        self._au = MIMEAudio(self._audiodata)

    def test_guess_minor_type(self):
        self.assertEqual(self._au.get_content_type(), 'audio/basic')

    def test_encoding(self):
        payload = self._au.get_payload()
        self.assertEqual(base64.decodebytes(bytes(payload, 'ascii')), self._audiodata)

    def test_checkSetMinor(self):
        au = MIMEAudio(self._audiodata, 'fish')
        self.assertEqual(au.get_content_type(), 'audio/fish')

    def test_add_header(self):
        eq = self.assertEqual
        self._au.add_header('Content-Disposition', 'attachment', filename='audiotest.au')
        eq(self._au['content-disposition'], 'attachment; filename="audiotest.au"')
        eq(self._au.get_params(header='content-disposition'), [('attachment', ''), ('filename', 'audiotest.au')])
        eq(self._au.get_param('filename', header='content-disposition'), 'audiotest.au')
        missing = []
        eq(self._au.get_param('attachment', header='content-disposition'), '')
        self.assertIs(self._au.get_param('foo', failobj=missing, header='content-disposition'), missing)
        self.assertIs(self._au.get_param('foobar', missing), missing)
        self.assertIs(self._au.get_param('attachment', missing, header='foobar'), missing)

class TestMIMEImage(unittest.TestCase):

    def setUp(self):
        with openfile('PyBanner048.gif', 'rb') as fp:
            self._imgdata = fp.read()
        self._im = MIMEImage(self._imgdata)

    def test_guess_minor_type(self):
        self.assertEqual(self._im.get_content_type(), 'image/gif')

    def test_encoding(self):
        payload = self._im.get_payload()
        self.assertEqual(base64.decodebytes(bytes(payload, 'ascii')), self._imgdata)

    def test_checkSetMinor(self):
        im = MIMEImage(self._imgdata, 'fish')
        self.assertEqual(im.get_content_type(), 'image/fish')

    def test_add_header(self):
        eq = self.assertEqual
        self._im.add_header('Content-Disposition', 'attachment', filename='dingusfish.gif')
        eq(self._im['content-disposition'], 'attachment; filename="dingusfish.gif"')
        eq(self._im.get_params(header='content-disposition'), [('attachment', ''), ('filename', 'dingusfish.gif')])
        eq(self._im.get_param('filename', header='content-disposition'), 'dingusfish.gif')
        missing = []
        eq(self._im.get_param('attachment', header='content-disposition'), '')
        self.assertIs(self._im.get_param('foo', failobj=missing, header='content-disposition'), missing)
        self.assertIs(self._im.get_param('foobar', missing), missing)
        self.assertIs(self._im.get_param('attachment', missing, header='foobar'), missing)

class TestMIMEApplication(unittest.TestCase):

    def test_headers(self):
        eq = self.assertEqual
        msg = MIMEApplication(b'\xfa\xfb\xfc\xfd\xfe\xff')
        eq(msg.get_content_type(), 'application/octet-stream')
        eq(msg['content-transfer-encoding'], 'base64')

    def test_body(self):
        eq = self.assertEqual
        bytesdata = b'\xfa\xfb\xfc\xfd\xfe\xff'
        msg = MIMEApplication(bytesdata)
        eq(msg.get_payload().strip(), '+vv8/f7/')
        eq(msg.get_payload(decode=True), bytesdata)

    def test_binary_body_with_encode_7or8bit(self):
        bytesdata = b'\xfa\xfb\xfc\xfd\xfe\xff'
        msg = MIMEApplication(bytesdata, _encoder=encoders.encode_7or8bit)
        self.assertEqual(msg.get_payload(), ('�' * len(bytesdata)))
        self.assertEqual(msg.get_payload(decode=True), bytesdata)
        self.assertEqual(msg['Content-Transfer-Encoding'], '8bit')
        s = BytesIO()
        g = BytesGenerator(s)
        g.flatten(msg)
        wireform = s.getvalue()
        msg2 = email.message_from_bytes(wireform)
        self.assertEqual(msg.get_payload(), ('�' * len(bytesdata)))
        self.assertEqual(msg2.get_payload(decode=True), bytesdata)
        self.assertEqual(msg2['Content-Transfer-Encoding'], '8bit')

    def test_binary_body_with_encode_noop(self):
        bytesdata = b'\xfa\xfb\xfc\xfd\xfe\xff'
        msg = MIMEApplication(bytesdata, _encoder=encoders.encode_noop)
        self.assertEqual(msg.get_payload(), ('�' * len(bytesdata)))
        self.assertEqual(msg.get_payload(decode=True), bytesdata)
        s = BytesIO()
        g = BytesGenerator(s)
        g.flatten(msg)
        wireform = s.getvalue()
        msg2 = email.message_from_bytes(wireform)
        self.assertEqual(msg.get_payload(), ('�' * len(bytesdata)))
        self.assertEqual(msg2.get_payload(decode=True), bytesdata)

    def test_binary_body_with_unicode_linend_encode_noop(self):
        bytesdata = b'\x0b\xfa\xfb\xfc\xfd\xfe\xff'
        msg = MIMEApplication(bytesdata, _encoder=encoders.encode_noop)
        self.assertEqual(msg.get_payload(decode=True), bytesdata)
        s = BytesIO()
        g = BytesGenerator(s)
        g.flatten(msg)
        wireform = s.getvalue()
        msg2 = email.message_from_bytes(wireform)
        self.assertEqual(msg2.get_payload(decode=True), bytesdata)

    def test_binary_body_with_encode_quopri(self):
        bytesdata = b'\xfa\xfb\xfc\xfd\xfe\xff '
        msg = MIMEApplication(bytesdata, _encoder=encoders.encode_quopri)
        self.assertEqual(msg.get_payload(), '=FA=FB=FC=FD=FE=FF=20')
        self.assertEqual(msg.get_payload(decode=True), bytesdata)
        self.assertEqual(msg['Content-Transfer-Encoding'], 'quoted-printable')
        s = BytesIO()
        g = BytesGenerator(s)
        g.flatten(msg)
        wireform = s.getvalue()
        msg2 = email.message_from_bytes(wireform)
        self.assertEqual(msg.get_payload(), '=FA=FB=FC=FD=FE=FF=20')
        self.assertEqual(msg2.get_payload(decode=True), bytesdata)
        self.assertEqual(msg2['Content-Transfer-Encoding'], 'quoted-printable')

    def test_binary_body_with_encode_base64(self):
        bytesdata = b'\xfa\xfb\xfc\xfd\xfe\xff'
        msg = MIMEApplication(bytesdata, _encoder=encoders.encode_base64)
        self.assertEqual(msg.get_payload(), '+vv8/f7/\n')
        self.assertEqual(msg.get_payload(decode=True), bytesdata)
        s = BytesIO()
        g = BytesGenerator(s)
        g.flatten(msg)
        wireform = s.getvalue()
        msg2 = email.message_from_bytes(wireform)
        self.assertEqual(msg.get_payload(), '+vv8/f7/\n')
        self.assertEqual(msg2.get_payload(decode=True), bytesdata)

class TestMIMEText(unittest.TestCase):

    def setUp(self):
        self._msg = MIMEText('hello there')

    def test_types(self):
        eq = self.assertEqual
        eq(self._msg.get_content_type(), 'text/plain')
        eq(self._msg.get_param('charset'), 'us-ascii')
        missing = []
        self.assertIs(self._msg.get_param('foobar', missing), missing)
        self.assertIs(self._msg.get_param('charset', missing, header='foobar'), missing)

    def test_payload(self):
        self.assertEqual(self._msg.get_payload(), 'hello there')
        self.assertFalse(self._msg.is_multipart())

    def test_charset(self):
        eq = self.assertEqual
        msg = MIMEText('hello there', _charset='us-ascii')
        eq(msg.get_charset().input_charset, 'us-ascii')
        eq(msg['content-type'], 'text/plain; charset="us-ascii"')
        charset = Charset('utf-8')
        charset.body_encoding = None
        msg = MIMEText('hello there', _charset=charset)
        eq(msg.get_charset().input_charset, 'utf-8')
        eq(msg['content-type'], 'text/plain; charset="utf-8"')
        eq(msg.get_payload(), 'hello there')

    def test_7bit_input(self):
        eq = self.assertEqual
        msg = MIMEText('hello there', _charset='us-ascii')
        eq(msg.get_charset().input_charset, 'us-ascii')
        eq(msg['content-type'], 'text/plain; charset="us-ascii"')

    def test_7bit_input_no_charset(self):
        eq = self.assertEqual
        msg = MIMEText('hello there')
        eq(msg.get_charset(), 'us-ascii')
        eq(msg['content-type'], 'text/plain; charset="us-ascii"')
        self.assertIn('hello there', msg.as_string())

    def test_utf8_input(self):
        teststr = 'кирилица'
        eq = self.assertEqual
        msg = MIMEText(teststr, _charset='utf-8')
        eq(msg.get_charset().output_charset, 'utf-8')
        eq(msg['content-type'], 'text/plain; charset="utf-8"')
        eq(msg.get_payload(decode=True), teststr.encode('utf-8'))

    @unittest.skip("can't fix because of backward compat in email5, will fix in email6")
    def test_utf8_input_no_charset(self):
        teststr = 'кирилица'
        self.assertRaises(UnicodeEncodeError, MIMEText, teststr)

class TestMultipart(TestEmailBase):

    def setUp(self):
        with openfile('PyBanner048.gif', 'rb') as fp:
            data = fp.read()
        container = MIMEBase('multipart', 'mixed', boundary='BOUNDARY')
        image = MIMEImage(data, name='dingusfish.gif')
        image.add_header('content-disposition', 'attachment', filename='dingusfish.gif')
        intro = MIMEText('Hi there,\n\nThis is the dingus fish.\n')
        container.attach(intro)
        container.attach(image)
        container['From'] = 'Barry <barry@digicool.com>'
        container['To'] = 'Dingus Lovers <cravindogs@cravindogs.com>'
        container['Subject'] = 'Here is your dingus fish'
        now = 987809702.548486
        timetuple = time.localtime(now)
        if (timetuple[(- 1)] == 0):
            tzsecs = time.timezone
        else:
            tzsecs = time.altzone
        if (tzsecs > 0):
            sign = '-'
        else:
            sign = '+'
        tzoffset = (' %s%04d' % (sign, (tzsecs / 36)))
        container['Date'] = (time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime(now)) + tzoffset)
        self._msg = container
        self._im = image
        self._txt = intro

    def test_hierarchy(self):
        eq = self.assertEqual
        raises = self.assertRaises
        m = self._msg
        self.assertTrue(m.is_multipart())
        eq(m.get_content_type(), 'multipart/mixed')
        eq(len(m.get_payload()), 2)
        raises(IndexError, m.get_payload, 2)
        m0 = m.get_payload(0)
        m1 = m.get_payload(1)
        self.assertIs(m0, self._txt)
        self.assertIs(m1, self._im)
        eq(m.get_payload(), [m0, m1])
        self.assertFalse(m0.is_multipart())
        self.assertFalse(m1.is_multipart())

    def test_empty_multipart_idempotent(self):
        text = 'Content-Type: multipart/mixed; boundary="BOUNDARY"\nMIME-Version: 1.0\nSubject: A subject\nTo: aperson@dom.ain\nFrom: bperson@dom.ain\n\n\n--BOUNDARY\n\n\n--BOUNDARY--\n'
        msg = Parser().parsestr(text)
        self.ndiffAssertEqual(text, msg.as_string())

    def test_no_parts_in_a_multipart_with_none_epilogue(self):
        outer = MIMEBase('multipart', 'mixed')
        outer['Subject'] = 'A subject'
        outer['To'] = 'aperson@dom.ain'
        outer['From'] = 'bperson@dom.ain'
        outer.set_boundary('BOUNDARY')
        self.ndiffAssertEqual(outer.as_string(), 'Content-Type: multipart/mixed; boundary="BOUNDARY"\nMIME-Version: 1.0\nSubject: A subject\nTo: aperson@dom.ain\nFrom: bperson@dom.ain\n\n--BOUNDARY\n\n--BOUNDARY--\n')

    def test_no_parts_in_a_multipart_with_empty_epilogue(self):
        outer = MIMEBase('multipart', 'mixed')
        outer['Subject'] = 'A subject'
        outer['To'] = 'aperson@dom.ain'
        outer['From'] = 'bperson@dom.ain'
        outer.preamble = ''
        outer.epilogue = ''
        outer.set_boundary('BOUNDARY')
        self.ndiffAssertEqual(outer.as_string(), 'Content-Type: multipart/mixed; boundary="BOUNDARY"\nMIME-Version: 1.0\nSubject: A subject\nTo: aperson@dom.ain\nFrom: bperson@dom.ain\n\n\n--BOUNDARY\n\n--BOUNDARY--\n')

    def test_one_part_in_a_multipart(self):
        eq = self.ndiffAssertEqual
        outer = MIMEBase('multipart', 'mixed')
        outer['Subject'] = 'A subject'
        outer['To'] = 'aperson@dom.ain'
        outer['From'] = 'bperson@dom.ain'
        outer.set_boundary('BOUNDARY')
        msg = MIMEText('hello world')
        outer.attach(msg)
        eq(outer.as_string(), 'Content-Type: multipart/mixed; boundary="BOUNDARY"\nMIME-Version: 1.0\nSubject: A subject\nTo: aperson@dom.ain\nFrom: bperson@dom.ain\n\n--BOUNDARY\nContent-Type: text/plain; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\n\nhello world\n--BOUNDARY--\n')

    def test_seq_parts_in_a_multipart_with_empty_preamble(self):
        eq = self.ndiffAssertEqual
        outer = MIMEBase('multipart', 'mixed')
        outer['Subject'] = 'A subject'
        outer['To'] = 'aperson@dom.ain'
        outer['From'] = 'bperson@dom.ain'
        outer.preamble = ''
        msg = MIMEText('hello world')
        outer.attach(msg)
        outer.set_boundary('BOUNDARY')
        eq(outer.as_string(), 'Content-Type: multipart/mixed; boundary="BOUNDARY"\nMIME-Version: 1.0\nSubject: A subject\nTo: aperson@dom.ain\nFrom: bperson@dom.ain\n\n\n--BOUNDARY\nContent-Type: text/plain; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\n\nhello world\n--BOUNDARY--\n')

    def test_seq_parts_in_a_multipart_with_none_preamble(self):
        eq = self.ndiffAssertEqual
        outer = MIMEBase('multipart', 'mixed')
        outer['Subject'] = 'A subject'
        outer['To'] = 'aperson@dom.ain'
        outer['From'] = 'bperson@dom.ain'
        outer.preamble = None
        msg = MIMEText('hello world')
        outer.attach(msg)
        outer.set_boundary('BOUNDARY')
        eq(outer.as_string(), 'Content-Type: multipart/mixed; boundary="BOUNDARY"\nMIME-Version: 1.0\nSubject: A subject\nTo: aperson@dom.ain\nFrom: bperson@dom.ain\n\n--BOUNDARY\nContent-Type: text/plain; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\n\nhello world\n--BOUNDARY--\n')

    def test_seq_parts_in_a_multipart_with_none_epilogue(self):
        eq = self.ndiffAssertEqual
        outer = MIMEBase('multipart', 'mixed')
        outer['Subject'] = 'A subject'
        outer['To'] = 'aperson@dom.ain'
        outer['From'] = 'bperson@dom.ain'
        outer.epilogue = None
        msg = MIMEText('hello world')
        outer.attach(msg)
        outer.set_boundary('BOUNDARY')
        eq(outer.as_string(), 'Content-Type: multipart/mixed; boundary="BOUNDARY"\nMIME-Version: 1.0\nSubject: A subject\nTo: aperson@dom.ain\nFrom: bperson@dom.ain\n\n--BOUNDARY\nContent-Type: text/plain; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\n\nhello world\n--BOUNDARY--\n')

    def test_seq_parts_in_a_multipart_with_empty_epilogue(self):
        eq = self.ndiffAssertEqual
        outer = MIMEBase('multipart', 'mixed')
        outer['Subject'] = 'A subject'
        outer['To'] = 'aperson@dom.ain'
        outer['From'] = 'bperson@dom.ain'
        outer.epilogue = ''
        msg = MIMEText('hello world')
        outer.attach(msg)
        outer.set_boundary('BOUNDARY')
        eq(outer.as_string(), 'Content-Type: multipart/mixed; boundary="BOUNDARY"\nMIME-Version: 1.0\nSubject: A subject\nTo: aperson@dom.ain\nFrom: bperson@dom.ain\n\n--BOUNDARY\nContent-Type: text/plain; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\n\nhello world\n--BOUNDARY--\n')

    def test_seq_parts_in_a_multipart_with_nl_epilogue(self):
        eq = self.ndiffAssertEqual
        outer = MIMEBase('multipart', 'mixed')
        outer['Subject'] = 'A subject'
        outer['To'] = 'aperson@dom.ain'
        outer['From'] = 'bperson@dom.ain'
        outer.epilogue = '\n'
        msg = MIMEText('hello world')
        outer.attach(msg)
        outer.set_boundary('BOUNDARY')
        eq(outer.as_string(), 'Content-Type: multipart/mixed; boundary="BOUNDARY"\nMIME-Version: 1.0\nSubject: A subject\nTo: aperson@dom.ain\nFrom: bperson@dom.ain\n\n--BOUNDARY\nContent-Type: text/plain; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\n\nhello world\n--BOUNDARY--\n\n')

    def test_message_external_body(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_36.txt')
        eq(len(msg.get_payload()), 2)
        msg1 = msg.get_payload(1)
        eq(msg1.get_content_type(), 'multipart/alternative')
        eq(len(msg1.get_payload()), 2)
        for subpart in msg1.get_payload():
            eq(subpart.get_content_type(), 'message/external-body')
            eq(len(subpart.get_payload()), 1)
            subsubpart = subpart.get_payload(0)
            eq(subsubpart.get_content_type(), 'text/plain')

    def test_double_boundary(self):
        msg = self._msgobj('msg_37.txt')
        self.assertEqual(len(msg.get_payload()), 3)

    def test_nested_inner_contains_outer_boundary(self):
        eq = self.ndiffAssertEqual
        msg = self._msgobj('msg_38.txt')
        sfp = StringIO()
        iterators._structure(msg, sfp)
        eq(sfp.getvalue(), 'multipart/mixed\n    multipart/mixed\n        multipart/alternative\n            text/plain\n        text/plain\n    text/plain\n    text/plain\n')

    def test_nested_with_same_boundary(self):
        eq = self.ndiffAssertEqual
        msg = self._msgobj('msg_39.txt')
        sfp = StringIO()
        iterators._structure(msg, sfp)
        eq(sfp.getvalue(), 'multipart/mixed\n    multipart/mixed\n        multipart/alternative\n        application/octet-stream\n        application/octet-stream\n    text/plain\n')

    def test_boundary_in_non_multipart(self):
        msg = self._msgobj('msg_40.txt')
        self.assertEqual(msg.as_string(), 'MIME-Version: 1.0\nContent-Type: text/html; boundary="--961284236552522269"\n\n----961284236552522269\nContent-Type: text/html;\nContent-Transfer-Encoding: 7Bit\n\n<html></html>\n\n----961284236552522269--\n')

    def test_boundary_with_leading_space(self):
        eq = self.assertEqual
        msg = email.message_from_string('MIME-Version: 1.0\nContent-Type: multipart/mixed; boundary="    XXXX"\n\n--    XXXX\nContent-Type: text/plain\n\n\n--    XXXX\nContent-Type: text/plain\n\n--    XXXX--\n')
        self.assertTrue(msg.is_multipart())
        eq(msg.get_boundary(), '    XXXX')
        eq(len(msg.get_payload()), 2)

    def test_boundary_without_trailing_newline(self):
        m = Parser().parsestr('Content-Type: multipart/mixed; boundary="===============0012394164=="\nMIME-Version: 1.0\n\n--===============0012394164==\nContent-Type: image/file1.jpg\nMIME-Version: 1.0\nContent-Transfer-Encoding: base64\n\nYXNkZg==\n--===============0012394164==--')
        self.assertEqual(m.get_payload(0).get_payload(), 'YXNkZg==')

    def test_mimebase_default_policy(self):
        m = MIMEBase('multipart', 'mixed')
        self.assertIs(m.policy, email.policy.compat32)

    def test_mimebase_custom_policy(self):
        m = MIMEBase('multipart', 'mixed', policy=email.policy.default)
        self.assertIs(m.policy, email.policy.default)

class TestNonConformant(TestEmailBase):

    def test_parse_missing_minor_type(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_14.txt')
        eq(msg.get_content_type(), 'text/plain')
        eq(msg.get_content_maintype(), 'text')
        eq(msg.get_content_subtype(), 'plain')

    def test_same_boundary_inner_outer(self):
        msg = self._msgobj('msg_15.txt')
        inner = msg.get_payload(0)
        self.assertTrue(hasattr(inner, 'defects'))
        self.assertEqual(len(inner.defects), 1)
        self.assertIsInstance(inner.defects[0], errors.StartBoundaryNotFoundDefect)

    def test_multipart_no_boundary(self):
        msg = self._msgobj('msg_25.txt')
        self.assertIsInstance(msg.get_payload(), str)
        self.assertEqual(len(msg.defects), 2)
        self.assertIsInstance(msg.defects[0], errors.NoBoundaryInMultipartDefect)
        self.assertIsInstance(msg.defects[1], errors.MultipartInvariantViolationDefect)
    multipart_msg = textwrap.dedent('        Date: Wed, 14 Nov 2007 12:56:23 GMT\n        From: foo@bar.invalid\n        To: foo@bar.invalid\n        Subject: Content-Transfer-Encoding: base64 and multipart\n        MIME-Version: 1.0\n        Content-Type: multipart/mixed;\n            boundary="===============3344438784458119861=="{}\n\n        --===============3344438784458119861==\n        Content-Type: text/plain\n\n        Test message\n\n        --===============3344438784458119861==\n        Content-Type: application/octet-stream\n        Content-Transfer-Encoding: base64\n\n        YWJj\n\n        --===============3344438784458119861==--\n        ')

    def test_multipart_invalid_cte(self):
        msg = self._str_msg(self.multipart_msg.format('\nContent-Transfer-Encoding: base64'))
        self.assertEqual(len(msg.defects), 1)
        self.assertIsInstance(msg.defects[0], errors.InvalidMultipartContentTransferEncodingDefect)

    def test_multipart_no_cte_no_defect(self):
        msg = self._str_msg(self.multipart_msg.format(''))
        self.assertEqual(len(msg.defects), 0)

    def test_multipart_valid_cte_no_defect(self):
        for cte in ('7bit', '8bit', 'BINary'):
            msg = self._str_msg(self.multipart_msg.format('\nContent-Transfer-Encoding: {}'.format(cte)))
            self.assertEqual(len(msg.defects), 0)

    def test_invalid_content_type(self):
        eq = self.assertEqual
        neq = self.ndiffAssertEqual
        msg = Message()
        msg['Content-Type'] = 'text'
        eq(msg.get_content_maintype(), 'text')
        eq(msg.get_content_subtype(), 'plain')
        eq(msg.get_content_type(), 'text/plain')
        del msg['content-type']
        msg['Content-Type'] = 'foo'
        eq(msg.get_content_maintype(), 'text')
        eq(msg.get_content_subtype(), 'plain')
        eq(msg.get_content_type(), 'text/plain')
        s = StringIO()
        g = Generator(s)
        g.flatten(msg)
        neq(s.getvalue(), 'Content-Type: foo\n\n')

    def test_no_start_boundary(self):
        eq = self.ndiffAssertEqual
        msg = self._msgobj('msg_31.txt')
        eq(msg.get_payload(), '--BOUNDARY\nContent-Type: text/plain\n\nmessage 1\n\n--BOUNDARY\nContent-Type: text/plain\n\nmessage 2\n\n--BOUNDARY--\n')

    def test_no_separating_blank_line(self):
        eq = self.ndiffAssertEqual
        msg = self._msgobj('msg_35.txt')
        eq(msg.as_string(), "From: aperson@dom.ain\nTo: bperson@dom.ain\nSubject: here's something interesting\n\ncounter to RFC 2822, there's no separating newline here\n")

    def test_lying_multipart(self):
        msg = self._msgobj('msg_41.txt')
        self.assertTrue(hasattr(msg, 'defects'))
        self.assertEqual(len(msg.defects), 2)
        self.assertIsInstance(msg.defects[0], errors.NoBoundaryInMultipartDefect)
        self.assertIsInstance(msg.defects[1], errors.MultipartInvariantViolationDefect)

    def test_missing_start_boundary(self):
        outer = self._msgobj('msg_42.txt')
        bad = outer.get_payload(1).get_payload(0)
        self.assertEqual(len(bad.defects), 1)
        self.assertIsInstance(bad.defects[0], errors.StartBoundaryNotFoundDefect)

    def test_first_line_is_continuation_header(self):
        eq = self.assertEqual
        m = ' Line 1\nSubject: test\n\nbody'
        msg = email.message_from_string(m)
        eq(msg.keys(), ['Subject'])
        eq(msg.get_payload(), 'body')
        eq(len(msg.defects), 1)
        self.assertDefectsEqual(msg.defects, [errors.FirstHeaderLineIsContinuationDefect])
        eq(msg.defects[0].line, ' Line 1\n')

    def test_missing_header_body_separator(self):
        msg = self._str_msg('Subject: test\nnot a header\nTo: abc\n\nb\n')
        self.assertEqual(msg.keys(), ['Subject'])
        self.assertEqual(msg.get_payload(), 'not a header\nTo: abc\n\nb\n')
        self.assertDefectsEqual(msg.defects, [errors.MissingHeaderBodySeparatorDefect])

class TestRFC2047(TestEmailBase):

    def test_rfc2047_multiline(self):
        eq = self.assertEqual
        s = 'Re: =?mac-iceland?q?r=8Aksm=9Arg=8Cs?= baz\n foo bar =?mac-iceland?q?r=8Aksm=9Arg=8Cs?='
        dh = decode_header(s)
        eq(dh, [(b'Re: ', None), (b'r\x8aksm\x9arg\x8cs', 'mac-iceland'), (b' baz foo bar ', None), (b'r\x8aksm\x9arg\x8cs', 'mac-iceland')])
        header = make_header(dh)
        eq(str(header), 'Re: räksmörgås baz foo bar räksmörgås')
        self.ndiffAssertEqual(header.encode(maxlinelen=76), 'Re: =?mac-iceland?q?r=8Aksm=9Arg=8Cs?= baz foo bar =?mac-iceland?q?r=8Aksm?=\n =?mac-iceland?q?=9Arg=8Cs?=')

    def test_whitespace_keeper_unicode(self):
        eq = self.assertEqual
        s = '=?ISO-8859-1?Q?Andr=E9?= Pirard <pirard@dom.ain>'
        dh = decode_header(s)
        eq(dh, [(b'Andr\xe9', 'iso-8859-1'), (b' Pirard <pirard@dom.ain>', None)])
        header = str(make_header(dh))
        eq(header, 'André Pirard <pirard@dom.ain>')

    def test_whitespace_keeper_unicode_2(self):
        eq = self.assertEqual
        s = 'The =?iso-8859-1?b?cXVpY2sgYnJvd24gZm94?= jumped over the =?iso-8859-1?b?bGF6eSBkb2c=?='
        dh = decode_header(s)
        eq(dh, [(b'The ', None), (b'quick brown fox', 'iso-8859-1'), (b' jumped over the ', None), (b'lazy dog', 'iso-8859-1')])
        hu = str(make_header(dh))
        eq(hu, 'The quick brown fox jumped over the lazy dog')

    def test_rfc2047_missing_whitespace(self):
        s = 'Sm=?ISO-8859-1?B?9g==?=rg=?ISO-8859-1?B?5Q==?=sbord'
        dh = decode_header(s)
        self.assertEqual(dh, [(b'Sm', None), (b'\xf6', 'iso-8859-1'), (b'rg', None), (b'\xe5', 'iso-8859-1'), (b'sbord', None)])

    def test_rfc2047_with_whitespace(self):
        s = 'Sm =?ISO-8859-1?B?9g==?= rg =?ISO-8859-1?B?5Q==?= sbord'
        dh = decode_header(s)
        self.assertEqual(dh, [(b'Sm ', None), (b'\xf6', 'iso-8859-1'), (b' rg ', None), (b'\xe5', 'iso-8859-1'), (b' sbord', None)])

    def test_rfc2047_B_bad_padding(self):
        s = '=?iso-8859-1?B?%s?='
        data = [('dm==', b'v'), ('dm=', b'v'), ('dm', b'v'), ('dmk=', b'vi'), ('dmk', b'vi')]
        for (q, a) in data:
            dh = decode_header((s % q))
            self.assertEqual(dh, [(a, 'iso-8859-1')])

    def test_rfc2047_Q_invalid_digits(self):
        s = '=?iso-8859-1?Q?andr=e9=zz?='
        self.assertEqual(decode_header(s), [(b'andr\xe9=zz', 'iso-8859-1')])

    def test_rfc2047_rfc2047_1(self):
        s = '(=?ISO-8859-1?Q?a?=)'
        self.assertEqual(decode_header(s), [(b'(', None), (b'a', 'iso-8859-1'), (b')', None)])

    def test_rfc2047_rfc2047_2(self):
        s = '(=?ISO-8859-1?Q?a?= b)'
        self.assertEqual(decode_header(s), [(b'(', None), (b'a', 'iso-8859-1'), (b' b)', None)])

    def test_rfc2047_rfc2047_3(self):
        s = '(=?ISO-8859-1?Q?a?= =?ISO-8859-1?Q?b?=)'
        self.assertEqual(decode_header(s), [(b'(', None), (b'ab', 'iso-8859-1'), (b')', None)])

    def test_rfc2047_rfc2047_4(self):
        s = '(=?ISO-8859-1?Q?a?=  =?ISO-8859-1?Q?b?=)'
        self.assertEqual(decode_header(s), [(b'(', None), (b'ab', 'iso-8859-1'), (b')', None)])

    def test_rfc2047_rfc2047_5a(self):
        s = '(=?ISO-8859-1?Q?a?=\r\n    =?ISO-8859-1?Q?b?=)'
        self.assertEqual(decode_header(s), [(b'(', None), (b'ab', 'iso-8859-1'), (b')', None)])

    def test_rfc2047_rfc2047_5b(self):
        s = '(=?ISO-8859-1?Q?a?=\n    =?ISO-8859-1?Q?b?=)'
        self.assertEqual(decode_header(s), [(b'(', None), (b'ab', 'iso-8859-1'), (b')', None)])

    def test_rfc2047_rfc2047_6(self):
        s = '(=?ISO-8859-1?Q?a_b?=)'
        self.assertEqual(decode_header(s), [(b'(', None), (b'a b', 'iso-8859-1'), (b')', None)])

    def test_rfc2047_rfc2047_7(self):
        s = '(=?ISO-8859-1?Q?a?= =?ISO-8859-2?Q?_b?=)'
        self.assertEqual(decode_header(s), [(b'(', None), (b'a', 'iso-8859-1'), (b' b', 'iso-8859-2'), (b')', None)])
        self.assertEqual(make_header(decode_header(s)).encode(), s.lower())
        self.assertEqual(str(make_header(decode_header(s))), '(a b)')

    def test_multiline_header(self):
        s = '=?windows-1252?q?=22M=FCller_T=22?=\r\n <T.Mueller@xxx.com>'
        self.assertEqual(decode_header(s), [(b'"M\xfcller T"', 'windows-1252'), (b'<T.Mueller@xxx.com>', None)])
        self.assertEqual(make_header(decode_header(s)).encode(), ''.join(s.splitlines()))
        self.assertEqual(str(make_header(decode_header(s))), '"Müller T" <T.Mueller@xxx.com>')

class TestMIMEMessage(TestEmailBase):

    def setUp(self):
        with openfile('msg_11.txt') as fp:
            self._text = fp.read()

    def test_type_error(self):
        self.assertRaises(TypeError, MIMEMessage, 'a plain string')

    def test_valid_argument(self):
        eq = self.assertEqual
        subject = 'A sub-message'
        m = Message()
        m['Subject'] = subject
        r = MIMEMessage(m)
        eq(r.get_content_type(), 'message/rfc822')
        payload = r.get_payload()
        self.assertIsInstance(payload, list)
        eq(len(payload), 1)
        subpart = payload[0]
        self.assertIs(subpart, m)
        eq(subpart['subject'], subject)

    def test_bad_multipart(self):
        msg1 = Message()
        msg1['Subject'] = 'subpart 1'
        msg2 = Message()
        msg2['Subject'] = 'subpart 2'
        r = MIMEMessage(msg1)
        self.assertRaises(errors.MultipartConversionError, r.attach, msg2)

    def test_generate(self):
        m = Message()
        m['Subject'] = 'An enclosed message'
        m.set_payload('Here is the body of the message.\n')
        r = MIMEMessage(m)
        r['Subject'] = 'The enclosing message'
        s = StringIO()
        g = Generator(s)
        g.flatten(r)
        self.assertEqual(s.getvalue(), 'Content-Type: message/rfc822\nMIME-Version: 1.0\nSubject: The enclosing message\n\nSubject: An enclosed message\n\nHere is the body of the message.\n')

    def test_parse_message_rfc822(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_11.txt')
        eq(msg.get_content_type(), 'message/rfc822')
        payload = msg.get_payload()
        self.assertIsInstance(payload, list)
        eq(len(payload), 1)
        submsg = payload[0]
        self.assertIsInstance(submsg, Message)
        eq(submsg['subject'], 'An enclosed message')
        eq(submsg.get_payload(), 'Here is the body of the message.\n')

    def test_dsn(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_16.txt')
        eq(msg.get_content_type(), 'multipart/report')
        self.assertTrue(msg.is_multipart())
        eq(len(msg.get_payload()), 3)
        subpart = msg.get_payload(0)
        eq(subpart.get_content_type(), 'text/plain')
        eq(subpart.get_payload(), 'This report relates to a message you sent with the following header fields:\n\n  Message-id: <002001c144a6$8752e060$56104586@oxy.edu>\n  Date: Sun, 23 Sep 2001 20:10:55 -0700\n  From: "Ian T. Henry" <henryi@oxy.edu>\n  To: SoCal Raves <scr@socal-raves.org>\n  Subject: [scr] yeah for Ians!!\n\nYour message cannot be delivered to the following recipients:\n\n  Recipient address: jangel1@cougar.noc.ucla.edu\n  Reason: recipient reached disk quota\n\n')
        subpart = msg.get_payload(1)
        eq(subpart.get_content_type(), 'message/delivery-status')
        eq(len(subpart.get_payload()), 2)
        dsn1 = subpart.get_payload(0)
        self.assertIsInstance(dsn1, Message)
        eq(dsn1['original-envelope-id'], '0GK500B4HD0888@cougar.noc.ucla.edu')
        eq(dsn1.get_param('dns', header='reporting-mta'), '')
        eq(dsn1.get_param('nsd', header='reporting-mta'), None)
        dsn2 = subpart.get_payload(1)
        self.assertIsInstance(dsn2, Message)
        eq(dsn2['action'], 'failed')
        eq(dsn2.get_params(header='original-recipient'), [('rfc822', ''), ('jangel1@cougar.noc.ucla.edu', '')])
        eq(dsn2.get_param('rfc822', header='final-recipient'), '')
        subpart = msg.get_payload(2)
        eq(subpart.get_content_type(), 'message/rfc822')
        payload = subpart.get_payload()
        self.assertIsInstance(payload, list)
        eq(len(payload), 1)
        subsubpart = payload[0]
        self.assertIsInstance(subsubpart, Message)
        eq(subsubpart.get_content_type(), 'text/plain')
        eq(subsubpart['message-id'], '<002001c144a6$8752e060$56104586@oxy.edu>')

    def test_epilogue(self):
        eq = self.ndiffAssertEqual
        with openfile('msg_21.txt') as fp:
            text = fp.read()
        msg = Message()
        msg['From'] = 'aperson@dom.ain'
        msg['To'] = 'bperson@dom.ain'
        msg['Subject'] = 'Test'
        msg.preamble = 'MIME message'
        msg.epilogue = 'End of MIME message\n'
        msg1 = MIMEText('One')
        msg2 = MIMEText('Two')
        msg.add_header('Content-Type', 'multipart/mixed', boundary='BOUNDARY')
        msg.attach(msg1)
        msg.attach(msg2)
        sfp = StringIO()
        g = Generator(sfp)
        g.flatten(msg)
        eq(sfp.getvalue(), text)

    def test_no_nl_preamble(self):
        eq = self.ndiffAssertEqual
        msg = Message()
        msg['From'] = 'aperson@dom.ain'
        msg['To'] = 'bperson@dom.ain'
        msg['Subject'] = 'Test'
        msg.preamble = 'MIME message'
        msg.epilogue = ''
        msg1 = MIMEText('One')
        msg2 = MIMEText('Two')
        msg.add_header('Content-Type', 'multipart/mixed', boundary='BOUNDARY')
        msg.attach(msg1)
        msg.attach(msg2)
        eq(msg.as_string(), 'From: aperson@dom.ain\nTo: bperson@dom.ain\nSubject: Test\nContent-Type: multipart/mixed; boundary="BOUNDARY"\n\nMIME message\n--BOUNDARY\nContent-Type: text/plain; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\n\nOne\n--BOUNDARY\nContent-Type: text/plain; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\n\nTwo\n--BOUNDARY--\n')

    def test_default_type(self):
        eq = self.assertEqual
        with openfile('msg_30.txt') as fp:
            msg = email.message_from_file(fp)
        container1 = msg.get_payload(0)
        eq(container1.get_default_type(), 'message/rfc822')
        eq(container1.get_content_type(), 'message/rfc822')
        container2 = msg.get_payload(1)
        eq(container2.get_default_type(), 'message/rfc822')
        eq(container2.get_content_type(), 'message/rfc822')
        container1a = container1.get_payload(0)
        eq(container1a.get_default_type(), 'text/plain')
        eq(container1a.get_content_type(), 'text/plain')
        container2a = container2.get_payload(0)
        eq(container2a.get_default_type(), 'text/plain')
        eq(container2a.get_content_type(), 'text/plain')

    def test_default_type_with_explicit_container_type(self):
        eq = self.assertEqual
        with openfile('msg_28.txt') as fp:
            msg = email.message_from_file(fp)
        container1 = msg.get_payload(0)
        eq(container1.get_default_type(), 'message/rfc822')
        eq(container1.get_content_type(), 'message/rfc822')
        container2 = msg.get_payload(1)
        eq(container2.get_default_type(), 'message/rfc822')
        eq(container2.get_content_type(), 'message/rfc822')
        container1a = container1.get_payload(0)
        eq(container1a.get_default_type(), 'text/plain')
        eq(container1a.get_content_type(), 'text/plain')
        container2a = container2.get_payload(0)
        eq(container2a.get_default_type(), 'text/plain')
        eq(container2a.get_content_type(), 'text/plain')

    def test_default_type_non_parsed(self):
        eq = self.assertEqual
        neq = self.ndiffAssertEqual
        container = MIMEMultipart('digest', 'BOUNDARY')
        container.epilogue = ''
        subpart1a = MIMEText('message 1\n')
        subpart2a = MIMEText('message 2\n')
        subpart1 = MIMEMessage(subpart1a)
        subpart2 = MIMEMessage(subpart2a)
        container.attach(subpart1)
        container.attach(subpart2)
        eq(subpart1.get_content_type(), 'message/rfc822')
        eq(subpart1.get_default_type(), 'message/rfc822')
        eq(subpart2.get_content_type(), 'message/rfc822')
        eq(subpart2.get_default_type(), 'message/rfc822')
        neq(container.as_string(0), 'Content-Type: multipart/digest; boundary="BOUNDARY"\nMIME-Version: 1.0\n\n--BOUNDARY\nContent-Type: message/rfc822\nMIME-Version: 1.0\n\nContent-Type: text/plain; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\n\nmessage 1\n\n--BOUNDARY\nContent-Type: message/rfc822\nMIME-Version: 1.0\n\nContent-Type: text/plain; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\n\nmessage 2\n\n--BOUNDARY--\n')
        del subpart1['content-type']
        del subpart1['mime-version']
        del subpart2['content-type']
        del subpart2['mime-version']
        eq(subpart1.get_content_type(), 'message/rfc822')
        eq(subpart1.get_default_type(), 'message/rfc822')
        eq(subpart2.get_content_type(), 'message/rfc822')
        eq(subpart2.get_default_type(), 'message/rfc822')
        neq(container.as_string(0), 'Content-Type: multipart/digest; boundary="BOUNDARY"\nMIME-Version: 1.0\n\n--BOUNDARY\n\nContent-Type: text/plain; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\n\nmessage 1\n\n--BOUNDARY\n\nContent-Type: text/plain; charset="us-ascii"\nMIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\n\nmessage 2\n\n--BOUNDARY--\n')

    def test_mime_attachments_in_constructor(self):
        eq = self.assertEqual
        text1 = MIMEText('')
        text2 = MIMEText('')
        msg = MIMEMultipart(_subparts=(text1, text2))
        eq(len(msg.get_payload()), 2)
        eq(msg.get_payload(0), text1)
        eq(msg.get_payload(1), text2)

    def test_default_multipart_constructor(self):
        msg = MIMEMultipart()
        self.assertTrue(msg.is_multipart())

    def test_multipart_default_policy(self):
        msg = MIMEMultipart()
        msg['To'] = 'a@b.com'
        msg['To'] = 'c@d.com'
        self.assertEqual(msg.get_all('to'), ['a@b.com', 'c@d.com'])

    def test_multipart_custom_policy(self):
        msg = MIMEMultipart(policy=email.policy.default)
        msg['To'] = 'a@b.com'
        with self.assertRaises(ValueError) as cm:
            msg['To'] = 'c@d.com'
        self.assertEqual(str(cm.exception), 'There may be at most 1 To headers in a message')

class TestIdempotent(TestEmailBase):
    linesep = '\n'

    def _msgobj(self, filename):
        with openfile(filename) as fp:
            data = fp.read()
        msg = email.message_from_string(data)
        return (msg, data)

    def _idempotent(self, msg, text, unixfrom=False):
        eq = self.ndiffAssertEqual
        s = StringIO()
        g = Generator(s, maxheaderlen=0)
        g.flatten(msg, unixfrom=unixfrom)
        eq(text, s.getvalue())

    def test_parse_text_message(self):
        eq = self.assertEqual
        (msg, text) = self._msgobj('msg_01.txt')
        eq(msg.get_content_type(), 'text/plain')
        eq(msg.get_content_maintype(), 'text')
        eq(msg.get_content_subtype(), 'plain')
        eq(msg.get_params()[1], ('charset', 'us-ascii'))
        eq(msg.get_param('charset'), 'us-ascii')
        eq(msg.preamble, None)
        eq(msg.epilogue, None)
        self._idempotent(msg, text)

    def test_parse_untyped_message(self):
        eq = self.assertEqual
        (msg, text) = self._msgobj('msg_03.txt')
        eq(msg.get_content_type(), 'text/plain')
        eq(msg.get_params(), None)
        eq(msg.get_param('charset'), None)
        self._idempotent(msg, text)

    def test_simple_multipart(self):
        (msg, text) = self._msgobj('msg_04.txt')
        self._idempotent(msg, text)

    def test_MIME_digest(self):
        (msg, text) = self._msgobj('msg_02.txt')
        self._idempotent(msg, text)

    def test_long_header(self):
        (msg, text) = self._msgobj('msg_27.txt')
        self._idempotent(msg, text)

    def test_MIME_digest_with_part_headers(self):
        (msg, text) = self._msgobj('msg_28.txt')
        self._idempotent(msg, text)

    def test_mixed_with_image(self):
        (msg, text) = self._msgobj('msg_06.txt')
        self._idempotent(msg, text)

    def test_multipart_report(self):
        (msg, text) = self._msgobj('msg_05.txt')
        self._idempotent(msg, text)

    def test_dsn(self):
        (msg, text) = self._msgobj('msg_16.txt')
        self._idempotent(msg, text)

    def test_preamble_epilogue(self):
        (msg, text) = self._msgobj('msg_21.txt')
        self._idempotent(msg, text)

    def test_multipart_one_part(self):
        (msg, text) = self._msgobj('msg_23.txt')
        self._idempotent(msg, text)

    def test_multipart_no_parts(self):
        (msg, text) = self._msgobj('msg_24.txt')
        self._idempotent(msg, text)

    def test_no_start_boundary(self):
        (msg, text) = self._msgobj('msg_31.txt')
        self._idempotent(msg, text)

    def test_rfc2231_charset(self):
        (msg, text) = self._msgobj('msg_32.txt')
        self._idempotent(msg, text)

    def test_more_rfc2231_parameters(self):
        (msg, text) = self._msgobj('msg_33.txt')
        self._idempotent(msg, text)

    def test_text_plain_in_a_multipart_digest(self):
        (msg, text) = self._msgobj('msg_34.txt')
        self._idempotent(msg, text)

    def test_nested_multipart_mixeds(self):
        (msg, text) = self._msgobj('msg_12a.txt')
        self._idempotent(msg, text)

    def test_message_external_body_idempotent(self):
        (msg, text) = self._msgobj('msg_36.txt')
        self._idempotent(msg, text)

    def test_message_delivery_status(self):
        (msg, text) = self._msgobj('msg_43.txt')
        self._idempotent(msg, text, unixfrom=True)

    def test_message_signed_idempotent(self):
        (msg, text) = self._msgobj('msg_45.txt')
        self._idempotent(msg, text)

    def test_content_type(self):
        eq = self.assertEqual
        (msg, text) = self._msgobj('msg_05.txt')
        eq(msg.get_content_type(), 'multipart/report')
        params = {}
        for (pk, pv) in msg.get_params():
            params[pk] = pv
        eq(params['report-type'], 'delivery-status')
        eq(params['boundary'], 'D1690A7AC1.996856090/mail.example.com')
        eq(msg.preamble, ('This is a MIME-encapsulated message.' + self.linesep))
        eq(msg.epilogue, self.linesep)
        eq(len(msg.get_payload()), 3)
        msg1 = msg.get_payload(0)
        eq(msg1.get_content_type(), 'text/plain')
        eq(msg1.get_payload(), ('Yadda yadda yadda' + self.linesep))
        msg2 = msg.get_payload(1)
        eq(msg2.get_content_type(), 'text/plain')
        eq(msg2.get_payload(), ('Yadda yadda yadda' + self.linesep))
        msg3 = msg.get_payload(2)
        eq(msg3.get_content_type(), 'message/rfc822')
        self.assertIsInstance(msg3, Message)
        payload = msg3.get_payload()
        self.assertIsInstance(payload, list)
        eq(len(payload), 1)
        msg4 = payload[0]
        self.assertIsInstance(msg4, Message)
        eq(msg4.get_payload(), ('Yadda yadda yadda' + self.linesep))

    def test_parser(self):
        eq = self.assertEqual
        (msg, text) = self._msgobj('msg_06.txt')
        eq(msg.get_content_type(), 'message/rfc822')
        payload = msg.get_payload()
        self.assertIsInstance(payload, list)
        eq(len(payload), 1)
        msg1 = payload[0]
        self.assertIsInstance(msg1, Message)
        eq(msg1.get_content_type(), 'text/plain')
        self.assertIsInstance(msg1.get_payload(), str)
        eq(msg1.get_payload(), self.linesep)

class TestMiscellaneous(TestEmailBase):

    def test_message_from_string(self):
        with openfile('msg_01.txt') as fp:
            text = fp.read()
        msg = email.message_from_string(text)
        s = StringIO()
        g = Generator(s, maxheaderlen=0)
        g.flatten(msg)
        self.assertEqual(text, s.getvalue())

    def test_message_from_file(self):
        with openfile('msg_01.txt') as fp:
            text = fp.read()
            fp.seek(0)
            msg = email.message_from_file(fp)
            s = StringIO()
            g = Generator(s, maxheaderlen=0)
            g.flatten(msg)
            self.assertEqual(text, s.getvalue())

    def test_message_from_string_with_class(self):
        with openfile('msg_01.txt') as fp:
            text = fp.read()

        class MyMessage(Message):
            pass
        msg = email.message_from_string(text, MyMessage)
        self.assertIsInstance(msg, MyMessage)
        with openfile('msg_02.txt') as fp:
            text = fp.read()
        msg = email.message_from_string(text, MyMessage)
        for subpart in msg.walk():
            self.assertIsInstance(subpart, MyMessage)

    def test_message_from_file_with_class(self):

        class MyMessage(Message):
            pass
        with openfile('msg_01.txt') as fp:
            msg = email.message_from_file(fp, MyMessage)
        self.assertIsInstance(msg, MyMessage)
        with openfile('msg_02.txt') as fp:
            msg = email.message_from_file(fp, MyMessage)
        for subpart in msg.walk():
            self.assertIsInstance(subpart, MyMessage)

    def test_custom_message_does_not_require_arguments(self):

        class MyMessage(Message):

            def __init__(self):
                super().__init__()
        msg = self._str_msg('Subject: test\n\ntest', MyMessage)
        self.assertIsInstance(msg, MyMessage)

    def test__all__(self):
        module = __import__('email')
        self.assertEqual(sorted(module.__all__), ['base64mime', 'charset', 'encoders', 'errors', 'feedparser', 'generator', 'header', 'iterators', 'message', 'message_from_binary_file', 'message_from_bytes', 'message_from_file', 'message_from_string', 'mime', 'parser', 'quoprimime', 'utils'])

    def test_formatdate(self):
        now = time.time()
        self.assertEqual(utils.parsedate(utils.formatdate(now))[:6], time.gmtime(now)[:6])

    def test_formatdate_localtime(self):
        now = time.time()
        self.assertEqual(utils.parsedate(utils.formatdate(now, localtime=True))[:6], time.localtime(now)[:6])

    def test_formatdate_usegmt(self):
        now = time.time()
        self.assertEqual(utils.formatdate(now, localtime=False), time.strftime('%a, %d %b %Y %H:%M:%S -0000', time.gmtime(now)))
        self.assertEqual(utils.formatdate(now, localtime=False, usegmt=True), time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(now)))

    def test_parsedate_returns_None_for_invalid_strings(self):
        self.assertIsNone(utils.parsedate(''))
        self.assertIsNone(utils.parsedate_tz(''))
        self.assertIsNone(utils.parsedate('0'))
        self.assertIsNone(utils.parsedate_tz('0'))
        self.assertIsNone(utils.parsedate('A Complete Waste of Time'))
        self.assertIsNone(utils.parsedate_tz('A Complete Waste of Time'))
        self.assertIsNone(utils.parsedate(None))
        self.assertIsNone(utils.parsedate_tz(None))

    def test_parsedate_compact(self):
        self.assertEqual(utils.parsedate('Wed,3 Apr 2002 14:58:26 +0800'), utils.parsedate('Wed, 3 Apr 2002 14:58:26 +0800'))

    def test_parsedate_no_dayofweek(self):
        eq = self.assertEqual
        eq(utils.parsedate_tz('25 Feb 2003 13:47:26 -0800'), (2003, 2, 25, 13, 47, 26, 0, 1, (- 1), (- 28800)))

    def test_parsedate_compact_no_dayofweek(self):
        eq = self.assertEqual
        eq(utils.parsedate_tz('5 Feb 2003 13:47:26 -0800'), (2003, 2, 5, 13, 47, 26, 0, 1, (- 1), (- 28800)))

    def test_parsedate_no_space_before_positive_offset(self):
        self.assertEqual(utils.parsedate_tz('Wed, 3 Apr 2002 14:58:26+0800'), (2002, 4, 3, 14, 58, 26, 0, 1, (- 1), 28800))

    def test_parsedate_no_space_before_negative_offset(self):
        self.assertEqual(utils.parsedate_tz('Wed, 3 Apr 2002 14:58:26-0800'), (2002, 4, 3, 14, 58, 26, 0, 1, (- 1), (- 28800)))

    def test_parsedate_accepts_time_with_dots(self):
        eq = self.assertEqual
        eq(utils.parsedate_tz('5 Feb 2003 13.47.26 -0800'), (2003, 2, 5, 13, 47, 26, 0, 1, (- 1), (- 28800)))
        eq(utils.parsedate_tz('5 Feb 2003 13.47 -0800'), (2003, 2, 5, 13, 47, 0, 0, 1, (- 1), (- 28800)))

    def test_parsedate_acceptable_to_time_functions(self):
        eq = self.assertEqual
        timetup = utils.parsedate('5 Feb 2003 13:47:26 -0800')
        t = int(time.mktime(timetup))
        eq(time.localtime(t)[:6], timetup[:6])
        eq(int(time.strftime('%Y', timetup)), 2003)
        timetup = utils.parsedate_tz('5 Feb 2003 13:47:26 -0800')
        t = int(time.mktime(timetup[:9]))
        eq(time.localtime(t)[:6], timetup[:6])
        eq(int(time.strftime('%Y', timetup[:9])), 2003)

    def test_mktime_tz(self):
        self.assertEqual(utils.mktime_tz((1970, 1, 1, 0, 0, 0, (- 1), (- 1), (- 1), 0)), 0)
        self.assertEqual(utils.mktime_tz((1970, 1, 1, 0, 0, 0, (- 1), (- 1), (- 1), 1234)), (- 1234))

    def test_parsedate_y2k(self):
        'Test for parsing a date with a two-digit year.\n\n        Parsing a date with a two-digit year should return the correct\n        four-digit year. RFC822 allows two-digit years, but RFC2822 (which\n        obsoletes RFC822) requires four-digit years.\n\n        '
        self.assertEqual(utils.parsedate_tz('25 Feb 03 13:47:26 -0800'), utils.parsedate_tz('25 Feb 2003 13:47:26 -0800'))
        self.assertEqual(utils.parsedate_tz('25 Feb 71 13:47:26 -0800'), utils.parsedate_tz('25 Feb 1971 13:47:26 -0800'))

    def test_parseaddr_empty(self):
        self.assertEqual(utils.parseaddr('<>'), ('', ''))
        self.assertEqual(utils.formataddr(utils.parseaddr('<>')), '')

    def test_parseaddr_multiple_domains(self):
        self.assertEqual(utils.parseaddr('a@b@c'), ('', ''))
        self.assertEqual(utils.parseaddr('a@b.c@c'), ('', ''))
        self.assertEqual(utils.parseaddr('a@172.17.0.1@c'), ('', ''))

    def test_noquote_dump(self):
        self.assertEqual(utils.formataddr(('A Silly Person', 'person@dom.ain')), 'A Silly Person <person@dom.ain>')

    def test_escape_dump(self):
        self.assertEqual(utils.formataddr(('A (Very) Silly Person', 'person@dom.ain')), '"A (Very) Silly Person" <person@dom.ain>')
        self.assertEqual(utils.parseaddr('"A \\(Very\\) Silly Person" <person@dom.ain>'), ('A (Very) Silly Person', 'person@dom.ain'))
        a = 'A \\(Special\\) Person'
        b = 'person@dom.ain'
        self.assertEqual(utils.parseaddr(utils.formataddr((a, b))), (a, b))

    def test_escape_backslashes(self):
        self.assertEqual(utils.formataddr(('Arthur \\Backslash\\ Foobar', 'person@dom.ain')), '"Arthur \\\\Backslash\\\\ Foobar" <person@dom.ain>')
        a = 'Arthur \\Backslash\\ Foobar'
        b = 'person@dom.ain'
        self.assertEqual(utils.parseaddr(utils.formataddr((a, b))), (a, b))

    def test_quotes_unicode_names(self):
        name = 'Häns Würst'
        addr = 'person@dom.ain'
        utf8_base64 = '=?utf-8?b?SMOkbnMgV8O8cnN0?= <person@dom.ain>'
        latin1_quopri = '=?iso-8859-1?q?H=E4ns_W=FCrst?= <person@dom.ain>'
        self.assertEqual(utils.formataddr((name, addr)), utf8_base64)
        self.assertEqual(utils.formataddr((name, addr), 'iso-8859-1'), latin1_quopri)

    def test_accepts_any_charset_like_object(self):
        name = 'Häns Würst'
        addr = 'person@dom.ain'
        utf8_base64 = '=?utf-8?b?SMOkbnMgV8O8cnN0?= <person@dom.ain>'
        foobar = 'FOOBAR'

        class CharsetMock():

            def header_encode(self, string):
                return foobar
        mock = CharsetMock()
        mock_expected = ('%s <%s>' % (foobar, addr))
        self.assertEqual(utils.formataddr((name, addr), mock), mock_expected)
        self.assertEqual(utils.formataddr((name, addr), Charset('utf-8')), utf8_base64)

    def test_invalid_charset_like_object_raises_error(self):
        name = 'Häns Würst'
        addr = 'person@dom.ain'
        bad_charset = object()
        self.assertRaises(AttributeError, utils.formataddr, (name, addr), bad_charset)

    def test_unicode_address_raises_error(self):
        addr = 'persön@dom.in'
        self.assertRaises(UnicodeError, utils.formataddr, (None, addr))
        self.assertRaises(UnicodeError, utils.formataddr, ('Name', addr))

    def test_name_with_dot(self):
        x = 'John X. Doe <jxd@example.com>'
        y = '"John X. Doe" <jxd@example.com>'
        (a, b) = ('John X. Doe', 'jxd@example.com')
        self.assertEqual(utils.parseaddr(x), (a, b))
        self.assertEqual(utils.parseaddr(y), (a, b))
        self.assertEqual(utils.formataddr((a, b)), y)

    def test_parseaddr_preserves_quoted_pairs_in_addresses(self):
        eq = self.assertEqual
        eq(utils.parseaddr('""example" example"@example.com'), ('', '""example" example"@example.com'))
        eq(utils.parseaddr('"\\"example\\" example"@example.com'), ('', '"\\"example\\" example"@example.com'))
        eq(utils.parseaddr('"\\\\"example\\\\" example"@example.com'), ('', '"\\\\"example\\\\" example"@example.com'))

    def test_parseaddr_preserves_spaces_in_local_part(self):
        self.assertEqual(('', 'merwok wok@xample.com'), utils.parseaddr('merwok wok@xample.com'))
        self.assertEqual(('', 'merwok  wok@xample.com'), utils.parseaddr('merwok  wok@xample.com'))
        self.assertEqual(('', 'merwok  wok@xample.com'), utils.parseaddr(' merwok  wok  @xample.com'))
        self.assertEqual(('', 'merwok"wok"  wok@xample.com'), utils.parseaddr('merwok"wok"  wok@xample.com'))
        self.assertEqual(('', 'merwok.wok.wok@xample.com'), utils.parseaddr('merwok. wok .  wok@xample.com'))

    def test_formataddr_does_not_quote_parens_in_quoted_string(self):
        addr = ("'foo@example.com' (foo@example.com)", 'foo@example.com')
        addrstr = '"\'foo@example.com\' (foo@example.com)" <foo@example.com>'
        self.assertEqual(utils.parseaddr(addrstr), addr)
        self.assertEqual(utils.formataddr(addr), addrstr)

    def test_multiline_from_comment(self):
        x = 'Foo\n\tBar <foo@example.com>'
        self.assertEqual(utils.parseaddr(x), ('Foo Bar', 'foo@example.com'))

    def test_quote_dump(self):
        self.assertEqual(utils.formataddr(('A Silly; Person', 'person@dom.ain')), '"A Silly; Person" <person@dom.ain>')

    def test_charset_richcomparisons(self):
        eq = self.assertEqual
        ne = self.assertNotEqual
        cset1 = Charset()
        cset2 = Charset()
        eq(cset1, 'us-ascii')
        eq(cset1, 'US-ASCII')
        eq(cset1, 'Us-AsCiI')
        eq('us-ascii', cset1)
        eq('US-ASCII', cset1)
        eq('Us-AsCiI', cset1)
        ne(cset1, 'usascii')
        ne(cset1, 'USASCII')
        ne(cset1, 'UsAsCiI')
        ne('usascii', cset1)
        ne('USASCII', cset1)
        ne('UsAsCiI', cset1)
        eq(cset1, cset2)
        eq(cset2, cset1)

    def test_getaddresses(self):
        eq = self.assertEqual
        eq(utils.getaddresses(['aperson@dom.ain (Al Person)', 'Bud Person <bperson@dom.ain>']), [('Al Person', 'aperson@dom.ain'), ('Bud Person', 'bperson@dom.ain')])

    def test_getaddresses_nasty(self):
        eq = self.assertEqual
        eq(utils.getaddresses(['foo: ;']), [('', '')])
        eq(utils.getaddresses(['[]*-- =~$']), [('', ''), ('', ''), ('', '*--')])
        eq(utils.getaddresses(['foo: ;', '"Jason R. Mastaler" <jason@dom.ain>']), [('', ''), ('Jason R. Mastaler', 'jason@dom.ain')])

    def test_getaddresses_embedded_comment(self):
        'Test proper handling of a nested comment'
        eq = self.assertEqual
        addrs = utils.getaddresses(['User ((nested comment)) <foo@bar.com>'])
        eq(addrs[0][1], 'foo@bar.com')

    def test_make_msgid_collisions(self):

        class MsgidsThread(Thread):

            def run(self):
                self.msgids = []
                append = self.msgids.append
                make_msgid = utils.make_msgid
                clock = time.monotonic
                tfin = (clock() + 3.0)
                while (clock() < tfin):
                    append(make_msgid(domain='testdomain-string'))
        threads = [MsgidsThread() for i in range(5)]
        with threading_helper.start_threads(threads):
            pass
        all_ids = sum([t.msgids for t in threads], [])
        self.assertEqual(len(set(all_ids)), len(all_ids))

    def test_utils_quote_unquote(self):
        eq = self.assertEqual
        msg = Message()
        msg.add_header('content-disposition', 'attachment', filename='foo\\wacky"name')
        eq(msg.get_filename(), 'foo\\wacky"name')

    def test_get_body_encoding_with_bogus_charset(self):
        charset = Charset('not a charset')
        self.assertEqual(charset.get_body_encoding(), 'base64')

    def test_get_body_encoding_with_uppercase_charset(self):
        eq = self.assertEqual
        msg = Message()
        msg['Content-Type'] = 'text/plain; charset=UTF-8'
        eq(msg['content-type'], 'text/plain; charset=UTF-8')
        charsets = msg.get_charsets()
        eq(len(charsets), 1)
        eq(charsets[0], 'utf-8')
        charset = Charset(charsets[0])
        eq(charset.get_body_encoding(), 'base64')
        msg.set_payload(b'hello world', charset=charset)
        eq(msg.get_payload(), 'aGVsbG8gd29ybGQ=\n')
        eq(msg.get_payload(decode=True), b'hello world')
        eq(msg['content-transfer-encoding'], 'base64')
        msg = Message()
        msg['Content-Type'] = 'text/plain; charset="US-ASCII"'
        charsets = msg.get_charsets()
        eq(len(charsets), 1)
        eq(charsets[0], 'us-ascii')
        charset = Charset(charsets[0])
        eq(charset.get_body_encoding(), encoders.encode_7or8bit)
        msg.set_payload('hello world', charset=charset)
        eq(msg.get_payload(), 'hello world')
        eq(msg['content-transfer-encoding'], '7bit')

    def test_charsets_case_insensitive(self):
        lc = Charset('us-ascii')
        uc = Charset('US-ASCII')
        self.assertEqual(lc.get_body_encoding(), uc.get_body_encoding())

    def test_partial_falls_inside_message_delivery_status(self):
        eq = self.ndiffAssertEqual
        msg = self._msgobj('msg_43.txt')
        sfp = StringIO()
        iterators._structure(msg, sfp)
        eq(sfp.getvalue(), 'multipart/report\n    text/plain\n    message/delivery-status\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n        text/plain\n    text/rfc822-headers\n')

    def test_make_msgid_domain(self):
        self.assertEqual(email.utils.make_msgid(domain='testdomain-string')[(- 19):], '@testdomain-string>')

    def test_make_msgid_idstring(self):
        self.assertEqual(email.utils.make_msgid(idstring='test-idstring', domain='testdomain-string')[(- 33):], '.test-idstring@testdomain-string>')

    def test_make_msgid_default_domain(self):
        with patch('socket.getfqdn') as mock_getfqdn:
            mock_getfqdn.return_value = domain = 'pythontest.example.com'
            self.assertTrue(email.utils.make_msgid().endswith((('@' + domain) + '>')))

    def test_Generator_linend(self):
        with openfile('msg_26.txt', newline='\n') as f:
            msgtxt = f.read()
        msgtxt_nl = msgtxt.replace('\r\n', '\n')
        msg = email.message_from_string(msgtxt)
        s = StringIO()
        g = email.generator.Generator(s)
        g.flatten(msg)
        self.assertEqual(s.getvalue(), msgtxt_nl)

    def test_BytesGenerator_linend(self):
        with openfile('msg_26.txt', newline='\n') as f:
            msgtxt = f.read()
        msgtxt_nl = msgtxt.replace('\r\n', '\n')
        msg = email.message_from_string(msgtxt_nl)
        s = BytesIO()
        g = email.generator.BytesGenerator(s)
        g.flatten(msg, linesep='\r\n')
        self.assertEqual(s.getvalue().decode('ascii'), msgtxt)

    def test_BytesGenerator_linend_with_non_ascii(self):
        with openfile('msg_26.txt', 'rb') as f:
            msgtxt = f.read()
        msgtxt = msgtxt.replace(b'with attachment', b'fo\xf6')
        msgtxt_nl = msgtxt.replace(b'\r\n', b'\n')
        msg = email.message_from_bytes(msgtxt_nl)
        s = BytesIO()
        g = email.generator.BytesGenerator(s)
        g.flatten(msg, linesep='\r\n')
        self.assertEqual(s.getvalue(), msgtxt)

    def test_mime_classes_policy_argument(self):
        with openfile('audiotest.au', 'rb') as fp:
            audiodata = fp.read()
        with openfile('PyBanner048.gif', 'rb') as fp:
            bindata = fp.read()
        classes = [(MIMEApplication, ('',)), (MIMEAudio, (audiodata,)), (MIMEImage, (bindata,)), (MIMEMessage, (Message(),)), (MIMENonMultipart, ('multipart', 'mixed')), (MIMEText, ('',))]
        for (cls, constructor) in classes:
            with self.subTest(cls=cls.__name__, policy='compat32'):
                m = cls(*constructor)
                self.assertIs(m.policy, email.policy.compat32)
            with self.subTest(cls=cls.__name__, policy='default'):
                m = cls(*constructor, policy=email.policy.default)
                self.assertIs(m.policy, email.policy.default)

class TestIterators(TestEmailBase):

    def test_body_line_iterator(self):
        eq = self.assertEqual
        neq = self.ndiffAssertEqual
        msg = self._msgobj('msg_01.txt')
        it = iterators.body_line_iterator(msg)
        lines = list(it)
        eq(len(lines), 6)
        neq(EMPTYSTRING.join(lines), msg.get_payload())
        msg = self._msgobj('msg_02.txt')
        it = iterators.body_line_iterator(msg)
        lines = list(it)
        eq(len(lines), 43)
        with openfile('msg_19.txt') as fp:
            neq(EMPTYSTRING.join(lines), fp.read())

    def test_typed_subpart_iterator(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_04.txt')
        it = iterators.typed_subpart_iterator(msg, 'text')
        lines = []
        subparts = 0
        for subpart in it:
            subparts += 1
            lines.append(subpart.get_payload())
        eq(subparts, 2)
        eq(EMPTYSTRING.join(lines), 'a simple kind of mirror\nto reflect upon our own\na simple kind of mirror\nto reflect upon our own\n')

    def test_typed_subpart_iterator_default_type(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_03.txt')
        it = iterators.typed_subpart_iterator(msg, 'text', 'plain')
        lines = []
        subparts = 0
        for subpart in it:
            subparts += 1
            lines.append(subpart.get_payload())
        eq(subparts, 1)
        eq(EMPTYSTRING.join(lines), '\nHi,\n\nDo you like this message?\n\n-Me\n')

    def test_pushCR_LF(self):
        'FeedParser BufferedSubFile.push() assumed it received complete\n           line endings.  A CR ending one push() followed by a LF starting\n           the next push() added an empty line.\n        '
        imt = [('a\r \n', 2), ('b', 0), ('c\n', 1), ('', 0), ('d\r\n', 1), ('e\r', 0), ('\nf', 1), ('\r\n', 1)]
        from email.feedparser import BufferedSubFile, NeedMoreData
        bsf = BufferedSubFile()
        om = []
        nt = 0
        for (il, n) in imt:
            bsf.push(il)
            nt += n
            n1 = 0
            for ol in iter(bsf.readline, NeedMoreData):
                om.append(ol)
                n1 += 1
            self.assertEqual(n, n1)
        self.assertEqual(len(om), nt)
        self.assertEqual(''.join([il for (il, n) in imt]), ''.join(om))

    def test_push_random(self):
        from email.feedparser import BufferedSubFile, NeedMoreData
        n = 10000
        chunksize = 5
        chars = 'abcd \t\r\n'
        s = (''.join((choice(chars) for i in range(n))) + '\n')
        target = s.splitlines(True)
        bsf = BufferedSubFile()
        lines = []
        for i in range(0, len(s), chunksize):
            chunk = s[i:(i + chunksize)]
            bsf.push(chunk)
            lines.extend(iter(bsf.readline, NeedMoreData))
        self.assertEqual(lines, target)

class TestFeedParsers(TestEmailBase):

    def parse(self, chunks):
        feedparser = FeedParser()
        for chunk in chunks:
            feedparser.feed(chunk)
        return feedparser.close()

    def test_empty_header_name_handled(self):
        msg = self.parse('First: val\n: bad\nSecond: val')
        self.assertEqual(msg['First'], 'val')
        self.assertEqual(msg['Second'], 'val')

    def test_newlines(self):
        m = self.parse(['a:\nb:\rc:\r\nd:\n'])
        self.assertEqual(m.keys(), ['a', 'b', 'c', 'd'])
        m = self.parse(['a:\nb:\rc:\r\nd:'])
        self.assertEqual(m.keys(), ['a', 'b', 'c', 'd'])
        m = self.parse(['a:\rb', 'c:\n'])
        self.assertEqual(m.keys(), ['a', 'bc'])
        m = self.parse(['a:\r', 'b:\n'])
        self.assertEqual(m.keys(), ['a', 'b'])
        m = self.parse(['a:\r', '\nb:\n'])
        self.assertEqual(m.keys(), ['a', 'b'])
        m = self.parse(['a:\x85b:\u2028c:\n'])
        self.assertEqual(m.items(), [('a', '\x85b:\u2028c:')])
        m = self.parse(['a:\r', 'b:\x85', 'c:\n'])
        self.assertEqual(m.items(), [('a', ''), ('b', '\x85c:')])

    def test_long_lines(self):
        (M, N) = (1000, 20000)
        m = self.parse((['a:b\n\n'] + ([('x' * M)] * N)))
        self.assertEqual(m.items(), [('a', 'b')])
        self.assertEqual(m.get_payload(), (('x' * M) * N))
        m = self.parse((['a:b\r\r'] + ([('x' * M)] * N)))
        self.assertEqual(m.items(), [('a', 'b')])
        self.assertEqual(m.get_payload(), (('x' * M) * N))
        m = self.parse((['a:b\r\r'] + ([(('x' * M) + '\x85')] * N)))
        self.assertEqual(m.items(), [('a', 'b')])
        self.assertEqual(m.get_payload(), ((('x' * M) + '\x85') * N))
        m = self.parse((['a:\r', 'b: '] + ([('x' * M)] * N)))
        self.assertEqual(m.items(), [('a', ''), ('b', (('x' * M) * N))])

class TestParsers(TestEmailBase):

    def test_header_parser(self):
        eq = self.assertEqual
        with openfile('msg_02.txt') as fp:
            msg = HeaderParser().parse(fp)
        eq(msg['from'], 'ppp-request@zzz.org')
        eq(msg['to'], 'ppp@zzz.org')
        eq(msg.get_content_type(), 'multipart/mixed')
        self.assertFalse(msg.is_multipart())
        self.assertIsInstance(msg.get_payload(), str)

    def test_bytes_header_parser(self):
        eq = self.assertEqual
        with openfile('msg_02.txt', 'rb') as fp:
            msg = email.parser.BytesHeaderParser().parse(fp)
        eq(msg['from'], 'ppp-request@zzz.org')
        eq(msg['to'], 'ppp@zzz.org')
        eq(msg.get_content_type(), 'multipart/mixed')
        self.assertFalse(msg.is_multipart())
        self.assertIsInstance(msg.get_payload(), str)
        self.assertIsInstance(msg.get_payload(decode=True), bytes)

    def test_bytes_parser_does_not_close_file(self):
        with openfile('msg_02.txt', 'rb') as fp:
            email.parser.BytesParser().parse(fp)
            self.assertFalse(fp.closed)

    def test_bytes_parser_on_exception_does_not_close_file(self):
        with openfile('msg_15.txt', 'rb') as fp:
            bytesParser = email.parser.BytesParser
            self.assertRaises(email.errors.StartBoundaryNotFoundDefect, bytesParser(policy=email.policy.strict).parse, fp)
            self.assertFalse(fp.closed)

    def test_parser_does_not_close_file(self):
        with openfile('msg_02.txt', 'r') as fp:
            email.parser.Parser().parse(fp)
            self.assertFalse(fp.closed)

    def test_parser_on_exception_does_not_close_file(self):
        with openfile('msg_15.txt', 'r') as fp:
            parser = email.parser.Parser
            self.assertRaises(email.errors.StartBoundaryNotFoundDefect, parser(policy=email.policy.strict).parse, fp)
            self.assertFalse(fp.closed)

    def test_whitespace_continuation(self):
        eq = self.assertEqual
        msg = email.message_from_string("From: aperson@dom.ain\nTo: bperson@dom.ain\nSubject: the next line has a space on it\n \nDate: Mon, 8 Apr 2002 15:09:19 -0400\nMessage-ID: spam\n\nHere's the message body\n")
        eq(msg['subject'], 'the next line has a space on it\n ')
        eq(msg['message-id'], 'spam')
        eq(msg.get_payload(), "Here's the message body\n")

    def test_whitespace_continuation_last_header(self):
        eq = self.assertEqual
        msg = email.message_from_string("From: aperson@dom.ain\nTo: bperson@dom.ain\nDate: Mon, 8 Apr 2002 15:09:19 -0400\nMessage-ID: spam\nSubject: the next line has a space on it\n \n\nHere's the message body\n")
        eq(msg['subject'], 'the next line has a space on it\n ')
        eq(msg['message-id'], 'spam')
        eq(msg.get_payload(), "Here's the message body\n")

    def test_crlf_separation(self):
        eq = self.assertEqual
        with openfile('msg_26.txt', newline='\n') as fp:
            msg = Parser().parse(fp)
        eq(len(msg.get_payload()), 2)
        part1 = msg.get_payload(0)
        eq(part1.get_content_type(), 'text/plain')
        eq(part1.get_payload(), 'Simple email with attachment.\r\n\r\n')
        part2 = msg.get_payload(1)
        eq(part2.get_content_type(), 'application/riscos')

    def test_crlf_flatten(self):
        with openfile('msg_26.txt', newline='\n') as fp:
            text = fp.read()
        msg = email.message_from_string(text)
        s = StringIO()
        g = Generator(s)
        g.flatten(msg, linesep='\r\n')
        self.assertEqual(s.getvalue(), text)
    maxDiff = None

    def test_multipart_digest_with_extra_mime_headers(self):
        eq = self.assertEqual
        neq = self.ndiffAssertEqual
        with openfile('msg_28.txt') as fp:
            msg = email.message_from_file(fp)
        eq(msg.is_multipart(), 1)
        eq(len(msg.get_payload()), 2)
        part1 = msg.get_payload(0)
        eq(part1.get_content_type(), 'message/rfc822')
        eq(part1.is_multipart(), 1)
        eq(len(part1.get_payload()), 1)
        part1a = part1.get_payload(0)
        eq(part1a.is_multipart(), 0)
        eq(part1a.get_content_type(), 'text/plain')
        neq(part1a.get_payload(), 'message 1\n')
        part2 = msg.get_payload(1)
        eq(part2.get_content_type(), 'message/rfc822')
        eq(part2.is_multipart(), 1)
        eq(len(part2.get_payload()), 1)
        part2a = part2.get_payload(0)
        eq(part2a.is_multipart(), 0)
        eq(part2a.get_content_type(), 'text/plain')
        neq(part2a.get_payload(), 'message 2\n')

    def test_three_lines(self):
        lines = ['From: Andrew Person <aperson@dom.ain', 'Subject: Test', 'Date: Tue, 20 Aug 2002 16:43:45 +1000']
        msg = email.message_from_string(NL.join(lines))
        self.assertEqual(msg['date'], 'Tue, 20 Aug 2002 16:43:45 +1000')

    def test_strip_line_feed_and_carriage_return_in_headers(self):
        eq = self.assertEqual
        value1 = 'text'
        value2 = 'more text'
        m = ('Header: %s\r\nNext-Header: %s\r\n\r\nBody\r\n\r\n' % (value1, value2))
        msg = email.message_from_string(m)
        eq(msg.get('Header'), value1)
        eq(msg.get('Next-Header'), value2)

    def test_rfc2822_header_syntax(self):
        eq = self.assertEqual
        m = '>From: foo\nFrom: bar\n!"#QUX;~: zoo\n\nbody'
        msg = email.message_from_string(m)
        eq(len(msg), 3)
        eq(sorted((field for field in msg)), ['!"#QUX;~', '>From', 'From'])
        eq(msg.get_payload(), 'body')

    def test_rfc2822_space_not_allowed_in_header(self):
        eq = self.assertEqual
        m = '>From foo@example.com 11:25:53\nFrom: bar\n!"#QUX;~: zoo\n\nbody'
        msg = email.message_from_string(m)
        eq(len(msg.keys()), 0)

    def test_rfc2822_one_character_header(self):
        eq = self.assertEqual
        m = 'A: first header\nB: second header\nCC: third header\n\nbody'
        msg = email.message_from_string(m)
        headers = msg.keys()
        headers.sort()
        eq(headers, ['A', 'B', 'CC'])
        eq(msg.get_payload(), 'body')

    def test_CRLFLF_at_end_of_part(self):
        m = 'From: foo@bar.com\nTo: baz\nMime-Version: 1.0\nContent-Type: multipart/mixed; boundary=BOUNDARY\n\n--BOUNDARY\nContent-Type: text/plain\n\nbody ending with CRLF newline\r\n\n--BOUNDARY--\n'
        msg = email.message_from_string(m)
        self.assertTrue(msg.get_payload(0).get_payload().endswith('\r\n'))

class Test8BitBytesHandling(TestEmailBase):
    bodytest_msg = textwrap.dedent('        From: foo@bar.com\n        To: baz\n        Mime-Version: 1.0\n        Content-Type: text/plain; charset={charset}\n        Content-Transfer-Encoding: {cte}\n\n        {bodyline}\n        ')

    def test_known_8bit_CTE(self):
        m = self.bodytest_msg.format(charset='utf-8', cte='8bit', bodyline='pöstal').encode('utf-8')
        msg = email.message_from_bytes(m)
        self.assertEqual(msg.get_payload(), 'pöstal\n')
        self.assertEqual(msg.get_payload(decode=True), 'pöstal\n'.encode('utf-8'))

    def test_unknown_8bit_CTE(self):
        m = self.bodytest_msg.format(charset='notavalidcharset', cte='8bit', bodyline='pöstal').encode('utf-8')
        msg = email.message_from_bytes(m)
        self.assertEqual(msg.get_payload(), 'p��stal\n')
        self.assertEqual(msg.get_payload(decode=True), 'pöstal\n'.encode('utf-8'))

    def test_8bit_in_quopri_body(self):
        m = self.bodytest_msg.format(charset='utf-8', cte='quoted-printable', bodyline='p=C3=B6stál').encode('utf-8')
        msg = email.message_from_bytes(m)
        self.assertEqual(msg.get_payload(), 'p=C3=B6stál\n')
        self.assertEqual(msg.get_payload(decode=True), 'pöstál\n'.encode('utf-8'))

    def test_invalid_8bit_in_non_8bit_cte_uses_replace(self):
        m = self.bodytest_msg.format(charset='ascii', cte='quoted-printable', bodyline='p=C3=B6stál').encode('utf-8')
        msg = email.message_from_bytes(m)
        self.assertEqual(msg.get_payload(), 'p=C3=B6st��l\n')
        self.assertEqual(msg.get_payload(decode=True), 'pöstál\n'.encode('utf-8'))

    def test_8bit_in_base64_body(self):
        m = self.bodytest_msg.format(charset='utf-8', cte='base64', bodyline='cMO2c3RhbAá=').encode('utf-8')
        msg = email.message_from_bytes(m)
        self.assertEqual(msg.get_payload(decode=True), 'pöstal'.encode('utf-8'))
        self.assertIsInstance(msg.defects[0], errors.InvalidBase64CharactersDefect)

    def test_8bit_in_uuencode_body(self):
        m = self.bodytest_msg.format(charset='utf-8', cte='uuencode', bodyline='<,.V<W1A; á ').encode('utf-8')
        msg = email.message_from_bytes(m)
        self.assertEqual(msg.get_payload(decode=True), '<,.V<W1A; á \n'.encode('utf-8'))
    headertest_headers = (('From: foo@bar.com', ('From', 'foo@bar.com')), ('To: báz', ('To', '=?unknown-8bit?q?b=C3=A1z?=')), ('Subject: Maintenant je vous présente mon collègue, le pouf célèbre\n\tJean de Baddie', ('Subject', '=?unknown-8bit?q?Maintenant_je_vous_pr=C3=A9sente_mon_coll=C3=A8gue=2C_le_pouf_c=C3=A9l=C3=A8bre?=\n =?unknown-8bit?q?_Jean_de_Baddie?=')), ('From: göst', ('From', '=?unknown-8bit?b?Z8O2c3Q=?=')))
    headertest_msg = ('\n'.join([src for (src, _) in headertest_headers]) + '\nYes, they are flying.\n').encode('utf-8')

    def test_get_8bit_header(self):
        msg = email.message_from_bytes(self.headertest_msg)
        self.assertEqual(str(msg.get('to')), 'b��z')
        self.assertEqual(str(msg['to']), 'b��z')

    def test_print_8bit_headers(self):
        msg = email.message_from_bytes(self.headertest_msg)
        self.assertEqual(str(msg), textwrap.dedent('                            From: {}\n                            To: {}\n                            Subject: {}\n                            From: {}\n\n                            Yes, they are flying.\n                            ').format(*[expected[1] for (_, expected) in self.headertest_headers]))

    def test_values_with_8bit_headers(self):
        msg = email.message_from_bytes(self.headertest_msg)
        self.assertListEqual([str(x) for x in msg.values()], ['foo@bar.com', 'b��z', 'Maintenant je vous pr��sente mon coll��gue, le pouf c��l��bre\n\tJean de Baddie', 'g��st'])

    def test_items_with_8bit_headers(self):
        msg = email.message_from_bytes(self.headertest_msg)
        self.assertListEqual([(str(x), str(y)) for (x, y) in msg.items()], [('From', 'foo@bar.com'), ('To', 'b��z'), ('Subject', 'Maintenant je vous pr��sente mon coll��gue, le pouf c��l��bre\n\tJean de Baddie'), ('From', 'g��st')])

    def test_get_all_with_8bit_headers(self):
        msg = email.message_from_bytes(self.headertest_msg)
        self.assertListEqual([str(x) for x in msg.get_all('from')], ['foo@bar.com', 'g��st'])

    def test_get_content_type_with_8bit(self):
        msg = email.message_from_bytes(textwrap.dedent('            Content-Type: text/pl§in; charset=utf-8\n            ').encode('latin-1'))
        self.assertEqual(msg.get_content_type(), 'text/pl�in')
        self.assertEqual(msg.get_content_maintype(), 'text')
        self.assertEqual(msg.get_content_subtype(), 'pl�in')

    def test_get_params_with_8bit(self):
        msg = email.message_from_bytes('X-Header: foo=§ne; b§r=two; baz=three\n'.encode('latin-1'))
        self.assertEqual(msg.get_params(header='x-header'), [('foo', '�ne'), ('b�r', 'two'), ('baz', 'three')])
        self.assertEqual(msg.get_param('Foo', header='x-header'), '�ne')
        self.assertEqual(msg.get_param('b§r', header='x-header'), None)

    def test_get_rfc2231_params_with_8bit(self):
        msg = email.message_from_bytes(textwrap.dedent("            Content-Type: text/plain; charset=us-ascii;\n             title*=us-ascii'en'This%20is%20not%20f§n").encode('latin-1'))
        self.assertEqual(msg.get_param('title'), ('us-ascii', 'en', 'This is not f�n'))

    def test_set_rfc2231_params_with_8bit(self):
        msg = email.message_from_bytes(textwrap.dedent("            Content-Type: text/plain; charset=us-ascii;\n             title*=us-ascii'en'This%20is%20not%20f§n").encode('latin-1'))
        msg.set_param('title', 'test')
        self.assertEqual(msg.get_param('title'), 'test')

    def test_del_rfc2231_params_with_8bit(self):
        msg = email.message_from_bytes(textwrap.dedent("            Content-Type: text/plain; charset=us-ascii;\n             title*=us-ascii'en'This%20is%20not%20f§n").encode('latin-1'))
        msg.del_param('title')
        self.assertEqual(msg.get_param('title'), None)
        self.assertEqual(msg.get_content_maintype(), 'text')

    def test_get_payload_with_8bit_cte_header(self):
        msg = email.message_from_bytes(textwrap.dedent('            Content-Transfer-Encoding: b§se64\n            Content-Type: text/plain; charset=latin-1\n\n            payload\n            ').encode('latin-1'))
        self.assertEqual(msg.get_payload(), 'payload\n')
        self.assertEqual(msg.get_payload(decode=True), b'payload\n')
    non_latin_bin_msg = textwrap.dedent('        From: foo@bar.com\n        To: báz\n        Subject: Maintenant je vous présente mon collègue, le pouf célèbre\n        \tJean de Baddie\n        Mime-Version: 1.0\n        Content-Type: text/plain; charset="utf-8"\n        Content-Transfer-Encoding: 8bit\n\n        Да, они летят.\n        ').encode('utf-8')

    def test_bytes_generator(self):
        msg = email.message_from_bytes(self.non_latin_bin_msg)
        out = BytesIO()
        email.generator.BytesGenerator(out).flatten(msg)
        self.assertEqual(out.getvalue(), self.non_latin_bin_msg)

    def test_bytes_generator_handles_None_body(self):
        msg = email.message.Message()
        out = BytesIO()
        email.generator.BytesGenerator(out).flatten(msg)
        self.assertEqual(out.getvalue(), b'\n')
    non_latin_bin_msg_as7bit_wrapped = textwrap.dedent('        From: foo@bar.com\n        To: =?unknown-8bit?q?b=C3=A1z?=\n        Subject: =?unknown-8bit?q?Maintenant_je_vous_pr=C3=A9sente_mon_coll=C3=A8gue?=\n         =?unknown-8bit?q?=2C_le_pouf_c=C3=A9l=C3=A8bre?=\n         =?unknown-8bit?q?_Jean_de_Baddie?=\n        Mime-Version: 1.0\n        Content-Type: text/plain; charset="utf-8"\n        Content-Transfer-Encoding: base64\n\n        0JTQsCwg0L7QvdC4INC70LXRgtGP0YIuCg==\n        ')

    def test_generator_handles_8bit(self):
        msg = email.message_from_bytes(self.non_latin_bin_msg)
        out = StringIO()
        email.generator.Generator(out).flatten(msg)
        self.assertEqual(out.getvalue(), self.non_latin_bin_msg_as7bit_wrapped)

    def test_str_generator_should_not_mutate_msg_when_handling_8bit(self):
        msg = email.message_from_bytes(self.non_latin_bin_msg)
        out = BytesIO()
        BytesGenerator(out).flatten(msg)
        orig_value = out.getvalue()
        Generator(StringIO()).flatten(msg)
        out = BytesIO()
        BytesGenerator(out).flatten(msg)
        self.assertEqual(out.getvalue(), orig_value)

    def test_bytes_generator_with_unix_from(self):
        msg = email.message_from_bytes(self.non_latin_bin_msg)
        out = BytesIO()
        email.generator.BytesGenerator(out).flatten(msg, unixfrom=True)
        lines = out.getvalue().split(b'\n')
        self.assertEqual(lines[0].split()[0], b'From')
        self.assertEqual(b'\n'.join(lines[1:]), self.non_latin_bin_msg)
    non_latin_bin_msg_as7bit = non_latin_bin_msg_as7bit_wrapped.split('\n')
    non_latin_bin_msg_as7bit[2:4] = ['Subject: =?unknown-8bit?q?Maintenant_je_vous_pr=C3=A9sente_mon_coll=C3=A8gue=2C_le_pouf_c=C3=A9l=C3=A8bre?=']
    non_latin_bin_msg_as7bit = '\n'.join(non_latin_bin_msg_as7bit)

    def test_message_from_binary_file(self):
        fn = 'test.msg'
        self.addCleanup(unlink, fn)
        with open(fn, 'wb') as testfile:
            testfile.write(self.non_latin_bin_msg)
        with open(fn, 'rb') as testfile:
            m = email.parser.BytesParser().parse(testfile)
        self.assertEqual(str(m), self.non_latin_bin_msg_as7bit)
    latin_bin_msg = textwrap.dedent('        From: foo@bar.com\n        To: Dinsdale\n        Subject: Nudge nudge, wink, wink\n        Mime-Version: 1.0\n        Content-Type: text/plain; charset="latin-1"\n        Content-Transfer-Encoding: 8bit\n\n        oh là là, know what I mean, know what I mean?\n        ').encode('latin-1')
    latin_bin_msg_as7bit = textwrap.dedent('        From: foo@bar.com\n        To: Dinsdale\n        Subject: Nudge nudge, wink, wink\n        Mime-Version: 1.0\n        Content-Type: text/plain; charset="iso-8859-1"\n        Content-Transfer-Encoding: quoted-printable\n\n        oh l=E0 l=E0, know what I mean, know what I mean?\n        ')

    def test_string_generator_reencodes_to_quopri_when_appropriate(self):
        m = email.message_from_bytes(self.latin_bin_msg)
        self.assertEqual(str(m), self.latin_bin_msg_as7bit)

    def test_decoded_generator_emits_unicode_body(self):
        m = email.message_from_bytes(self.latin_bin_msg)
        out = StringIO()
        email.generator.DecodedGenerator(out).flatten(m)
        self.assertEqual(out.getvalue(), (self.latin_bin_msg.decode('latin-1') + '\n'))

    def test_bytes_feedparser(self):
        bfp = email.feedparser.BytesFeedParser()
        for i in range(0, len(self.latin_bin_msg), 10):
            bfp.feed(self.latin_bin_msg[i:(i + 10)])
        m = bfp.close()
        self.assertEqual(str(m), self.latin_bin_msg_as7bit)

    def test_crlf_flatten(self):
        with openfile('msg_26.txt', 'rb') as fp:
            text = fp.read()
        msg = email.message_from_bytes(text)
        s = BytesIO()
        g = email.generator.BytesGenerator(s)
        g.flatten(msg, linesep='\r\n')
        self.assertEqual(s.getvalue(), text)

    def test_8bit_multipart(self):
        source = textwrap.dedent('            Date: Fri, 18 Mar 2011 17:15:43 +0100\n            To: foo@example.com\n            From: foodwatch-Newsletter <bar@example.com>\n            Subject: Aktuelles zu Japan, Klonfleisch und Smiley-System\n            Message-ID: <76a486bee62b0d200f33dc2ca08220ad@localhost.localdomain>\n            MIME-Version: 1.0\n            Content-Type: multipart/alternative;\n                    boundary="b1_76a486bee62b0d200f33dc2ca08220ad"\n\n            --b1_76a486bee62b0d200f33dc2ca08220ad\n            Content-Type: text/plain; charset="utf-8"\n            Content-Transfer-Encoding: 8bit\n\n            Guten Tag, ,\n\n            mit großer Betroffenheit verfolgen auch wir im foodwatch-Team die\n            Nachrichten aus Japan.\n\n\n            --b1_76a486bee62b0d200f33dc2ca08220ad\n            Content-Type: text/html; charset="utf-8"\n            Content-Transfer-Encoding: 8bit\n\n            <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"\n                "http://www.w3.org/TR/html4/loose.dtd">\n            <html lang="de">\n            <head>\n                    <title>foodwatch - Newsletter</title>\n            </head>\n            <body>\n              <p>mit gro&szlig;er Betroffenheit verfolgen auch wir im foodwatch-Team\n                 die Nachrichten aus Japan.</p>\n            </body>\n            </html>\n            --b1_76a486bee62b0d200f33dc2ca08220ad--\n\n            ').encode('utf-8')
        msg = email.message_from_bytes(source)
        s = BytesIO()
        g = email.generator.BytesGenerator(s)
        g.flatten(msg)
        self.assertEqual(s.getvalue(), source)

    def test_bytes_generator_b_encoding_linesep(self):
        m = Message()
        m['Subject'] = Header('žluťoučký kůň')
        s = BytesIO()
        g = email.generator.BytesGenerator(s)
        g.flatten(m, linesep='\r\n')
        self.assertEqual(s.getvalue(), b'Subject: =?utf-8?b?xb5sdcWlb3XEjWvDvSBrxa/FiA==?=\r\n\r\n')

    def test_generator_b_encoding_linesep(self):
        m = Message()
        m['Subject'] = Header('žluťoučký kůň')
        s = StringIO()
        g = email.generator.Generator(s)
        g.flatten(m, linesep='\r\n')
        self.assertEqual(s.getvalue(), 'Subject: =?utf-8?b?xb5sdcWlb3XEjWvDvSBrxa/FiA==?=\r\n\r\n')
    maxDiff = None

class BaseTestBytesGeneratorIdempotent():
    maxDiff = None

    def _msgobj(self, filename):
        with openfile(filename, 'rb') as fp:
            data = fp.read()
        data = self.normalize_linesep_regex.sub(self.blinesep, data)
        msg = email.message_from_bytes(data)
        return (msg, data)

    def _idempotent(self, msg, data, unixfrom=False):
        b = BytesIO()
        g = email.generator.BytesGenerator(b, maxheaderlen=0)
        g.flatten(msg, unixfrom=unixfrom, linesep=self.linesep)
        self.assertEqual(data, b.getvalue())

class TestBytesGeneratorIdempotentNL(BaseTestBytesGeneratorIdempotent, TestIdempotent):
    linesep = '\n'
    blinesep = b'\n'
    normalize_linesep_regex = re.compile(b'\\r\\n')

class TestBytesGeneratorIdempotentCRLF(BaseTestBytesGeneratorIdempotent, TestIdempotent):
    linesep = '\r\n'
    blinesep = b'\r\n'
    normalize_linesep_regex = re.compile(b'(?<!\\r)\\n')

class TestBase64(unittest.TestCase):

    def test_len(self):
        eq = self.assertEqual
        eq(base64mime.header_length('hello'), len(base64mime.body_encode(b'hello', eol='')))
        for size in range(15):
            if (size == 0):
                bsize = 0
            elif (size <= 3):
                bsize = 4
            elif (size <= 6):
                bsize = 8
            elif (size <= 9):
                bsize = 12
            elif (size <= 12):
                bsize = 16
            else:
                bsize = 20
            eq(base64mime.header_length(('x' * size)), bsize)

    def test_decode(self):
        eq = self.assertEqual
        eq(base64mime.decode(''), b'')
        eq(base64mime.decode('aGVsbG8='), b'hello')

    def test_encode(self):
        eq = self.assertEqual
        eq(base64mime.body_encode(b''), b'')
        eq(base64mime.body_encode(b'hello'), 'aGVsbG8=\n')
        eq(base64mime.body_encode(b'hello\n'), 'aGVsbG8K\n')
        eq(base64mime.body_encode((b'xxxx ' * 20), maxlinelen=40), 'eHh4eCB4eHh4IHh4eHggeHh4eCB4eHh4IHh4eHgg\neHh4eCB4eHh4IHh4eHggeHh4eCB4eHh4IHh4eHgg\neHh4eCB4eHh4IHh4eHggeHh4eCB4eHh4IHh4eHgg\neHh4eCB4eHh4IA==\n')
        eq(base64mime.body_encode((b'xxxx ' * 20), maxlinelen=40, eol='\r\n'), 'eHh4eCB4eHh4IHh4eHggeHh4eCB4eHh4IHh4eHgg\r\neHh4eCB4eHh4IHh4eHggeHh4eCB4eHh4IHh4eHgg\r\neHh4eCB4eHh4IHh4eHggeHh4eCB4eHh4IHh4eHgg\r\neHh4eCB4eHh4IA==\r\n')

    def test_header_encode(self):
        eq = self.assertEqual
        he = base64mime.header_encode
        eq(he('hello'), '=?iso-8859-1?b?aGVsbG8=?=')
        eq(he('hello\r\nworld'), '=?iso-8859-1?b?aGVsbG8NCndvcmxk?=')
        eq(he('hello\nworld'), '=?iso-8859-1?b?aGVsbG8Kd29ybGQ=?=')
        eq(he('hello', charset='iso-8859-2'), '=?iso-8859-2?b?aGVsbG8=?=')
        eq(he('hello\nworld'), '=?iso-8859-1?b?aGVsbG8Kd29ybGQ=?=')

class TestQuopri(unittest.TestCase):

    def setUp(self):
        self.hlit = list(chain(range(ord('a'), (ord('z') + 1)), range(ord('A'), (ord('Z') + 1)), range(ord('0'), (ord('9') + 1)), (c for c in b'!*+-/')))
        self.hnon = [c for c in range(256) if (c not in self.hlit)]
        assert ((len(self.hlit) + len(self.hnon)) == 256)
        self.blit = list(range(ord(' '), (ord('~') + 1)))
        self.blit.append(ord('\t'))
        self.blit.remove(ord('='))
        self.bnon = [c for c in range(256) if (c not in self.blit)]
        assert ((len(self.blit) + len(self.bnon)) == 256)

    def test_quopri_header_check(self):
        for c in self.hlit:
            self.assertFalse(quoprimime.header_check(c), ('Should not be header quopri encoded: %s' % chr(c)))
        for c in self.hnon:
            self.assertTrue(quoprimime.header_check(c), ('Should be header quopri encoded: %s' % chr(c)))

    def test_quopri_body_check(self):
        for c in self.blit:
            self.assertFalse(quoprimime.body_check(c), ('Should not be body quopri encoded: %s' % chr(c)))
        for c in self.bnon:
            self.assertTrue(quoprimime.body_check(c), ('Should be body quopri encoded: %s' % chr(c)))

    def test_header_quopri_len(self):
        eq = self.assertEqual
        eq(quoprimime.header_length(b'hello'), 5)
        eq(len(quoprimime.header_encode(b'hello', charset='xxx')), (quoprimime.header_length(b'hello') + 10))
        eq(quoprimime.header_length(b'h@e@l@l@o@'), 20)
        eq(len(quoprimime.header_encode(b'h@e@l@l@o@', charset='xxx')), (quoprimime.header_length(b'h@e@l@l@o@') + 10))
        for c in self.hlit:
            eq(quoprimime.header_length(bytes([c])), 1, ('expected length 1 for %r' % chr(c)))
        for c in self.hnon:
            if (c == ord(' ')):
                continue
            eq(quoprimime.header_length(bytes([c])), 3, ('expected length 3 for %r' % chr(c)))
        eq(quoprimime.header_length(b' '), 1)

    def test_body_quopri_len(self):
        eq = self.assertEqual
        for c in self.blit:
            eq(quoprimime.body_length(bytes([c])), 1)
        for c in self.bnon:
            eq(quoprimime.body_length(bytes([c])), 3)

    def test_quote_unquote_idempotent(self):
        for x in range(256):
            c = chr(x)
            self.assertEqual(quoprimime.unquote(quoprimime.quote(c)), c)

    def _test_header_encode(self, header, expected_encoded_header, charset=None):
        if (charset is None):
            encoded_header = quoprimime.header_encode(header)
        else:
            encoded_header = quoprimime.header_encode(header, charset)
        self.assertEqual(encoded_header, expected_encoded_header)

    def test_header_encode_null(self):
        self._test_header_encode(b'', '')

    def test_header_encode_one_word(self):
        self._test_header_encode(b'hello', '=?iso-8859-1?q?hello?=')

    def test_header_encode_two_lines(self):
        self._test_header_encode(b'hello\nworld', '=?iso-8859-1?q?hello=0Aworld?=')

    def test_header_encode_non_ascii(self):
        self._test_header_encode(b'hello\xc7there', '=?iso-8859-1?q?hello=C7there?=')

    def test_header_encode_alt_charset(self):
        self._test_header_encode(b'hello', '=?iso-8859-2?q?hello?=', charset='iso-8859-2')

    def _test_header_decode(self, encoded_header, expected_decoded_header):
        decoded_header = quoprimime.header_decode(encoded_header)
        self.assertEqual(decoded_header, expected_decoded_header)

    def test_header_decode_null(self):
        self._test_header_decode('', '')

    def test_header_decode_one_word(self):
        self._test_header_decode('hello', 'hello')

    def test_header_decode_two_lines(self):
        self._test_header_decode('hello=0Aworld', 'hello\nworld')

    def test_header_decode_non_ascii(self):
        self._test_header_decode('hello=C7there', 'helloÇthere')

    def test_header_decode_re_bug_18380(self):
        self.assertEqual(quoprimime.header_decode(('=30' * 257)), ('0' * 257))

    def _test_decode(self, encoded, expected_decoded, eol=None):
        if (eol is None):
            decoded = quoprimime.decode(encoded)
        else:
            decoded = quoprimime.decode(encoded, eol=eol)
        self.assertEqual(decoded, expected_decoded)

    def test_decode_null_word(self):
        self._test_decode('', '')

    def test_decode_null_line_null_word(self):
        self._test_decode('\r\n', '\n')

    def test_decode_one_word(self):
        self._test_decode('hello', 'hello')

    def test_decode_one_word_eol(self):
        self._test_decode('hello', 'hello', eol='X')

    def test_decode_one_line(self):
        self._test_decode('hello\r\n', 'hello\n')

    def test_decode_one_line_lf(self):
        self._test_decode('hello\n', 'hello\n')

    def test_decode_one_line_cr(self):
        self._test_decode('hello\r', 'hello\n')

    def test_decode_one_line_nl(self):
        self._test_decode('hello\n', 'helloX', eol='X')

    def test_decode_one_line_crnl(self):
        self._test_decode('hello\r\n', 'helloX', eol='X')

    def test_decode_one_line_one_word(self):
        self._test_decode('hello\r\nworld', 'hello\nworld')

    def test_decode_one_line_one_word_eol(self):
        self._test_decode('hello\r\nworld', 'helloXworld', eol='X')

    def test_decode_two_lines(self):
        self._test_decode('hello\r\nworld\r\n', 'hello\nworld\n')

    def test_decode_two_lines_eol(self):
        self._test_decode('hello\r\nworld\r\n', 'helloXworldX', eol='X')

    def test_decode_one_long_line(self):
        self._test_decode(('Spam' * 250), ('Spam' * 250))

    def test_decode_one_space(self):
        self._test_decode(' ', '')

    def test_decode_multiple_spaces(self):
        self._test_decode((' ' * 5), '')

    def test_decode_one_line_trailing_spaces(self):
        self._test_decode('hello    \r\n', 'hello\n')

    def test_decode_two_lines_trailing_spaces(self):
        self._test_decode('hello    \r\nworld   \r\n', 'hello\nworld\n')

    def test_decode_quoted_word(self):
        self._test_decode('=22quoted=20words=22', '"quoted words"')

    def test_decode_uppercase_quoting(self):
        self._test_decode('ab=CD=EF', 'abÍï')

    def test_decode_lowercase_quoting(self):
        self._test_decode('ab=cd=ef', 'abÍï')

    def test_decode_soft_line_break(self):
        self._test_decode('soft line=\r\nbreak', 'soft linebreak')

    def test_decode_false_quoting(self):
        self._test_decode('A=1,B=A ==> A+B==2', 'A=1,B=A ==> A+B==2')

    def _test_encode(self, body, expected_encoded_body, maxlinelen=None, eol=None):
        kwargs = {}
        if (maxlinelen is None):
            maxlinelen = 76
        else:
            kwargs['maxlinelen'] = maxlinelen
        if (eol is None):
            eol = '\n'
        else:
            kwargs['eol'] = eol
        encoded_body = quoprimime.body_encode(body, **kwargs)
        self.assertEqual(encoded_body, expected_encoded_body)
        if ((eol == '\n') or (eol == '\r\n')):
            for line in encoded_body.splitlines():
                self.assertLessEqual(len(line), maxlinelen)

    def test_encode_null(self):
        self._test_encode('', '')

    def test_encode_null_lines(self):
        self._test_encode('\n\n', '\n\n')

    def test_encode_one_line(self):
        self._test_encode('hello\n', 'hello\n')

    def test_encode_one_line_crlf(self):
        self._test_encode('hello\r\n', 'hello\n')

    def test_encode_one_line_eol(self):
        self._test_encode('hello\n', 'hello\r\n', eol='\r\n')

    def test_encode_one_line_eol_after_non_ascii(self):
        self._test_encode('helloυ\n'.encode('utf-8').decode('latin1'), 'hello=CF=85\r\n', eol='\r\n')

    def test_encode_one_space(self):
        self._test_encode(' ', '=20')

    def test_encode_one_line_one_space(self):
        self._test_encode(' \n', '=20\n')

    def test_encode_two_lines_one_space(self):
        self._test_encode(' \n \n', '=20\n=20\n')

    def test_encode_one_word_trailing_spaces(self):
        self._test_encode('hello   ', 'hello  =20')

    def test_encode_one_line_trailing_spaces(self):
        self._test_encode('hello   \n', 'hello  =20\n')

    def test_encode_one_word_trailing_tab(self):
        self._test_encode('hello  \t', 'hello  =09')

    def test_encode_one_line_trailing_tab(self):
        self._test_encode('hello  \t\n', 'hello  =09\n')

    def test_encode_trailing_space_before_maxlinelen(self):
        self._test_encode('abcd \n1234', 'abcd =\n\n1234', maxlinelen=6)

    def test_encode_trailing_space_at_maxlinelen(self):
        self._test_encode('abcd \n1234', 'abcd=\n=20\n1234', maxlinelen=5)

    def test_encode_trailing_space_beyond_maxlinelen(self):
        self._test_encode('abcd \n1234', 'abc=\nd=20\n1234', maxlinelen=4)

    def test_encode_whitespace_lines(self):
        self._test_encode((' \n' * 5), ('=20\n' * 5))

    def test_encode_quoted_equals(self):
        self._test_encode('a = b', 'a =3D b')

    def test_encode_one_long_string(self):
        self._test_encode(('x' * 100), ((('x' * 75) + '=\n') + ('x' * 25)))

    def test_encode_one_long_line(self):
        self._test_encode((('x' * 100) + '\n'), (((('x' * 75) + '=\n') + ('x' * 25)) + '\n'))

    def test_encode_one_very_long_line(self):
        self._test_encode((('x' * 200) + '\n'), (((2 * (('x' * 75) + '=\n')) + ('x' * 50)) + '\n'))

    def test_encode_shortest_maxlinelen(self):
        self._test_encode(('=' * 5), (('=3D=\n' * 4) + '=3D'), maxlinelen=4)

    def test_encode_maxlinelen_too_small(self):
        self.assertRaises(ValueError, self._test_encode, '', '', maxlinelen=3)

    def test_encode(self):
        eq = self.assertEqual
        eq(quoprimime.body_encode(''), '')
        eq(quoprimime.body_encode('hello'), 'hello')
        eq(quoprimime.body_encode('hello\r\nworld'), 'hello\nworld')
        eq(quoprimime.body_encode(('xxxx ' * 20), maxlinelen=40), 'xxxx xxxx xxxx xxxx xxxx xxxx xxxx xxxx=\n xxxx xxxx xxxx xxxx xxxx xxxx xxxx xxx=\nx xxxx xxxx xxxx xxxx=20')
        eq(quoprimime.body_encode(('xxxx ' * 20), maxlinelen=40, eol='\r\n'), 'xxxx xxxx xxxx xxxx xxxx xxxx xxxx xxxx=\r\n xxxx xxxx xxxx xxxx xxxx xxxx xxxx xxx=\r\nx xxxx xxxx xxxx xxxx=20')
        eq(quoprimime.body_encode('one line\n\ntwo line'), 'one line\n\ntwo line')

class TestCharset(unittest.TestCase):

    def tearDown(self):
        from email import charset as CharsetModule
        try:
            del CharsetModule.CHARSETS['fake']
        except KeyError:
            pass

    def test_codec_encodeable(self):
        eq = self.assertEqual
        c = Charset('us-ascii')
        eq(c.header_encode('Hello World!'), 'Hello World!')
        s = '¤¢¤¤¤¦¤¨¤ª'
        self.assertRaises(UnicodeError, c.header_encode, s)
        c = Charset('utf-8')
        eq(c.header_encode(s), '=?utf-8?b?wqTCosKkwqTCpMKmwqTCqMKkwqo=?=')

    def test_body_encode(self):
        eq = self.assertEqual
        c = Charset('iso-8859-1')
        eq('hello w=F6rld', c.body_encode('hello wörld'))
        c = Charset('utf-8')
        eq('aGVsbG8gd29ybGQ=\n', c.body_encode(b'hello world'))
        c = Charset('us-ascii')
        eq('hello world', c.body_encode('hello world'))
        c = Charset('euc-jp')
        from email import charset as CharsetModule
        CharsetModule.add_charset('fake', CharsetModule.QP, None, 'utf-8')
        c = Charset('fake')
        eq('hello world', c.body_encode('hello world'))

    def test_unicode_charset_name(self):
        charset = Charset('us-ascii')
        self.assertEqual(str(charset), 'us-ascii')
        self.assertRaises(errors.CharsetError, Charset, 'ascÿii')

class TestHeader(TestEmailBase):

    def test_simple(self):
        eq = self.ndiffAssertEqual
        h = Header('Hello World!')
        eq(h.encode(), 'Hello World!')
        h.append(' Goodbye World!')
        eq(h.encode(), 'Hello World!  Goodbye World!')

    def test_simple_surprise(self):
        eq = self.ndiffAssertEqual
        h = Header('Hello World!')
        eq(h.encode(), 'Hello World!')
        h.append('Goodbye World!')
        eq(h.encode(), 'Hello World! Goodbye World!')

    def test_header_needs_no_decoding(self):
        h = 'no decoding needed'
        self.assertEqual(decode_header(h), [(h, None)])

    def test_long(self):
        h = Header("I am the very model of a modern Major-General; I've information vegetable, animal, and mineral; I know the kings of England, and I quote the fights historical from Marathon to Waterloo, in order categorical; I'm very well acquainted, too, with matters mathematical; I understand equations, both the simple and quadratical; about binomial theorem I'm teeming with a lot o' news, with many cheerful facts about the square of the hypotenuse.", maxlinelen=76)
        for l in h.encode(splitchars=' ').split('\n '):
            self.assertLessEqual(len(l), 76)

    def test_multilingual(self):
        eq = self.ndiffAssertEqual
        g = Charset('iso-8859-1')
        cz = Charset('iso-8859-2')
        utf8 = Charset('utf-8')
        g_head = b'Die Mieter treten hier ein werden mit einem Foerderband komfortabel den Korridor entlang, an s\xfcdl\xfcndischen Wandgem\xe4lden vorbei, gegen die rotierenden Klingen bef\xf6rdert. '
        cz_head = b'Finan\xe8ni metropole se hroutily pod tlakem jejich d\xf9vtipu.. '
        utf8_head = '正確に言うと翻訳はされていません。一部はドイツ語ですが、あとはでたらめです。実際には「Wenn ist das Nunstuck git und Slotermeyer? Ja! Beiherhund das Oder die Flipperwaldt gersput.」と言っています。'
        h = Header(g_head, g)
        h.append(cz_head, cz)
        h.append(utf8_head, utf8)
        enc = h.encode(maxlinelen=76)
        eq(enc, '=?iso-8859-1?q?Die_Mieter_treten_hier_ein_werden_mit_einem_Foerderband_kom?=\n =?iso-8859-1?q?fortabel_den_Korridor_entlang=2C_an_s=FCdl=FCndischen_Wand?=\n =?iso-8859-1?q?gem=E4lden_vorbei=2C_gegen_die_rotierenden_Klingen_bef=F6r?=\n =?iso-8859-1?q?dert=2E_?= =?iso-8859-2?q?Finan=E8ni_metropole_se_hroutily?=\n =?iso-8859-2?q?_pod_tlakem_jejich_d=F9vtipu=2E=2E_?= =?utf-8?b?5q2j56K6?=\n =?utf-8?b?44Gr6KiA44GG44Go57+76Kiz44Gv44GV44KM44Gm44GE44G+44Gb44KT44CC?=\n =?utf-8?b?5LiA6YOo44Gv44OJ44Kk44OE6Kqe44Gn44GZ44GM44CB44GC44Go44Gv44Gn?=\n =?utf-8?b?44Gf44KJ44KB44Gn44GZ44CC5a6f6Zqb44Gr44Gv44CMV2VubiBpc3QgZGFz?=\n =?utf-8?b?IE51bnN0dWNrIGdpdCB1bmQgU2xvdGVybWV5ZXI/IEphISBCZWloZXJodW5k?=\n =?utf-8?b?IGRhcyBPZGVyIGRpZSBGbGlwcGVyd2FsZHQgZ2Vyc3B1dC7jgI3jgajoqIA=?=\n =?utf-8?b?44Gj44Gm44GE44G+44GZ44CC?=')
        decoded = decode_header(enc)
        eq(len(decoded), 3)
        eq(decoded[0], (g_head, 'iso-8859-1'))
        eq(decoded[1], (cz_head, 'iso-8859-2'))
        eq(decoded[2], (utf8_head.encode('utf-8'), 'utf-8'))
        ustr = str(h)
        eq(ustr, b'Die Mieter treten hier ein werden mit einem Foerderband komfortabel den Korridor entlang, an s\xc3\xbcdl\xc3\xbcndischen Wandgem\xc3\xa4lden vorbei, gegen die rotierenden Klingen bef\xc3\xb6rdert. Finan\xc4\x8dni metropole se hroutily pod tlakem jejich d\xc5\xafvtipu.. \xe6\xad\xa3\xe7\xa2\xba\xe3\x81\xab\xe8\xa8\x80\xe3\x81\x86\xe3\x81\xa8\xe7\xbf\xbb\xe8\xa8\xb3\xe3\x81\xaf\xe3\x81\x95\xe3\x82\x8c\xe3\x81\xa6\xe3\x81\x84\xe3\x81\xbe\xe3\x81\x9b\xe3\x82\x93\xe3\x80\x82\xe4\xb8\x80\xe9\x83\xa8\xe3\x81\xaf\xe3\x83\x89\xe3\x82\xa4\xe3\x83\x84\xe8\xaa\x9e\xe3\x81\xa7\xe3\x81\x99\xe3\x81\x8c\xe3\x80\x81\xe3\x81\x82\xe3\x81\xa8\xe3\x81\xaf\xe3\x81\xa7\xe3\x81\x9f\xe3\x82\x89\xe3\x82\x81\xe3\x81\xa7\xe3\x81\x99\xe3\x80\x82\xe5\xae\x9f\xe9\x9a\x9b\xe3\x81\xab\xe3\x81\xaf\xe3\x80\x8cWenn ist das Nunstuck git und Slotermeyer? Ja! Beiherhund das Oder die Flipperwaldt gersput.\xe3\x80\x8d\xe3\x81\xa8\xe8\xa8\x80\xe3\x81\xa3\xe3\x81\xa6\xe3\x81\x84\xe3\x81\xbe\xe3\x81\x99\xe3\x80\x82'.decode('utf-8'))
        newh = make_header(decode_header(enc))
        eq(newh, h)

    def test_empty_header_encode(self):
        h = Header()
        self.assertEqual(h.encode(), '')

    def test_header_ctor_default_args(self):
        eq = self.ndiffAssertEqual
        h = Header()
        eq(h, '')
        h.append('foo', Charset('iso-8859-1'))
        eq(h, 'foo')

    def test_explicit_maxlinelen(self):
        eq = self.ndiffAssertEqual
        hstr = 'A very long line that must get split to something other than at the 76th character boundary to test the non-default behavior'
        h = Header(hstr)
        eq(h.encode(), 'A very long line that must get split to something other than at the 76th\n character boundary to test the non-default behavior')
        eq(str(h), hstr)
        h = Header(hstr, header_name='Subject')
        eq(h.encode(), 'A very long line that must get split to something other than at the\n 76th character boundary to test the non-default behavior')
        eq(str(h), hstr)
        h = Header(hstr, maxlinelen=1024, header_name='Subject')
        eq(h.encode(), hstr)
        eq(str(h), hstr)

    def test_quopri_splittable(self):
        eq = self.ndiffAssertEqual
        h = Header(charset='iso-8859-1', maxlinelen=20)
        x = ('xxxx ' * 20)
        h.append(x)
        s = h.encode()
        eq(s, '=?iso-8859-1?q?xxx?=\n =?iso-8859-1?q?x_?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?_x?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?x_?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?_x?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?x_?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?_x?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?x_?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?_x?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?x_?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?_x?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?x_?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?_x?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?x_?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?_x?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?x_?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?_x?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?x_?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?_x?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?x_?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?xx?=\n =?iso-8859-1?q?_?=')
        eq(x, str(make_header(decode_header(s))))
        h = Header(charset='iso-8859-1', maxlinelen=40)
        h.append(('xxxx ' * 20))
        s = h.encode()
        eq(s, '=?iso-8859-1?q?xxxx_xxxx_xxxx_xxxx_xxx?=\n =?iso-8859-1?q?x_xxxx_xxxx_xxxx_xxxx_?=\n =?iso-8859-1?q?xxxx_xxxx_xxxx_xxxx_xx?=\n =?iso-8859-1?q?xx_xxxx_xxxx_xxxx_xxxx?=\n =?iso-8859-1?q?_xxxx_xxxx_?=')
        eq(x, str(make_header(decode_header(s))))

    def test_base64_splittable(self):
        eq = self.ndiffAssertEqual
        h = Header(charset='koi8-r', maxlinelen=20)
        x = ('xxxx ' * 20)
        h.append(x)
        s = h.encode()
        eq(s, '=?koi8-r?b?eHh4?=\n =?koi8-r?b?eCB4?=\n =?koi8-r?b?eHh4?=\n =?koi8-r?b?IHh4?=\n =?koi8-r?b?eHgg?=\n =?koi8-r?b?eHh4?=\n =?koi8-r?b?eCB4?=\n =?koi8-r?b?eHh4?=\n =?koi8-r?b?IHh4?=\n =?koi8-r?b?eHgg?=\n =?koi8-r?b?eHh4?=\n =?koi8-r?b?eCB4?=\n =?koi8-r?b?eHh4?=\n =?koi8-r?b?IHh4?=\n =?koi8-r?b?eHgg?=\n =?koi8-r?b?eHh4?=\n =?koi8-r?b?eCB4?=\n =?koi8-r?b?eHh4?=\n =?koi8-r?b?IHh4?=\n =?koi8-r?b?eHgg?=\n =?koi8-r?b?eHh4?=\n =?koi8-r?b?eCB4?=\n =?koi8-r?b?eHh4?=\n =?koi8-r?b?IHh4?=\n =?koi8-r?b?eHgg?=\n =?koi8-r?b?eHh4?=\n =?koi8-r?b?eCB4?=\n =?koi8-r?b?eHh4?=\n =?koi8-r?b?IHh4?=\n =?koi8-r?b?eHgg?=\n =?koi8-r?b?eHh4?=\n =?koi8-r?b?eCB4?=\n =?koi8-r?b?eHh4?=\n =?koi8-r?b?IA==?=')
        eq(x, str(make_header(decode_header(s))))
        h = Header(charset='koi8-r', maxlinelen=40)
        h.append(x)
        s = h.encode()
        eq(s, '=?koi8-r?b?eHh4eCB4eHh4IHh4eHggeHh4?=\n =?koi8-r?b?eCB4eHh4IHh4eHggeHh4eCB4?=\n =?koi8-r?b?eHh4IHh4eHggeHh4eCB4eHh4?=\n =?koi8-r?b?IHh4eHggeHh4eCB4eHh4IHh4?=\n =?koi8-r?b?eHggeHh4eCB4eHh4IHh4eHgg?=\n =?koi8-r?b?eHh4eCB4eHh4IA==?=')
        eq(x, str(make_header(decode_header(s))))

    def test_us_ascii_header(self):
        eq = self.assertEqual
        s = 'hello'
        x = decode_header(s)
        eq(x, [('hello', None)])
        h = make_header(x)
        eq(s, h.encode())

    def test_string_charset(self):
        eq = self.assertEqual
        h = Header()
        h.append('hello', 'iso-8859-1')
        eq(h, 'hello')

    def test_utf8_shortest(self):
        eq = self.assertEqual
        h = Header('pöstal', 'utf-8')
        eq(h.encode(), '=?utf-8?q?p=C3=B6stal?=')
        h = Header('菊地時夫', 'utf-8')
        eq(h.encode(), '=?utf-8?b?6I+K5Zyw5pmC5aSr?=')

    def test_bad_8bit_header(self):
        raises = self.assertRaises
        eq = self.assertEqual
        x = b'Ynwp4dUEbay Auction Semiar- No Charge \x96 Earn Big'
        raises(UnicodeError, Header, x)
        h = Header()
        raises(UnicodeError, h.append, x)
        e = x.decode('utf-8', 'replace')
        eq(str(Header(x, errors='replace')), e)
        h.append(x, errors='replace')
        eq(str(h), e)

    def test_escaped_8bit_header(self):
        x = b'Ynwp4dUEbay Auction Semiar- No Charge \x96 Earn Big'
        e = x.decode('ascii', 'surrogateescape')
        h = Header(e, charset=email.charset.UNKNOWN8BIT)
        self.assertEqual(str(h), 'Ynwp4dUEbay Auction Semiar- No Charge � Earn Big')
        self.assertEqual(email.header.decode_header(h), [(x, 'unknown-8bit')])

    def test_header_handles_binary_unknown8bit(self):
        x = b'Ynwp4dUEbay Auction Semiar- No Charge \x96 Earn Big'
        h = Header(x, charset=email.charset.UNKNOWN8BIT)
        self.assertEqual(str(h), 'Ynwp4dUEbay Auction Semiar- No Charge � Earn Big')
        self.assertEqual(email.header.decode_header(h), [(x, 'unknown-8bit')])

    def test_make_header_handles_binary_unknown8bit(self):
        x = b'Ynwp4dUEbay Auction Semiar- No Charge \x96 Earn Big'
        h = Header(x, charset=email.charset.UNKNOWN8BIT)
        h2 = email.header.make_header(email.header.decode_header(h))
        self.assertEqual(str(h2), 'Ynwp4dUEbay Auction Semiar- No Charge � Earn Big')
        self.assertEqual(email.header.decode_header(h2), [(x, 'unknown-8bit')])

    def test_modify_returned_list_does_not_change_header(self):
        h = Header('test')
        chunks = email.header.decode_header(h)
        chunks.append(('ascii', 'test2'))
        self.assertEqual(str(h), 'test')

    def test_encoded_adjacent_nonencoded(self):
        eq = self.assertEqual
        h = Header()
        h.append('hello', 'iso-8859-1')
        h.append('world')
        s = h.encode()
        eq(s, '=?iso-8859-1?q?hello?= world')
        h = make_header(decode_header(s))
        eq(h.encode(), s)

    def test_whitespace_keeper(self):
        eq = self.assertEqual
        s = 'Subject: =?koi8-r?b?8NLP18XSy8EgzsEgxsnOwczYztk=?= =?koi8-r?q?=CA?= zz.'
        parts = decode_header(s)
        eq(parts, [(b'Subject: ', None), (b'\xf0\xd2\xcf\xd7\xc5\xd2\xcb\xc1 \xce\xc1 \xc6\xc9\xce\xc1\xcc\xd8\xce\xd9\xca', 'koi8-r'), (b' zz.', None)])
        hdr = make_header(parts)
        eq(hdr.encode(), 'Subject: =?koi8-r?b?8NLP18XSy8EgzsEgxsnOwczYztnK?= zz.')

    def test_broken_base64_header(self):
        raises = self.assertRaises
        s = 'Subject: =?EUC-KR?B?CSixpLDtKSC/7Liuvsax4iC6uLmwMcijIKHaILzSwd/H0SC8+LCjwLsgv7W/+Mj3I ?='
        raises(errors.HeaderParseError, decode_header, s)

    def test_shift_jis_charset(self):
        h = Header('文', charset='shift_jis')
        self.assertEqual(h.encode(), '=?iso-2022-jp?b?GyRCSjgbKEI=?=')

    def test_flatten_header_with_no_value(self):
        msg = email.message_from_string('EmptyHeader:')
        self.assertEqual(str(msg), 'EmptyHeader: \n\n')

    def test_encode_preserves_leading_ws_on_value(self):
        msg = Message()
        msg['SomeHeader'] = '   value with leading ws'
        self.assertEqual(str(msg), 'SomeHeader:    value with leading ws\n\n')

    def test_whitespace_header(self):
        self.assertEqual(Header(' ').encode(), ' ')

class TestRFC2231(TestEmailBase):

    def test_get_param(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_29.txt')
        eq(msg.get_param('title'), ('us-ascii', 'en', "This is even more ***fun*** isn't it!"))
        eq(msg.get_param('title', unquote=False), ('us-ascii', 'en', '"This is even more ***fun*** isn\'t it!"'))

    def test_set_param(self):
        eq = self.ndiffAssertEqual
        msg = Message()
        msg.set_param('title', "This is even more ***fun*** isn't it!", charset='us-ascii')
        eq(msg.get_param('title'), ('us-ascii', '', "This is even more ***fun*** isn't it!"))
        msg.set_param('title', "This is even more ***fun*** isn't it!", charset='us-ascii', language='en')
        eq(msg.get_param('title'), ('us-ascii', 'en', "This is even more ***fun*** isn't it!"))
        msg = self._msgobj('msg_01.txt')
        msg.set_param('title', "This is even more ***fun*** isn't it!", charset='us-ascii', language='en')
        eq(msg.as_string(maxheaderlen=78), "Return-Path: <bbb@zzz.org>\nDelivered-To: bbb@zzz.org\nReceived: by mail.zzz.org (Postfix, from userid 889)\n\tid 27CEAD38CC; Fri,  4 May 2001 14:05:44 -0400 (EDT)\nMIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\nMessage-ID: <15090.61304.110929.45684@aaa.zzz.org>\nFrom: bbb@ddd.com (John X. Doe)\nTo: bbb@zzz.org\nSubject: This is a test message\nDate: Fri, 4 May 2001 14:05:44 -0400\nContent-Type: text/plain; charset=us-ascii;\n title*=us-ascii'en'This%20is%20even%20more%20%2A%2A%2Afun%2A%2A%2A%20isn%27t%20it%21\n\n\nHi,\n\nDo you like this message?\n\n-Me\n")

    def test_set_param_requote(self):
        msg = Message()
        msg.set_param('title', 'foo')
        self.assertEqual(msg['content-type'], 'text/plain; title="foo"')
        msg.set_param('title', 'bar', requote=False)
        self.assertEqual(msg['content-type'], 'text/plain; title=bar')
        msg.set_param('title', '(bar)bell', requote=False)
        self.assertEqual(msg['content-type'], 'text/plain; title="(bar)bell"')

    def test_del_param(self):
        eq = self.ndiffAssertEqual
        msg = self._msgobj('msg_01.txt')
        msg.set_param('foo', 'bar', charset='us-ascii', language='en')
        msg.set_param('title', "This is even more ***fun*** isn't it!", charset='us-ascii', language='en')
        msg.del_param('foo', header='Content-Type')
        eq(msg.as_string(maxheaderlen=78), 'Return-Path: <bbb@zzz.org>\nDelivered-To: bbb@zzz.org\nReceived: by mail.zzz.org (Postfix, from userid 889)\n\tid 27CEAD38CC; Fri,  4 May 2001 14:05:44 -0400 (EDT)\nMIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\nMessage-ID: <15090.61304.110929.45684@aaa.zzz.org>\nFrom: bbb@ddd.com (John X. Doe)\nTo: bbb@zzz.org\nSubject: This is a test message\nDate: Fri, 4 May 2001 14:05:44 -0400\nContent-Type: text/plain; charset="us-ascii";\n title*=us-ascii\'en\'This%20is%20even%20more%20%2A%2A%2Afun%2A%2A%2A%20isn%27t%20it%21\n\n\nHi,\n\nDo you like this message?\n\n-Me\n')

    def test_rfc2231_get_content_charset(self):
        eq = self.assertEqual
        msg = self._msgobj('msg_32.txt')
        eq(msg.get_content_charset(), 'us-ascii')

    def test_rfc2231_parse_rfc_quoting(self):
        m = textwrap.dedent('            Content-Disposition: inline;\n            \tfilename*0*=\'\'This%20is%20even%20more%20;\n            \tfilename*1*=%2A%2A%2Afun%2A%2A%2A%20;\n            \tfilename*2="is it not.pdf"\n\n            ')
        msg = email.message_from_string(m)
        self.assertEqual(msg.get_filename(), 'This is even more ***fun*** is it not.pdf')
        self.assertEqual(m, msg.as_string())

    def test_rfc2231_parse_extra_quoting(self):
        m = textwrap.dedent('            Content-Disposition: inline;\n            \tfilename*0*="\'\'This%20is%20even%20more%20";\n            \tfilename*1*="%2A%2A%2Afun%2A%2A%2A%20";\n            \tfilename*2="is it not.pdf"\n\n            ')
        msg = email.message_from_string(m)
        self.assertEqual(msg.get_filename(), 'This is even more ***fun*** is it not.pdf')
        self.assertEqual(m, msg.as_string())

    def test_rfc2231_no_language_or_charset(self):
        m = 'Content-Transfer-Encoding: 8bit\nContent-Disposition: inline; filename="file____C__DOCUMENTS_20AND_20SETTINGS_FABIEN_LOCAL_20SETTINGS_TEMP_nsmail.htm"\nContent-Type: text/html; NAME*0=file____C__DOCUMENTS_20AND_20SETTINGS_FABIEN_LOCAL_20SETTINGS_TEM; NAME*1=P_nsmail.htm\n\n'
        msg = email.message_from_string(m)
        param = msg.get_param('NAME')
        self.assertNotIsInstance(param, tuple)
        self.assertEqual(param, 'file____C__DOCUMENTS_20AND_20SETTINGS_FABIEN_LOCAL_20SETTINGS_TEMP_nsmail.htm')

    def test_rfc2231_no_language_or_charset_in_filename(self):
        m = 'Content-Disposition: inline;\n\tfilename*0*="\'\'This%20is%20even%20more%20";\n\tfilename*1*="%2A%2A%2Afun%2A%2A%2A%20";\n\tfilename*2="is it not.pdf"\n\n'
        msg = email.message_from_string(m)
        self.assertEqual(msg.get_filename(), 'This is even more ***fun*** is it not.pdf')

    def test_rfc2231_no_language_or_charset_in_filename_encoded(self):
        m = 'Content-Disposition: inline;\n\tfilename*0*="\'\'This%20is%20even%20more%20";\n\tfilename*1*="%2A%2A%2Afun%2A%2A%2A%20";\n\tfilename*2="is it not.pdf"\n\n'
        msg = email.message_from_string(m)
        self.assertEqual(msg.get_filename(), 'This is even more ***fun*** is it not.pdf')

    def test_rfc2231_partly_encoded(self):
        m = 'Content-Disposition: inline;\n\tfilename*0="\'\'This%20is%20even%20more%20";\n\tfilename*1*="%2A%2A%2Afun%2A%2A%2A%20";\n\tfilename*2="is it not.pdf"\n\n'
        msg = email.message_from_string(m)
        self.assertEqual(msg.get_filename(), 'This%20is%20even%20more%20***fun*** is it not.pdf')

    def test_rfc2231_partly_nonencoded(self):
        m = 'Content-Disposition: inline;\n\tfilename*0="This%20is%20even%20more%20";\n\tfilename*1="%2A%2A%2Afun%2A%2A%2A%20";\n\tfilename*2="is it not.pdf"\n\n'
        msg = email.message_from_string(m)
        self.assertEqual(msg.get_filename(), 'This%20is%20even%20more%20%2A%2A%2Afun%2A%2A%2A%20is it not.pdf')

    def test_rfc2231_no_language_or_charset_in_boundary(self):
        m = 'Content-Type: multipart/alternative;\n\tboundary*0*="\'\'This%20is%20even%20more%20";\n\tboundary*1*="%2A%2A%2Afun%2A%2A%2A%20";\n\tboundary*2="is it not.pdf"\n\n'
        msg = email.message_from_string(m)
        self.assertEqual(msg.get_boundary(), 'This is even more ***fun*** is it not.pdf')

    def test_rfc2231_no_language_or_charset_in_charset(self):
        m = 'Content-Type: text/plain;\n\tcharset*0*="This%20is%20even%20more%20";\n\tcharset*1*="%2A%2A%2Afun%2A%2A%2A%20";\n\tcharset*2="is it not.pdf"\n\n'
        msg = email.message_from_string(m)
        self.assertEqual(msg.get_content_charset(), 'this is even more ***fun*** is it not.pdf')

    def test_rfc2231_bad_encoding_in_filename(self):
        m = 'Content-Disposition: inline;\n\tfilename*0*="bogus\'xx\'This%20is%20even%20more%20";\n\tfilename*1*="%2A%2A%2Afun%2A%2A%2A%20";\n\tfilename*2="is it not.pdf"\n\n'
        msg = email.message_from_string(m)
        self.assertEqual(msg.get_filename(), 'This is even more ***fun*** is it not.pdf')

    def test_rfc2231_bad_encoding_in_charset(self):
        m = "Content-Type: text/plain; charset*=bogus''utf-8%E2%80%9D\n\n"
        msg = email.message_from_string(m)
        self.assertEqual(msg.get_content_charset(), None)

    def test_rfc2231_bad_character_in_charset(self):
        m = "Content-Type: text/plain; charset*=ascii''utf-8%E2%80%9D\n\n"
        msg = email.message_from_string(m)
        self.assertEqual(msg.get_content_charset(), None)

    def test_rfc2231_bad_character_in_filename(self):
        m = 'Content-Disposition: inline;\n\tfilename*0*="ascii\'xx\'This%20is%20even%20more%20";\n\tfilename*1*="%2A%2A%2Afun%2A%2A%2A%20";\n\tfilename*2*="is it not.pdf%E2"\n\n'
        msg = email.message_from_string(m)
        self.assertEqual(msg.get_filename(), 'This is even more ***fun*** is it not.pdf�')

    def test_rfc2231_unknown_encoding(self):
        m = "Content-Transfer-Encoding: 8bit\nContent-Disposition: inline; filename*=X-UNKNOWN''myfile.txt\n\n"
        msg = email.message_from_string(m)
        self.assertEqual(msg.get_filename(), 'myfile.txt')

    def test_rfc2231_single_tick_in_filename_extended(self):
        eq = self.assertEqual
        m = 'Content-Type: application/x-foo;\n\tname*0*="Frank\'s"; name*1*=" Document"\n\n'
        msg = email.message_from_string(m)
        (charset, language, s) = msg.get_param('name')
        eq(charset, None)
        eq(language, None)
        eq(s, "Frank's Document")

    def test_rfc2231_single_tick_in_filename(self):
        m = 'Content-Type: application/x-foo; name*0="Frank\'s"; name*1=" Document"\n\n'
        msg = email.message_from_string(m)
        param = msg.get_param('name')
        self.assertNotIsInstance(param, tuple)
        self.assertEqual(param, "Frank's Document")

    def test_rfc2231_missing_tick(self):
        m = 'Content-Disposition: inline;\n\tfilename*0*="\'This%20is%20broken";\n'
        msg = email.message_from_string(m)
        self.assertEqual(msg.get_filename(), "'This is broken")

    def test_rfc2231_missing_tick_with_encoded_non_ascii(self):
        m = 'Content-Disposition: inline;\n\tfilename*0*="\'This%20is%E2broken";\n'
        msg = email.message_from_string(m)
        self.assertEqual(msg.get_filename(), "'This is�broken")

    def test_rfc2231_tick_attack_extended(self):
        eq = self.assertEqual
        m = 'Content-Type: application/x-foo;\n\tname*0*="us-ascii\'en-us\'Frank\'s"; name*1*=" Document"\n\n'
        msg = email.message_from_string(m)
        (charset, language, s) = msg.get_param('name')
        eq(charset, 'us-ascii')
        eq(language, 'en-us')
        eq(s, "Frank's Document")

    def test_rfc2231_tick_attack(self):
        m = 'Content-Type: application/x-foo;\n\tname*0="us-ascii\'en-us\'Frank\'s"; name*1=" Document"\n\n'
        msg = email.message_from_string(m)
        param = msg.get_param('name')
        self.assertNotIsInstance(param, tuple)
        self.assertEqual(param, "us-ascii'en-us'Frank's Document")

    def test_rfc2231_no_extended_values(self):
        eq = self.assertEqual
        m = 'Content-Type: application/x-foo; name="Frank\'s Document"\n\n'
        msg = email.message_from_string(m)
        eq(msg.get_param('name'), "Frank's Document")

    def test_rfc2231_encoded_then_unencoded_segments(self):
        eq = self.assertEqual
        m = 'Content-Type: application/x-foo;\n\tname*0*="us-ascii\'en-us\'My";\n\tname*1=" Document";\n\tname*2*=" For You"\n\n'
        msg = email.message_from_string(m)
        (charset, language, s) = msg.get_param('name')
        eq(charset, 'us-ascii')
        eq(language, 'en-us')
        eq(s, 'My Document For You')

    def test_rfc2231_unencoded_then_encoded_segments(self):
        eq = self.assertEqual
        m = 'Content-Type: application/x-foo;\n\tname*0="us-ascii\'en-us\'My";\n\tname*1*=" Document";\n\tname*2*=" For You"\n\n'
        msg = email.message_from_string(m)
        (charset, language, s) = msg.get_param('name')
        eq(charset, 'us-ascii')
        eq(language, 'en-us')
        eq(s, 'My Document For You')

    def test_should_not_hang_on_invalid_ew_messages(self):
        messages = ['From: user@host.com\nTo: user@host.com\nBad-Header:\n =?us-ascii?Q?LCSwrV11+IB0rSbSker+M9vWR7wEDSuGqmHD89Gt=ea0nJFSaiz4vX3XMJPT4vrE?=\n =?us-ascii?Q?xGUZeOnp0o22pLBB7CYLH74Js=wOlK6Tfru2U47qR?=\n =?us-ascii?Q?72OfyEY2p2=2FrA9xNFyvH+fBTCmazxwzF8nGkK6D?=\n\nHello!\n', 'From: ï¿½ï¿½ï¿½ï¿½ï¿½ ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ <xxx@xxx>\nTo: "xxx" <xxx@xxx>\nSubject:   ï¿½ï¿½ï¿½ ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ ï¿½ï¿½ï¿½ï¿½ï¿½ ï¿½ï¿½ï¿½ï¿½ï¿½ ï¿½ ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ ï¿½ï¿½ ï¿½ï¿½ï¿½ï¿½\nMIME-Version: 1.0\nContent-Type: text/plain; charset="windows-1251";\nContent-Transfer-Encoding: 8bit\n\nï¿½ï¿½ ï¿½ï¿½ï¿½ï¿½ï¿½ ï¿½ ï¿½ï¿½ï¿½ï¿½ ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ ï¿½ï¿½ï¿½ ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½ï¿½\n']
        for m in messages:
            with self.subTest(m=m):
                msg = email.message_from_string(m)

class TestSigned(TestEmailBase):

    def _msg_and_obj(self, filename):
        with openfile(filename) as fp:
            original = fp.read()
            msg = email.message_from_string(original)
        return (original, msg)

    def _signed_parts_eq(self, original, result):
        import re
        repart = re.compile('^--([^\\n]+)\\n(.*?)\\n--\\1$', (re.S | re.M))
        inpart = repart.search(original).group(2)
        outpart = repart.search(result).group(2)
        self.assertEqual(outpart, inpart)

    def test_long_headers_as_string(self):
        (original, msg) = self._msg_and_obj('msg_45.txt')
        result = msg.as_string()
        self._signed_parts_eq(original, result)

    def test_long_headers_as_string_maxheaderlen(self):
        (original, msg) = self._msg_and_obj('msg_45.txt')
        result = msg.as_string(maxheaderlen=60)
        self._signed_parts_eq(original, result)

    def test_long_headers_flatten(self):
        (original, msg) = self._msg_and_obj('msg_45.txt')
        fp = StringIO()
        Generator(fp).flatten(msg)
        result = fp.getvalue()
        self._signed_parts_eq(original, result)
if (__name__ == '__main__'):
    unittest.main()
