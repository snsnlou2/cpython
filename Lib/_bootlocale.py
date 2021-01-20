
"A minimal subset of the locale module used at interpreter startup\n(imported by the _io module), in order to reduce startup time.\n\nDon't import directly from third-party code; use the `locale` module instead!\n"
import sys
import _locale
if sys.platform.startswith('win'):

    def getpreferredencoding(do_setlocale=True):
        if sys.flags.utf8_mode:
            return 'UTF-8'
        return _locale._getdefaultlocale()[1]
else:
    try:
        _locale.CODESET
    except AttributeError:
        if hasattr(sys, 'getandroidapilevel'):

            def getpreferredencoding(do_setlocale=True):
                return 'UTF-8'
        else:

            def getpreferredencoding(do_setlocale=True):
                if sys.flags.utf8_mode:
                    return 'UTF-8'
                import locale
                return locale.getpreferredencoding(do_setlocale)
    else:

        def getpreferredencoding(do_setlocale=True):
            assert (not do_setlocale)
            if sys.flags.utf8_mode:
                return 'UTF-8'
            result = _locale.nl_langinfo(_locale.CODESET)
            if ((not result) and (sys.platform == 'darwin')):
                result = 'UTF-8'
            return result
