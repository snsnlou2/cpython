
'Classes to parse mailer-daemon messages.'
import calendar
import email.message
import re
import os
import sys

class Unparseable(Exception):
    pass

class ErrorMessage(email.message.Message):

    def __init__(self):
        email.message.Message.__init__(self)
        self.sub = ''

    def is_warning(self):
        sub = self.get('Subject')
        if (not sub):
            return 0
        sub = sub.lower()
        if sub.startswith('waiting mail'):
            return 1
        if ('warning' in sub):
            return 1
        self.sub = sub
        return 0

    def get_errors(self):
        for p in EMPARSERS:
            self.rewindbody()
            try:
                return p(self.fp, self.sub)
            except Unparseable:
                pass
        raise Unparseable
emparse_list_list = ['error: (?P<reason>unresolvable): (?P<email>.+)', ('----- The following addresses had permanent fatal errors -----\n', '(?P<email>[^ \n].*)\n( .*\n)?'), 'remote execution.*\n.*rmail (?P<email>.+)', ('The following recipients did not receive your message:\n\n', ' +(?P<email>.*)\n(The following recipients did not receive your message:\n\n)?'), '------- Failure Reasons  --------\n\n(?P<reason>.*)\n(?P<email>.*)', '^<(?P<email>.*)>:\n(?P<reason>.*)', '^(?P<reason>User mailbox exceeds allowed size): (?P<email>.+)', '^5\\d{2} <(?P<email>[^\n>]+)>\\.\\.\\. (?P<reason>.+)', '^Original-Recipient: rfc822;(?P<email>.*)', '^did not reach the following recipient\\(s\\):\n\n(?P<email>.*) on .*\n +(?P<reason>.*)', '^ <(?P<email>[^\n>]+)> \\.\\.\\. (?P<reason>.*)', '^Report on your message to: (?P<email>.*)\nReason: (?P<reason>.*)', '^Your message was not delivered to +(?P<email>.*)\n +for the following reason:\n +(?P<reason>.*)', '^ was not +(?P<email>[^ \n].*?) *\n.*\n.*\n.*\n because:.*\n +(?P<reason>[^ \n].*?) *\n']
for i in range(len(emparse_list_list)):
    x = emparse_list_list[i]
    if (type(x) is type('')):
        x = re.compile(x, re.MULTILINE)
    else:
        xl = []
        for x in x:
            xl.append(re.compile(x, re.MULTILINE))
        x = tuple(xl)
        del xl
    emparse_list_list[i] = x
    del x
del i
emparse_list_reason = ['^5\\d{2} <>\\.\\.\\. (?P<reason>.*)', '<>\\.\\.\\. (?P<reason>.*)', re.compile('^<<< 5\\d{2} (?P<reason>.*)', re.MULTILINE), re.compile('===== stderr was =====\nrmail: (?P<reason>.*)'), re.compile('^Diagnostic-Code: (?P<reason>.*)', re.MULTILINE)]
emparse_list_from = re.compile('^From:', (re.IGNORECASE | re.MULTILINE))

def emparse_list(fp, sub):
    data = fp.read()
    res = emparse_list_from.search(data)
    if (res is None):
        from_index = len(data)
    else:
        from_index = res.start(0)
    errors = []
    emails = []
    reason = None
    for regexp in emparse_list_list:
        if (type(regexp) is type(())):
            res = regexp[0].search(data, 0, from_index)
            if (res is not None):
                try:
                    reason = res.group('reason')
                except IndexError:
                    pass
                while 1:
                    res = regexp[1].match(data, res.end(0), from_index)
                    if (res is None):
                        break
                    emails.append(res.group('email'))
                break
        else:
            res = regexp.search(data, 0, from_index)
            if (res is not None):
                emails.append(res.group('email'))
                try:
                    reason = res.group('reason')
                except IndexError:
                    pass
                break
    if (not emails):
        raise Unparseable
    if (not reason):
        reason = sub
        if (reason[:15] == 'returned mail: '):
            reason = reason[15:]
        for regexp in emparse_list_reason:
            if (type(regexp) is type('')):
                for i in range((len(emails) - 1), (- 1), (- 1)):
                    email = emails[i]
                    exp = re.compile(re.escape(email).join(regexp.split('<>')), re.MULTILINE)
                    res = exp.search(data)
                    if (res is not None):
                        errors.append(' '.join(((email.strip() + ': ') + res.group('reason')).split()))
                        del emails[i]
                continue
            res = regexp.search(data)
            if (res is not None):
                reason = res.group('reason')
                break
    for email in emails:
        errors.append(' '.join(((email.strip() + ': ') + reason).split()))
    return errors
EMPARSERS = [emparse_list]

def sort_numeric(a, b):
    a = int(a)
    b = int(b)
    if (a < b):
        return (- 1)
    elif (a > b):
        return 1
    else:
        return 0

def parsedir(dir, modify):
    os.chdir(dir)
    pat = re.compile('^[0-9]*$')
    errordict = {}
    errorfirst = {}
    errorlast = {}
    nok = nwarn = nbad = 0
    files = list(filter((lambda fn, pat=pat: (pat.match(fn) is not None)), os.listdir('.')))
    files.sort(sort_numeric)
    for fn in files:
        fp = open(fn)
        m = email.message_from_file(fp, _class=ErrorMessage)
        sender = m.getaddr('From')
        print(('%s\t%-40s\t' % (fn, sender[1])), end=' ')
        if m.is_warning():
            fp.close()
            print('warning only')
            nwarn = (nwarn + 1)
            if modify:
                os.rename(fn, (',' + fn))
            continue
        try:
            errors = m.get_errors()
        except Unparseable:
            print('** Not parseable')
            nbad = (nbad + 1)
            fp.close()
            continue
        print(len(errors), 'errors')
        for e in errors:
            try:
                (mm, dd) = m.getdate('date')[1:(1 + 2)]
                date = ('%s %02d' % (calendar.month_abbr[mm], dd))
            except:
                date = '??????'
            if (e not in errordict):
                errordict[e] = 1
                errorfirst[e] = ('%s (%s)' % (fn, date))
            else:
                errordict[e] = (errordict[e] + 1)
            errorlast[e] = ('%s (%s)' % (fn, date))
        fp.close()
        nok = (nok + 1)
        if modify:
            os.rename(fn, (',' + fn))
    print('--------------')
    print(nok, 'files parsed,', nwarn, 'files warning-only,', end=' ')
    print(nbad, 'files unparseable')
    print('--------------')
    list = []
    for e in errordict.keys():
        list.append((errordict[e], errorfirst[e], errorlast[e], e))
    list.sort()
    for (num, first, last, e) in list:
        print(('%d %s - %s\t%s' % (num, first, last, e)))

def main():
    modify = 0
    if ((len(sys.argv) > 1) and (sys.argv[1] == '-d')):
        modify = 1
        del sys.argv[1]
    if (len(sys.argv) > 1):
        for folder in sys.argv[1:]:
            parsedir(folder, modify)
    else:
        parsedir('/ufs/jack/Mail/errorsinbox', modify)
if ((__name__ == '__main__') or (sys.argv[0] == __name__)):
    main()
