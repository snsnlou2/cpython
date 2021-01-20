
"Base64 content transfer encoding per RFCs 2045-2047.\n\nThis module handles the content transfer encoding method defined in RFC 2045\nto encode arbitrary 8-bit data using the three 8-bit bytes in four 7-bit\ncharacters encoding known as Base64.\n\nIt is used in the MIME standards for email to attach images, audio, and text\nusing some 8-bit character sets to messages.\n\nThis module provides an interface to encode and decode both headers and bodies\nwith Base64 encoding.\n\nRFC 2045 defines a method for including character set information in an\n`encoded-word' in a header.  This method is commonly used for 8-bit real names\nin To:, From:, Cc:, etc. fields, as well as Subject: lines.\n\nThis module does not do the line wrapping or end-of-line character conversion\nnecessary for proper internationalized headers; it only does dumb encoding and\ndecoding.  To deal with the various line wrapping issues, use the email.header\nmodule.\n"
__all__ = ['body_decode', 'body_encode', 'decode', 'decodestring', 'header_encode', 'header_length']
from base64 import b64encode
from binascii import b2a_base64, a2b_base64
CRLF = '\r\n'
NL = '\n'
EMPTYSTRING = ''
MISC_LEN = 7

def header_length(bytearray):
    'Return the length of s when it is encoded with base64.'
    (groups_of_3, leftover) = divmod(len(bytearray), 3)
    n = (groups_of_3 * 4)
    if leftover:
        n += 4
    return n

def header_encode(header_bytes, charset='iso-8859-1'):
    'Encode a single header line with Base64 encoding in a given charset.\n\n    charset names the character set to use to encode the header.  It defaults\n    to iso-8859-1.  Base64 encoding is defined in RFC 2045.\n    '
    if (not header_bytes):
        return ''
    if isinstance(header_bytes, str):
        header_bytes = header_bytes.encode(charset)
    encoded = b64encode(header_bytes).decode('ascii')
    return ('=?%s?b?%s?=' % (charset, encoded))

def body_encode(s, maxlinelen=76, eol=NL):
    'Encode a string with base64.\n\n    Each line will be wrapped at, at most, maxlinelen characters (defaults to\n    76 characters).\n\n    Each line of encoded text will end with eol, which defaults to "\\n".  Set\n    this to "\\r\\n" if you will be using the result of this function directly\n    in an email.\n    '
    if (not s):
        return s
    encvec = []
    max_unencoded = ((maxlinelen * 3) // 4)
    for i in range(0, len(s), max_unencoded):
        enc = b2a_base64(s[i:(i + max_unencoded)]).decode('ascii')
        if (enc.endswith(NL) and (eol != NL)):
            enc = (enc[:(- 1)] + eol)
        encvec.append(enc)
    return EMPTYSTRING.join(encvec)

def decode(string):
    'Decode a raw base64 string, returning a bytes object.\n\n    This function does not parse a full MIME header value encoded with\n    base64 (like =?iso-8859-1?b?bmloISBuaWgh?=) -- please use the high\n    level email.header class for that functionality.\n    '
    if (not string):
        return bytes()
    elif isinstance(string, str):
        return a2b_base64(string.encode('raw-unicode-escape'))
    else:
        return a2b_base64(string)
body_decode = decode
decodestring = decode
