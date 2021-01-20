
"Exception classes raised by urllib.\n\nThe base exception class is URLError, which inherits from OSError.  It\ndoesn't define any behavior of its own, but is the base class for all\nexceptions defined in this package.\n\nHTTPError is an exception class that is also a valid HTTP response\ninstance.  It behaves this way because HTTP protocol errors are valid\nresponses, with a status code, headers, and a body.  In some contexts,\nan application may want to handle an exception like a regular\nresponse.\n"
import urllib.response
__all__ = ['URLError', 'HTTPError', 'ContentTooShortError']

class URLError(OSError):

    def __init__(self, reason, filename=None):
        self.args = (reason,)
        self.reason = reason
        if (filename is not None):
            self.filename = filename

    def __str__(self):
        return ('<urlopen error %s>' % self.reason)

class HTTPError(URLError, urllib.response.addinfourl):
    'Raised when HTTP error occurs, but also acts like non-error return'
    __super_init = urllib.response.addinfourl.__init__

    def __init__(self, url, code, msg, hdrs, fp):
        self.code = code
        self.msg = msg
        self.hdrs = hdrs
        self.fp = fp
        self.filename = url
        if (fp is not None):
            self.__super_init(fp, hdrs, url, code)

    def __str__(self):
        return ('HTTP Error %s: %s' % (self.code, self.msg))

    def __repr__(self):
        return ('<HTTPError %s: %r>' % (self.code, self.msg))

    @property
    def reason(self):
        return self.msg

    @property
    def headers(self):
        return self.hdrs

    @headers.setter
    def headers(self, headers):
        self.hdrs = headers

class ContentTooShortError(URLError):
    'Exception raised when downloaded size does not match content-length.'

    def __init__(self, message, content):
        URLError.__init__(self, message)
        self.content = content
