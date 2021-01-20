
'Various types of useful iterators and generators.'
__all__ = ['body_line_iterator', 'typed_subpart_iterator', 'walk']
import sys
from io import StringIO

def walk(self):
    'Walk over the message tree, yielding each subpart.\n\n    The walk is performed in depth-first order.  This method is a\n    generator.\n    '
    (yield self)
    if self.is_multipart():
        for subpart in self.get_payload():
            (yield from subpart.walk())

def body_line_iterator(msg, decode=False):
    'Iterate over the parts, returning string payloads line-by-line.\n\n    Optional decode (default False) is passed through to .get_payload().\n    '
    for subpart in msg.walk():
        payload = subpart.get_payload(decode=decode)
        if isinstance(payload, str):
            (yield from StringIO(payload))

def typed_subpart_iterator(msg, maintype='text', subtype=None):
    'Iterate over the subparts with a given MIME type.\n\n    Use `maintype\' as the main MIME type to match against; this defaults to\n    "text".  Optional `subtype\' is the MIME subtype to match against; if\n    omitted, only the main type is matched.\n    '
    for subpart in msg.walk():
        if (subpart.get_content_maintype() == maintype):
            if ((subtype is None) or (subpart.get_content_subtype() == subtype)):
                (yield subpart)

def _structure(msg, fp=None, level=0, include_default=False):
    'A handy debugging aid'
    if (fp is None):
        fp = sys.stdout
    tab = (' ' * (level * 4))
    print((tab + msg.get_content_type()), end='', file=fp)
    if include_default:
        print((' [%s]' % msg.get_default_type()), file=fp)
    else:
        print(file=fp)
    if msg.is_multipart():
        for subpart in msg.get_payload():
            _structure(subpart, fp, (level + 1), include_default)
