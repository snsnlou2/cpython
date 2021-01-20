
'Class representing audio/* type MIME documents.'
__all__ = ['MIMEAudio']
import sndhdr
from io import BytesIO
from email import encoders
from email.mime.nonmultipart import MIMENonMultipart
_sndhdr_MIMEmap = {'au': 'basic', 'wav': 'x-wav', 'aiff': 'x-aiff', 'aifc': 'x-aiff'}

def _whatsnd(data):
    "Try to identify a sound file type.\n\n    sndhdr.what() has a pretty cruddy interface, unfortunately.  This is why\n    we re-do it here.  It would be easier to reverse engineer the Unix 'file'\n    command and use the standard 'magic' file, as shipped with a modern Unix.\n    "
    hdr = data[:512]
    fakefile = BytesIO(hdr)
    for testfn in sndhdr.tests:
        res = testfn(hdr, fakefile)
        if (res is not None):
            return _sndhdr_MIMEmap.get(res[0])
    return None

class MIMEAudio(MIMENonMultipart):
    'Class for generating audio/* MIME documents.'

    def __init__(self, _audiodata, _subtype=None, _encoder=encoders.encode_base64, *, policy=None, **_params):
        "Create an audio/* type MIME document.\n\n        _audiodata is a string containing the raw audio data.  If this data\n        can be decoded by the standard Python `sndhdr' module, then the\n        subtype will be automatically included in the Content-Type header.\n        Otherwise, you can specify  the specific audio subtype via the\n        _subtype parameter.  If _subtype is not given, and no subtype can be\n        guessed, a TypeError is raised.\n\n        _encoder is a function which will perform the actual encoding for\n        transport of the image data.  It takes one argument, which is this\n        Image instance.  It should use get_payload() and set_payload() to\n        change the payload to the encoded form.  It should also add any\n        Content-Transfer-Encoding or other headers to the message as\n        necessary.  The default encoding is Base64.\n\n        Any additional keyword arguments are passed to the base class\n        constructor, which turns them into parameters on the Content-Type\n        header.\n        "
        if (_subtype is None):
            _subtype = _whatsnd(_audiodata)
        if (_subtype is None):
            raise TypeError('Could not find audio MIME subtype')
        MIMENonMultipart.__init__(self, 'audio', _subtype, policy=policy, **_params)
        self.set_payload(_audiodata)
        _encoder(self)
