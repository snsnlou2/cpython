
'Mailcap file handling.  See RFC 1524.'
import os
import warnings
__all__ = ['getcaps', 'findmatch']

def lineno_sort_key(entry):
    if ('lineno' in entry):
        return (0, entry['lineno'])
    else:
        return (1, 0)

def getcaps():
    'Return a dictionary containing the mailcap database.\n\n    The dictionary maps a MIME type (in all lowercase, e.g. \'text/plain\')\n    to a list of dictionaries corresponding to mailcap entries.  The list\n    collects all the entries for that MIME type from all available mailcap\n    files.  Each dictionary contains key-value pairs for that MIME type,\n    where the viewing command is stored with the key "view".\n\n    '
    caps = {}
    lineno = 0
    for mailcap in listmailcapfiles():
        try:
            fp = open(mailcap, 'r')
        except OSError:
            continue
        with fp:
            (morecaps, lineno) = _readmailcapfile(fp, lineno)
        for (key, value) in morecaps.items():
            if (not (key in caps)):
                caps[key] = value
            else:
                caps[key] = (caps[key] + value)
    return caps

def listmailcapfiles():
    'Return a list of all mailcap files found on the system.'
    if ('MAILCAPS' in os.environ):
        pathstr = os.environ['MAILCAPS']
        mailcaps = pathstr.split(os.pathsep)
    else:
        if ('HOME' in os.environ):
            home = os.environ['HOME']
        else:
            home = '.'
        mailcaps = [(home + '/.mailcap'), '/etc/mailcap', '/usr/etc/mailcap', '/usr/local/etc/mailcap']
    return mailcaps

def readmailcapfile(fp):
    'Read a mailcap file and return a dictionary keyed by MIME type.'
    warnings.warn('readmailcapfile is deprecated, use getcaps instead', DeprecationWarning, 2)
    (caps, _) = _readmailcapfile(fp, None)
    return caps

def _readmailcapfile(fp, lineno):
    'Read a mailcap file and return a dictionary keyed by MIME type.\n\n    Each MIME type is mapped to an entry consisting of a list of\n    dictionaries; the list will contain more than one such dictionary\n    if a given MIME type appears more than once in the mailcap file.\n    Each dictionary contains key-value pairs for that MIME type, where\n    the viewing command is stored with the key "view".\n    '
    caps = {}
    while 1:
        line = fp.readline()
        if (not line):
            break
        if ((line[0] == '#') or (line.strip() == '')):
            continue
        nextline = line
        while (nextline[(- 2):] == '\\\n'):
            nextline = fp.readline()
            if (not nextline):
                nextline = '\n'
            line = (line[:(- 2)] + nextline)
        (key, fields) = parseline(line)
        if (not (key and fields)):
            continue
        if (lineno is not None):
            fields['lineno'] = lineno
            lineno += 1
        types = key.split('/')
        for j in range(len(types)):
            types[j] = types[j].strip()
        key = '/'.join(types).lower()
        if (key in caps):
            caps[key].append(fields)
        else:
            caps[key] = [fields]
    return (caps, lineno)

def parseline(line):
    'Parse one entry in a mailcap file and return a dictionary.\n\n    The viewing command is stored as the value with the key "view",\n    and the rest of the fields produce key-value pairs in the dict.\n    '
    fields = []
    (i, n) = (0, len(line))
    while (i < n):
        (field, i) = parsefield(line, i, n)
        fields.append(field)
        i = (i + 1)
    if (len(fields) < 2):
        return (None, None)
    (key, view, rest) = (fields[0], fields[1], fields[2:])
    fields = {'view': view}
    for field in rest:
        i = field.find('=')
        if (i < 0):
            fkey = field
            fvalue = ''
        else:
            fkey = field[:i].strip()
            fvalue = field[(i + 1):].strip()
        if (fkey in fields):
            pass
        else:
            fields[fkey] = fvalue
    return (key, fields)

def parsefield(line, i, n):
    'Separate one key-value pair in a mailcap entry.'
    start = i
    while (i < n):
        c = line[i]
        if (c == ';'):
            break
        elif (c == '\\'):
            i = (i + 2)
        else:
            i = (i + 1)
    return (line[start:i].strip(), i)

def findmatch(caps, MIMEtype, key='view', filename='/dev/null', plist=[]):
    "Find a match for a mailcap entry.\n\n    Return a tuple containing the command line, and the mailcap entry\n    used; (None, None) if no match is found.  This may invoke the\n    'test' command of several matching entries before deciding which\n    entry to use.\n\n    "
    entries = lookup(caps, MIMEtype, key)
    for e in entries:
        if ('test' in e):
            test = subst(e['test'], filename, plist)
            if (test and (os.system(test) != 0)):
                continue
        command = subst(e[key], MIMEtype, filename, plist)
        return (command, e)
    return (None, None)

def lookup(caps, MIMEtype, key=None):
    entries = []
    if (MIMEtype in caps):
        entries = (entries + caps[MIMEtype])
    MIMEtypes = MIMEtype.split('/')
    MIMEtype = (MIMEtypes[0] + '/*')
    if (MIMEtype in caps):
        entries = (entries + caps[MIMEtype])
    if (key is not None):
        entries = [e for e in entries if (key in e)]
    entries = sorted(entries, key=lineno_sort_key)
    return entries

def subst(field, MIMEtype, filename, plist=[]):
    res = ''
    (i, n) = (0, len(field))
    while (i < n):
        c = field[i]
        i = (i + 1)
        if (c != '%'):
            if (c == '\\'):
                c = field[i:(i + 1)]
                i = (i + 1)
            res = (res + c)
        else:
            c = field[i]
            i = (i + 1)
            if (c == '%'):
                res = (res + c)
            elif (c == 's'):
                res = (res + filename)
            elif (c == 't'):
                res = (res + MIMEtype)
            elif (c == '{'):
                start = i
                while ((i < n) and (field[i] != '}')):
                    i = (i + 1)
                name = field[start:i]
                i = (i + 1)
                res = (res + findparam(name, plist))
            else:
                res = ((res + '%') + c)
    return res

def findparam(name, plist):
    name = (name.lower() + '=')
    n = len(name)
    for p in plist:
        if (p[:n].lower() == name):
            return p[n:]
    return ''

def test():
    import sys
    caps = getcaps()
    if (not sys.argv[1:]):
        show(caps)
        return
    for i in range(1, len(sys.argv), 2):
        args = sys.argv[i:(i + 2)]
        if (len(args) < 2):
            print('usage: mailcap [MIMEtype file] ...')
            return
        MIMEtype = args[0]
        file = args[1]
        (command, e) = findmatch(caps, MIMEtype, 'view', file)
        if (not command):
            print('No viewer found for', type)
        else:
            print('Executing:', command)
            sts = os.system(command)
            sts = os.waitstatus_to_exitcode(sts)
            if sts:
                print('Exit status:', sts)

def show(caps):
    print('Mailcap files:')
    for fn in listmailcapfiles():
        print(('\t' + fn))
    print()
    if (not caps):
        caps = getcaps()
    print('Mailcap entries:')
    print()
    ckeys = sorted(caps)
    for type in ckeys:
        print(type)
        entries = caps[type]
        for e in entries:
            keys = sorted(e)
            for k in keys:
                print(('  %-15s' % k), e[k])
            print()
if (__name__ == '__main__'):
    test()
