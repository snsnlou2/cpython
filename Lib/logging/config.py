
"\nConfiguration functions for the logging package for Python. The core package\nis based on PEP 282 and comments thereto in comp.lang.python, and influenced\nby Apache's log4j system.\n\nCopyright (C) 2001-2019 Vinay Sajip. All Rights Reserved.\n\nTo use, simply 'import logging' and log away!\n"
import errno
import io
import logging
import logging.handlers
import re
import struct
import sys
import threading
import traceback
from socketserver import ThreadingTCPServer, StreamRequestHandler
DEFAULT_LOGGING_CONFIG_PORT = 9030
RESET_ERROR = errno.ECONNRESET
_listener = None

def fileConfig(fname, defaults=None, disable_existing_loggers=True):
    '\n    Read the logging configuration from a ConfigParser-format file.\n\n    This can be called several times from an application, allowing an end user\n    the ability to select from various pre-canned configurations (if the\n    developer provides a mechanism to present the choices and load the chosen\n    configuration).\n    '
    import configparser
    if isinstance(fname, configparser.RawConfigParser):
        cp = fname
    else:
        cp = configparser.ConfigParser(defaults)
        if hasattr(fname, 'readline'):
            cp.read_file(fname)
        else:
            cp.read(fname)
    formatters = _create_formatters(cp)
    logging._acquireLock()
    try:
        _clearExistingHandlers()
        handlers = _install_handlers(cp, formatters)
        _install_loggers(cp, handlers, disable_existing_loggers)
    finally:
        logging._releaseLock()

def _resolve(name):
    'Resolve a dotted name to a global object.'
    name = name.split('.')
    used = name.pop(0)
    found = __import__(used)
    for n in name:
        used = ((used + '.') + n)
        try:
            found = getattr(found, n)
        except AttributeError:
            __import__(used)
            found = getattr(found, n)
    return found

def _strip_spaces(alist):
    return map(str.strip, alist)

def _create_formatters(cp):
    'Create and return formatters'
    flist = cp['formatters']['keys']
    if (not len(flist)):
        return {}
    flist = flist.split(',')
    flist = _strip_spaces(flist)
    formatters = {}
    for form in flist:
        sectname = ('formatter_%s' % form)
        fs = cp.get(sectname, 'format', raw=True, fallback=None)
        dfs = cp.get(sectname, 'datefmt', raw=True, fallback=None)
        stl = cp.get(sectname, 'style', raw=True, fallback='%')
        c = logging.Formatter
        class_name = cp[sectname].get('class')
        if class_name:
            c = _resolve(class_name)
        f = c(fs, dfs, stl)
        formatters[form] = f
    return formatters

def _install_handlers(cp, formatters):
    'Install and return handlers'
    hlist = cp['handlers']['keys']
    if (not len(hlist)):
        return {}
    hlist = hlist.split(',')
    hlist = _strip_spaces(hlist)
    handlers = {}
    fixups = []
    for hand in hlist:
        section = cp[('handler_%s' % hand)]
        klass = section['class']
        fmt = section.get('formatter', '')
        try:
            klass = eval(klass, vars(logging))
        except (AttributeError, NameError):
            klass = _resolve(klass)
        args = section.get('args', '()')
        args = eval(args, vars(logging))
        kwargs = section.get('kwargs', '{}')
        kwargs = eval(kwargs, vars(logging))
        h = klass(*args, **kwargs)
        h.name = hand
        if ('level' in section):
            level = section['level']
            h.setLevel(level)
        if len(fmt):
            h.setFormatter(formatters[fmt])
        if issubclass(klass, logging.handlers.MemoryHandler):
            target = section.get('target', '')
            if len(target):
                fixups.append((h, target))
        handlers[hand] = h
    for (h, t) in fixups:
        h.setTarget(handlers[t])
    return handlers

def _handle_existing_loggers(existing, child_loggers, disable_existing):
    "\n    When (re)configuring logging, handle loggers which were in the previous\n    configuration but are not in the new configuration. There's no point\n    deleting them as other threads may continue to hold references to them;\n    and by disabling them, you stop them doing any logging.\n\n    However, don't disable children of named loggers, as that's probably not\n    what was intended by the user. Also, allow existing loggers to NOT be\n    disabled if disable_existing is false.\n    "
    root = logging.root
    for log in existing:
        logger = root.manager.loggerDict[log]
        if (log in child_loggers):
            if (not isinstance(logger, logging.PlaceHolder)):
                logger.setLevel(logging.NOTSET)
                logger.handlers = []
                logger.propagate = True
        else:
            logger.disabled = disable_existing

def _install_loggers(cp, handlers, disable_existing):
    'Create and install loggers'
    llist = cp['loggers']['keys']
    llist = llist.split(',')
    llist = list(_strip_spaces(llist))
    llist.remove('root')
    section = cp['logger_root']
    root = logging.root
    log = root
    if ('level' in section):
        level = section['level']
        log.setLevel(level)
    for h in root.handlers[:]:
        root.removeHandler(h)
    hlist = section['handlers']
    if len(hlist):
        hlist = hlist.split(',')
        hlist = _strip_spaces(hlist)
        for hand in hlist:
            log.addHandler(handlers[hand])
    existing = list(root.manager.loggerDict.keys())
    existing.sort()
    child_loggers = []
    for log in llist:
        section = cp[('logger_%s' % log)]
        qn = section['qualname']
        propagate = section.getint('propagate', fallback=1)
        logger = logging.getLogger(qn)
        if (qn in existing):
            i = (existing.index(qn) + 1)
            prefixed = (qn + '.')
            pflen = len(prefixed)
            num_existing = len(existing)
            while (i < num_existing):
                if (existing[i][:pflen] == prefixed):
                    child_loggers.append(existing[i])
                i += 1
            existing.remove(qn)
        if ('level' in section):
            level = section['level']
            logger.setLevel(level)
        for h in logger.handlers[:]:
            logger.removeHandler(h)
        logger.propagate = propagate
        logger.disabled = 0
        hlist = section['handlers']
        if len(hlist):
            hlist = hlist.split(',')
            hlist = _strip_spaces(hlist)
            for hand in hlist:
                logger.addHandler(handlers[hand])
    _handle_existing_loggers(existing, child_loggers, disable_existing)

def _clearExistingHandlers():
    'Clear and close existing handlers'
    logging._handlers.clear()
    logging.shutdown(logging._handlerList[:])
    del logging._handlerList[:]
IDENTIFIER = re.compile('^[a-z_][a-z0-9_]*$', re.I)

def valid_ident(s):
    m = IDENTIFIER.match(s)
    if (not m):
        raise ValueError(('Not a valid Python identifier: %r' % s))
    return True

class ConvertingMixin(object):
    "For ConvertingXXX's, this mixin class provides common functions"

    def convert_with_key(self, key, value, replace=True):
        result = self.configurator.convert(value)
        if (value is not result):
            if replace:
                self[key] = result
            if (type(result) in (ConvertingDict, ConvertingList, ConvertingTuple)):
                result.parent = self
                result.key = key
        return result

    def convert(self, value):
        result = self.configurator.convert(value)
        if (value is not result):
            if (type(result) in (ConvertingDict, ConvertingList, ConvertingTuple)):
                result.parent = self
        return result

class ConvertingDict(dict, ConvertingMixin):
    'A converting dictionary wrapper.'

    def __getitem__(self, key):
        value = dict.__getitem__(self, key)
        return self.convert_with_key(key, value)

    def get(self, key, default=None):
        value = dict.get(self, key, default)
        return self.convert_with_key(key, value)

    def pop(self, key, default=None):
        value = dict.pop(self, key, default)
        return self.convert_with_key(key, value, replace=False)

class ConvertingList(list, ConvertingMixin):
    'A converting list wrapper.'

    def __getitem__(self, key):
        value = list.__getitem__(self, key)
        return self.convert_with_key(key, value)

    def pop(self, idx=(- 1)):
        value = list.pop(self, idx)
        return self.convert(value)

class ConvertingTuple(tuple, ConvertingMixin):
    'A converting tuple wrapper.'

    def __getitem__(self, key):
        value = tuple.__getitem__(self, key)
        return self.convert_with_key(key, value, replace=False)

class BaseConfigurator(object):
    '\n    The configurator base class which defines some useful defaults.\n    '
    CONVERT_PATTERN = re.compile('^(?P<prefix>[a-z]+)://(?P<suffix>.*)$')
    WORD_PATTERN = re.compile('^\\s*(\\w+)\\s*')
    DOT_PATTERN = re.compile('^\\.\\s*(\\w+)\\s*')
    INDEX_PATTERN = re.compile('^\\[\\s*(\\w+)\\s*\\]\\s*')
    DIGIT_PATTERN = re.compile('^\\d+$')
    value_converters = {'ext': 'ext_convert', 'cfg': 'cfg_convert'}
    importer = staticmethod(__import__)

    def __init__(self, config):
        self.config = ConvertingDict(config)
        self.config.configurator = self

    def resolve(self, s):
        '\n        Resolve strings to objects using standard import and attribute\n        syntax.\n        '
        name = s.split('.')
        used = name.pop(0)
        try:
            found = self.importer(used)
            for frag in name:
                used += ('.' + frag)
                try:
                    found = getattr(found, frag)
                except AttributeError:
                    self.importer(used)
                    found = getattr(found, frag)
            return found
        except ImportError:
            (e, tb) = sys.exc_info()[1:]
            v = ValueError(('Cannot resolve %r: %s' % (s, e)))
            (v.__cause__, v.__traceback__) = (e, tb)
            raise v

    def ext_convert(self, value):
        'Default converter for the ext:// protocol.'
        return self.resolve(value)

    def cfg_convert(self, value):
        'Default converter for the cfg:// protocol.'
        rest = value
        m = self.WORD_PATTERN.match(rest)
        if (m is None):
            raise ValueError(('Unable to convert %r' % value))
        else:
            rest = rest[m.end():]
            d = self.config[m.groups()[0]]
            while rest:
                m = self.DOT_PATTERN.match(rest)
                if m:
                    d = d[m.groups()[0]]
                else:
                    m = self.INDEX_PATTERN.match(rest)
                    if m:
                        idx = m.groups()[0]
                        if (not self.DIGIT_PATTERN.match(idx)):
                            d = d[idx]
                        else:
                            try:
                                n = int(idx)
                                d = d[n]
                            except TypeError:
                                d = d[idx]
                if m:
                    rest = rest[m.end():]
                else:
                    raise ValueError(('Unable to convert %r at %r' % (value, rest)))
        return d

    def convert(self, value):
        '\n        Convert values to an appropriate type. dicts, lists and tuples are\n        replaced by their converting alternatives. Strings are checked to\n        see if they have a conversion format and are converted if they do.\n        '
        if ((not isinstance(value, ConvertingDict)) and isinstance(value, dict)):
            value = ConvertingDict(value)
            value.configurator = self
        elif ((not isinstance(value, ConvertingList)) and isinstance(value, list)):
            value = ConvertingList(value)
            value.configurator = self
        elif ((not isinstance(value, ConvertingTuple)) and isinstance(value, tuple) and (not hasattr(value, '_fields'))):
            value = ConvertingTuple(value)
            value.configurator = self
        elif isinstance(value, str):
            m = self.CONVERT_PATTERN.match(value)
            if m:
                d = m.groupdict()
                prefix = d['prefix']
                converter = self.value_converters.get(prefix, None)
                if converter:
                    suffix = d['suffix']
                    converter = getattr(self, converter)
                    value = converter(suffix)
        return value

    def configure_custom(self, config):
        'Configure an object with a user-supplied factory.'
        c = config.pop('()')
        if (not callable(c)):
            c = self.resolve(c)
        props = config.pop('.', None)
        kwargs = {k: config[k] for k in config if valid_ident(k)}
        result = c(**kwargs)
        if props:
            for (name, value) in props.items():
                setattr(result, name, value)
        return result

    def as_tuple(self, value):
        'Utility function which converts lists to tuples.'
        if isinstance(value, list):
            value = tuple(value)
        return value

class DictConfigurator(BaseConfigurator):
    '\n    Configure logging using a dictionary-like object to describe the\n    configuration.\n    '

    def configure(self):
        'Do the configuration.'
        config = self.config
        if ('version' not in config):
            raise ValueError("dictionary doesn't specify a version")
        if (config['version'] != 1):
            raise ValueError(('Unsupported version: %s' % config['version']))
        incremental = config.pop('incremental', False)
        EMPTY_DICT = {}
        logging._acquireLock()
        try:
            if incremental:
                handlers = config.get('handlers', EMPTY_DICT)
                for name in handlers:
                    if (name not in logging._handlers):
                        raise ValueError(('No handler found with name %r' % name))
                    else:
                        try:
                            handler = logging._handlers[name]
                            handler_config = handlers[name]
                            level = handler_config.get('level', None)
                            if level:
                                handler.setLevel(logging._checkLevel(level))
                        except Exception as e:
                            raise ValueError(('Unable to configure handler %r' % name)) from e
                loggers = config.get('loggers', EMPTY_DICT)
                for name in loggers:
                    try:
                        self.configure_logger(name, loggers[name], True)
                    except Exception as e:
                        raise ValueError(('Unable to configure logger %r' % name)) from e
                root = config.get('root', None)
                if root:
                    try:
                        self.configure_root(root, True)
                    except Exception as e:
                        raise ValueError('Unable to configure root logger') from e
            else:
                disable_existing = config.pop('disable_existing_loggers', True)
                _clearExistingHandlers()
                formatters = config.get('formatters', EMPTY_DICT)
                for name in formatters:
                    try:
                        formatters[name] = self.configure_formatter(formatters[name])
                    except Exception as e:
                        raise ValueError(('Unable to configure formatter %r' % name)) from e
                filters = config.get('filters', EMPTY_DICT)
                for name in filters:
                    try:
                        filters[name] = self.configure_filter(filters[name])
                    except Exception as e:
                        raise ValueError(('Unable to configure filter %r' % name)) from e
                handlers = config.get('handlers', EMPTY_DICT)
                deferred = []
                for name in sorted(handlers):
                    try:
                        handler = self.configure_handler(handlers[name])
                        handler.name = name
                        handlers[name] = handler
                    except Exception as e:
                        if ('target not configured yet' in str(e.__cause__)):
                            deferred.append(name)
                        else:
                            raise ValueError(('Unable to configure handler %r' % name)) from e
                for name in deferred:
                    try:
                        handler = self.configure_handler(handlers[name])
                        handler.name = name
                        handlers[name] = handler
                    except Exception as e:
                        raise ValueError(('Unable to configure handler %r' % name)) from e
                root = logging.root
                existing = list(root.manager.loggerDict.keys())
                existing.sort()
                child_loggers = []
                loggers = config.get('loggers', EMPTY_DICT)
                for name in loggers:
                    if (name in existing):
                        i = (existing.index(name) + 1)
                        prefixed = (name + '.')
                        pflen = len(prefixed)
                        num_existing = len(existing)
                        while (i < num_existing):
                            if (existing[i][:pflen] == prefixed):
                                child_loggers.append(existing[i])
                            i += 1
                        existing.remove(name)
                    try:
                        self.configure_logger(name, loggers[name])
                    except Exception as e:
                        raise ValueError(('Unable to configure logger %r' % name)) from e
                _handle_existing_loggers(existing, child_loggers, disable_existing)
                root = config.get('root', None)
                if root:
                    try:
                        self.configure_root(root)
                    except Exception as e:
                        raise ValueError('Unable to configure root logger') from e
        finally:
            logging._releaseLock()

    def configure_formatter(self, config):
        'Configure a formatter from a dictionary.'
        if ('()' in config):
            factory = config['()']
            try:
                result = self.configure_custom(config)
            except TypeError as te:
                if ("'format'" not in str(te)):
                    raise
                config['fmt'] = config.pop('format')
                config['()'] = factory
                result = self.configure_custom(config)
        else:
            fmt = config.get('format', None)
            dfmt = config.get('datefmt', None)
            style = config.get('style', '%')
            cname = config.get('class', None)
            if (not cname):
                c = logging.Formatter
            else:
                c = _resolve(cname)
            if ('validate' in config):
                result = c(fmt, dfmt, style, config['validate'])
            else:
                result = c(fmt, dfmt, style)
        return result

    def configure_filter(self, config):
        'Configure a filter from a dictionary.'
        if ('()' in config):
            result = self.configure_custom(config)
        else:
            name = config.get('name', '')
            result = logging.Filter(name)
        return result

    def add_filters(self, filterer, filters):
        'Add filters to a filterer from a list of names.'
        for f in filters:
            try:
                filterer.addFilter(self.config['filters'][f])
            except Exception as e:
                raise ValueError(('Unable to add filter %r' % f)) from e

    def configure_handler(self, config):
        'Configure a handler from a dictionary.'
        config_copy = dict(config)
        formatter = config.pop('formatter', None)
        if formatter:
            try:
                formatter = self.config['formatters'][formatter]
            except Exception as e:
                raise ValueError(('Unable to set formatter %r' % formatter)) from e
        level = config.pop('level', None)
        filters = config.pop('filters', None)
        if ('()' in config):
            c = config.pop('()')
            if (not callable(c)):
                c = self.resolve(c)
            factory = c
        else:
            cname = config.pop('class')
            klass = self.resolve(cname)
            if (issubclass(klass, logging.handlers.MemoryHandler) and ('target' in config)):
                try:
                    th = self.config['handlers'][config['target']]
                    if (not isinstance(th, logging.Handler)):
                        config.update(config_copy)
                        raise TypeError('target not configured yet')
                    config['target'] = th
                except Exception as e:
                    raise ValueError(('Unable to set target handler %r' % config['target'])) from e
            elif (issubclass(klass, logging.handlers.SMTPHandler) and ('mailhost' in config)):
                config['mailhost'] = self.as_tuple(config['mailhost'])
            elif (issubclass(klass, logging.handlers.SysLogHandler) and ('address' in config)):
                config['address'] = self.as_tuple(config['address'])
            factory = klass
        props = config.pop('.', None)
        kwargs = {k: config[k] for k in config if valid_ident(k)}
        try:
            result = factory(**kwargs)
        except TypeError as te:
            if ("'stream'" not in str(te)):
                raise
            kwargs['strm'] = kwargs.pop('stream')
            result = factory(**kwargs)
        if formatter:
            result.setFormatter(formatter)
        if (level is not None):
            result.setLevel(logging._checkLevel(level))
        if filters:
            self.add_filters(result, filters)
        if props:
            for (name, value) in props.items():
                setattr(result, name, value)
        return result

    def add_handlers(self, logger, handlers):
        'Add handlers to a logger from a list of names.'
        for h in handlers:
            try:
                logger.addHandler(self.config['handlers'][h])
            except Exception as e:
                raise ValueError(('Unable to add handler %r' % h)) from e

    def common_logger_config(self, logger, config, incremental=False):
        '\n        Perform configuration which is common to root and non-root loggers.\n        '
        level = config.get('level', None)
        if (level is not None):
            logger.setLevel(logging._checkLevel(level))
        if (not incremental):
            for h in logger.handlers[:]:
                logger.removeHandler(h)
            handlers = config.get('handlers', None)
            if handlers:
                self.add_handlers(logger, handlers)
            filters = config.get('filters', None)
            if filters:
                self.add_filters(logger, filters)

    def configure_logger(self, name, config, incremental=False):
        'Configure a non-root logger from a dictionary.'
        logger = logging.getLogger(name)
        self.common_logger_config(logger, config, incremental)
        propagate = config.get('propagate', None)
        if (propagate is not None):
            logger.propagate = propagate

    def configure_root(self, config, incremental=False):
        'Configure a root logger from a dictionary.'
        root = logging.getLogger()
        self.common_logger_config(root, config, incremental)
dictConfigClass = DictConfigurator

def dictConfig(config):
    'Configure logging using a dictionary.'
    dictConfigClass(config).configure()

def listen(port=DEFAULT_LOGGING_CONFIG_PORT, verify=None):
    '\n    Start up a socket server on the specified port, and listen for new\n    configurations.\n\n    These will be sent as a file suitable for processing by fileConfig().\n    Returns a Thread object on which you can call start() to start the server,\n    and which you can join() when appropriate. To stop the server, call\n    stopListening().\n\n    Use the ``verify`` argument to verify any bytes received across the wire\n    from a client. If specified, it should be a callable which receives a\n    single argument - the bytes of configuration data received across the\n    network - and it should return either ``None``, to indicate that the\n    passed in bytes could not be verified and should be discarded, or a\n    byte string which is then passed to the configuration machinery as\n    normal. Note that you can return transformed bytes, e.g. by decrypting\n    the bytes passed in.\n    '

    class ConfigStreamHandler(StreamRequestHandler):
        '\n        Handler for a logging configuration request.\n\n        It expects a completely new logging configuration and uses fileConfig\n        to install it.\n        '

        def handle(self):
            '\n            Handle a request.\n\n            Each request is expected to be a 4-byte length, packed using\n            struct.pack(">L", n), followed by the config file.\n            Uses fileConfig() to do the grunt work.\n            '
            try:
                conn = self.connection
                chunk = conn.recv(4)
                if (len(chunk) == 4):
                    slen = struct.unpack('>L', chunk)[0]
                    chunk = self.connection.recv(slen)
                    while (len(chunk) < slen):
                        chunk = (chunk + conn.recv((slen - len(chunk))))
                    if (self.server.verify is not None):
                        chunk = self.server.verify(chunk)
                    if (chunk is not None):
                        chunk = chunk.decode('utf-8')
                        try:
                            import json
                            d = json.loads(chunk)
                            assert isinstance(d, dict)
                            dictConfig(d)
                        except Exception:
                            file = io.StringIO(chunk)
                            try:
                                fileConfig(file)
                            except Exception:
                                traceback.print_exc()
                    if self.server.ready:
                        self.server.ready.set()
            except OSError as e:
                if (e.errno != RESET_ERROR):
                    raise

    class ConfigSocketReceiver(ThreadingTCPServer):
        '\n        A simple TCP socket-based logging config receiver.\n        '
        allow_reuse_address = 1

        def __init__(self, host='localhost', port=DEFAULT_LOGGING_CONFIG_PORT, handler=None, ready=None, verify=None):
            ThreadingTCPServer.__init__(self, (host, port), handler)
            logging._acquireLock()
            self.abort = 0
            logging._releaseLock()
            self.timeout = 1
            self.ready = ready
            self.verify = verify

        def serve_until_stopped(self):
            import select
            abort = 0
            while (not abort):
                (rd, wr, ex) = select.select([self.socket.fileno()], [], [], self.timeout)
                if rd:
                    self.handle_request()
                logging._acquireLock()
                abort = self.abort
                logging._releaseLock()
            self.server_close()

    class Server(threading.Thread):

        def __init__(self, rcvr, hdlr, port, verify):
            super(Server, self).__init__()
            self.rcvr = rcvr
            self.hdlr = hdlr
            self.port = port
            self.verify = verify
            self.ready = threading.Event()

        def run(self):
            server = self.rcvr(port=self.port, handler=self.hdlr, ready=self.ready, verify=self.verify)
            if (self.port == 0):
                self.port = server.server_address[1]
            self.ready.set()
            global _listener
            logging._acquireLock()
            _listener = server
            logging._releaseLock()
            server.serve_until_stopped()
    return Server(ConfigSocketReceiver, ConfigStreamHandler, port, verify)

def stopListening():
    '\n    Stop the listening server which was created with a call to listen().\n    '
    global _listener
    logging._acquireLock()
    try:
        if _listener:
            _listener.abort = 1
            _listener = None
    finally:
        logging._releaseLock()
