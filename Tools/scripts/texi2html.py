
import os
import sys
import string
import re
MAGIC = '\\input texinfo'
cmprog = re.compile('^@([a-z]+)([ \t]|$)')
blprog = re.compile('^[ \t]*$')
kwprog = re.compile('@[a-z]+')
spprog = re.compile('[\n@{}&<>]')
miprog = re.compile('^\\* ([^:]*):(:|[ \\t]*([^\\t,\\n.]+)([^ \\t\\n]*))[ \\t\\n]*')

class HTMLNode():
    "Some of the parser's functionality is separated into this class.\n\n    A Node accumulates its contents, takes care of links to other Nodes\n    and saves itself when it is finished and all links are resolved.\n    "
    DOCTYPE = '<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">'
    type = 0
    cont = ''
    epilogue = '</BODY></HTML>\n'

    def __init__(self, dir, name, topname, title, next, prev, up):
        self.dirname = dir
        self.name = name
        if topname:
            self.topname = topname
        else:
            self.topname = name
        self.title = title
        self.next = next
        self.prev = prev
        self.up = up
        self.lines = []

    def write(self, *lines):
        for line in lines:
            self.lines.append(line)

    def flush(self):
        with open(((self.dirname + '/') + makefile(self.name)), 'w') as fp:
            fp.write(self.prologue)
            fp.write(self.text)
            fp.write(self.epilogue)

    def link(self, label, nodename, rel=None, rev=None):
        if nodename:
            if (nodename.lower() == '(dir)'):
                addr = '../dir.html'
                title = ''
            else:
                addr = makefile(nodename)
                title = (' TITLE="%s"' % nodename)
            self.write(label, ': <A HREF="', addr, '"', ((rel and (' REL=' + rel)) or ''), ((rev and (' REV=' + rev)) or ''), title, '>', nodename, '</A>  \n')

    def finalize(self):
        length = len(self.lines)
        self.text = ''.join(self.lines)
        self.lines = []
        self.open_links()
        self.output_links()
        self.close_links()
        links = ''.join(self.lines)
        self.lines = []
        self.prologue = ((((((((((((((((self.DOCTYPE + '\n<HTML><HEAD>\n  <!-- Converted with texi2html and Python -->\n  <TITLE>') + self.title) + '</TITLE>\n  <LINK REL=Next HREF="') + makefile(self.next)) + '" TITLE="') + self.next) + '">\n  <LINK REL=Previous HREF="') + makefile(self.prev)) + '" TITLE="') + self.prev) + '">\n  <LINK REL=Up HREF="') + makefile(self.up)) + '" TITLE="') + self.up) + '">\n</HEAD><BODY>\n') + links)
        if (length > 20):
            self.epilogue = ('<P>\n%s</BODY></HTML>\n' % links)

    def open_links(self):
        self.write('<HR>\n')

    def close_links(self):
        self.write('<HR>\n')

    def output_links(self):
        if (self.cont != self.next):
            self.link('  Cont', self.cont)
        self.link('  Next', self.next, rel='Next')
        self.link('  Prev', self.prev, rel='Previous')
        self.link('  Up', self.up, rel='Up')
        if (self.name != self.topname):
            self.link('  Top', self.topname)

class HTML3Node(HTMLNode):
    DOCTYPE = '<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML Level 3//EN//3.0">'

    def open_links(self):
        self.write('<DIV CLASS=Navigation>\n <HR>\n')

    def close_links(self):
        self.write(' <HR>\n</DIV>\n')

class TexinfoParser():
    COPYRIGHT_SYMBOL = '&copy;'
    FN_ID_PATTERN = '(%(id)s)'
    FN_SOURCE_PATTERN = (('<A NAME=footnoteref%(id)s HREF="#footnotetext%(id)s">' + FN_ID_PATTERN) + '</A>')
    FN_TARGET_PATTERN = (('<A NAME=footnotetext%(id)s HREF="#footnoteref%(id)s">' + FN_ID_PATTERN) + '</A>\n%(text)s<P>\n')
    FN_HEADER = '\n<P>\n<HR NOSHADE SIZE=1 WIDTH=200>\n<STRONG><EM>Footnotes</EM></STRONG>\n<P>'
    Node = HTMLNode

    def __init__(self):
        self.unknown = {}
        self.filenames = {}
        self.debugging = 0
        self.print_headers = 0
        self.nodefp = None
        self.nodelineno = 0
        self.links = None
        self.savetext = None
        self.savestack = []
        self.htmlhelp = None
        self.dirname = 'tmp'
        self.includedir = '.'
        self.nodename = ''
        self.topname = ''
        self.title = ''
        self.resetindex()
        self.contents = []
        self.numbering = []
        self.nofill = 0
        self.values = {'html': 1}
        self.stackinfo = {}
        self.footnotes = []
        self.itemarg = None
        self.itemnumber = None
        self.itemindex = None
        self.node = None
        self.nodestack = []
        self.cont = 0
        self.includedepth = 0

    def sethtmlhelp(self, htmlhelp):
        self.htmlhelp = htmlhelp

    def setdirname(self, dirname):
        self.dirname = dirname

    def setincludedir(self, includedir):
        self.includedir = includedir

    def parse(self, fp):
        line = fp.readline()
        lineno = 1
        while (line and ((line[0] == '%') or blprog.match(line))):
            line = fp.readline()
            lineno = (lineno + 1)
        if (line[:len(MAGIC)] != MAGIC):
            raise SyntaxError(('file does not begin with %r' % (MAGIC,)))
        self.parserest(fp, lineno)

    def parserest(self, fp, initial_lineno):
        lineno = initial_lineno
        self.done = 0
        self.skip = 0
        self.stack = []
        accu = []
        while (not self.done):
            line = fp.readline()
            self.nodelineno = (self.nodelineno + 1)
            if (not line):
                if accu:
                    if (not self.skip):
                        self.process(accu)
                    accu = []
                if (initial_lineno > 0):
                    print('*** EOF before @bye')
                break
            lineno = (lineno + 1)
            mo = cmprog.match(line)
            if mo:
                (a, b) = mo.span(1)
                cmd = line[a:b]
                if (cmd in ('noindent', 'refill')):
                    accu.append(line)
                else:
                    if accu:
                        if (not self.skip):
                            self.process(accu)
                        accu = []
                    self.command(line, mo)
            elif (blprog.match(line) and ('format' not in self.stack) and ('example' not in self.stack)):
                if accu:
                    if (not self.skip):
                        self.process(accu)
                        if self.nofill:
                            self.write('\n')
                        else:
                            self.write('<P>\n')
                        accu = []
            else:
                accu.append(line)
        if self.skip:
            print('*** Still skipping at the end')
        if self.stack:
            print('*** Stack not empty at the end')
            print('***', self.stack)
        if (self.includedepth == 0):
            while self.nodestack:
                self.nodestack[(- 1)].finalize()
                self.nodestack[(- 1)].flush()
                del self.nodestack[(- 1)]

    def startsaving(self):
        if (self.savetext is not None):
            self.savestack.append(self.savetext)
        self.savetext = ''

    def collectsavings(self):
        savetext = self.savetext
        if (len(self.savestack) > 0):
            self.savetext = self.savestack[(- 1)]
            del self.savestack[(- 1)]
        else:
            self.savetext = None
        return (savetext or '')

    def write(self, *args):
        try:
            text = ''.join(args)
        except:
            print(args)
            raise TypeError
        if (self.savetext is not None):
            self.savetext = (self.savetext + text)
        elif self.nodefp:
            self.nodefp.write(text)
        elif self.node:
            self.node.write(text)

    def endnode(self):
        if (self.savetext is not None):
            print('*** Still saving text at end of node')
            dummy = self.collectsavings()
        if self.footnotes:
            self.writefootnotes()
        if self.nodefp:
            if (self.nodelineno > 20):
                self.write('<HR>\n')
                [name, next, prev, up] = self.nodelinks[:4]
                self.link('Next', next)
                self.link('Prev', prev)
                self.link('Up', up)
                if (self.nodename != self.topname):
                    self.link('Top', self.topname)
                self.write('<HR>\n')
            self.write('</BODY>\n')
            self.nodefp.close()
            self.nodefp = None
        elif self.node:
            if ((not self.cont) and ((not self.node.type) or (self.node.next and self.node.prev and self.node.up))):
                self.node.finalize()
                self.node.flush()
            else:
                self.nodestack.append(self.node)
            self.node = None
        self.nodename = ''

    def process(self, accu):
        if (self.debugging > 1):
            print(('!' * self.debugging), 'process:', self.skip, self.stack, end=' ')
            if accu:
                print(accu[0][:30], end=' ')
            if (accu[0][30:] or accu[1:]):
                print('...', end=' ')
            print()
        if self.inmenu():
            for line in accu:
                mo = miprog.match(line)
                if (not mo):
                    line = (line.strip() + '\n')
                    self.expand(line)
                    continue
                (bgn, end) = mo.span(0)
                (a, b) = mo.span(1)
                (c, d) = mo.span(2)
                (e, f) = mo.span(3)
                (g, h) = mo.span(4)
                label = line[a:b]
                nodename = line[c:d]
                if (nodename[0] == ':'):
                    nodename = label
                else:
                    nodename = line[e:f]
                punct = line[g:h]
                self.write('  <LI><A HREF="', makefile(nodename), '">', nodename, '</A>', punct, '\n')
                self.htmlhelp.menuitem(nodename)
                self.expand(line[end:])
        else:
            text = ''.join(accu)
            self.expand(text)

    def inmenu(self):
        stack = self.stack
        while (stack and (stack[(- 1)] in ('ifset', 'ifclear'))):
            try:
                if self.stackinfo[len(stack)]:
                    return 0
            except KeyError:
                pass
            stack = stack[:(- 1)]
        return (stack and (stack[(- 1)] == 'menu'))

    def expand(self, text):
        stack = []
        i = 0
        n = len(text)
        while (i < n):
            start = i
            mo = spprog.search(text, i)
            if mo:
                i = mo.start()
            else:
                self.write(text[start:])
                break
            self.write(text[start:i])
            c = text[i]
            i = (i + 1)
            if (c == '\n'):
                self.write('\n')
                continue
            if (c == '<'):
                self.write('&lt;')
                continue
            if (c == '>'):
                self.write('&gt;')
                continue
            if (c == '&'):
                self.write('&amp;')
                continue
            if (c == '{'):
                stack.append('')
                continue
            if (c == '}'):
                if (not stack):
                    print('*** Unmatched }')
                    self.write('}')
                    continue
                cmd = stack[(- 1)]
                del stack[(- 1)]
                try:
                    method = getattr(self, ('close_' + cmd))
                except AttributeError:
                    self.unknown_close(cmd)
                    continue
                method()
                continue
            if (c != '@'):
                raise RuntimeError(('unexpected funny %r' % c))
            start = i
            while ((i < n) and (text[i] in string.ascii_letters)):
                i = (i + 1)
            if (i == start):
                i = (i + 1)
                c = text[start:i]
                if (c == ':'):
                    pass
                else:
                    self.write(c)
                continue
            cmd = text[start:i]
            if ((i < n) and (text[i] == '{')):
                i = (i + 1)
                stack.append(cmd)
                try:
                    method = getattr(self, ('open_' + cmd))
                except AttributeError:
                    self.unknown_open(cmd)
                    continue
                method()
                continue
            try:
                method = getattr(self, ('handle_' + cmd))
            except AttributeError:
                self.unknown_handle(cmd)
                continue
            method()
        if stack:
            print('*** Stack not empty at para:', stack)

    def unknown_open(self, cmd):
        print((('*** No open func for @' + cmd) + '{...}'))
        cmd = (cmd + '{')
        self.write('@', cmd)
        if (cmd not in self.unknown):
            self.unknown[cmd] = 1
        else:
            self.unknown[cmd] = (self.unknown[cmd] + 1)

    def unknown_close(self, cmd):
        print((('*** No close func for @' + cmd) + '{...}'))
        cmd = ('}' + cmd)
        self.write('}')
        if (cmd not in self.unknown):
            self.unknown[cmd] = 1
        else:
            self.unknown[cmd] = (self.unknown[cmd] + 1)

    def unknown_handle(self, cmd):
        print(('*** No handler for @' + cmd))
        self.write('@', cmd)
        if (cmd not in self.unknown):
            self.unknown[cmd] = 1
        else:
            self.unknown[cmd] = (self.unknown[cmd] + 1)

    def handle_noindent(self):
        pass

    def handle_refill(self):
        pass

    def do_include(self, args):
        file = args
        file = os.path.join(self.includedir, file)
        try:
            fp = open(file, 'r')
        except IOError as msg:
            print("*** Can't open include file", repr(file))
            return
        with fp:
            print(('!' * self.debugging), '--> file', repr(file))
            save_done = self.done
            save_skip = self.skip
            save_stack = self.stack
            self.includedepth = (self.includedepth + 1)
            self.parserest(fp, 0)
            self.includedepth = (self.includedepth - 1)
        self.done = save_done
        self.skip = save_skip
        self.stack = save_stack
        print(('!' * self.debugging), '<-- file', repr(file))

    def open_dmn(self):
        pass

    def close_dmn(self):
        pass

    def open_dots(self):
        self.write('...')

    def close_dots(self):
        pass

    def open_bullet(self):
        pass

    def close_bullet(self):
        pass

    def open_TeX(self):
        self.write('TeX')

    def close_TeX(self):
        pass

    def handle_copyright(self):
        self.write(self.COPYRIGHT_SYMBOL)

    def open_copyright(self):
        self.write(self.COPYRIGHT_SYMBOL)

    def close_copyright(self):
        pass

    def open_minus(self):
        self.write('-')

    def close_minus(self):
        pass

    def open_exclamdown(self):
        self.write('&#161;')

    def close_exclamdown(self):
        pass

    def open_questiondown(self):
        self.write('&#191;')

    def close_questiondown(self):
        pass

    def open_aa(self):
        self.write('&#229;')

    def close_aa(self):
        pass

    def open_AA(self):
        self.write('&#197;')

    def close_AA(self):
        pass

    def open_ae(self):
        self.write('&#230;')

    def close_ae(self):
        pass

    def open_AE(self):
        self.write('&#198;')

    def close_AE(self):
        pass

    def open_o(self):
        self.write('&#248;')

    def close_o(self):
        pass

    def open_O(self):
        self.write('&#216;')

    def close_O(self):
        pass

    def open_ss(self):
        self.write('&#223;')

    def close_ss(self):
        pass

    def open_oe(self):
        self.write('oe')

    def close_oe(self):
        pass

    def open_OE(self):
        self.write('OE')

    def close_OE(self):
        pass

    def open_l(self):
        self.write('l/')

    def close_l(self):
        pass

    def open_L(self):
        self.write('L/')

    def close_L(self):
        pass

    def open_result(self):
        self.write('=&gt;')

    def close_result(self):
        pass

    def open_expansion(self):
        self.write('==&gt;')

    def close_expansion(self):
        pass

    def open_print(self):
        self.write('-|')

    def close_print(self):
        pass

    def open_error(self):
        self.write('error--&gt;')

    def close_error(self):
        pass

    def open_equiv(self):
        self.write('==')

    def close_equiv(self):
        pass

    def open_point(self):
        self.write('-!-')

    def close_point(self):
        pass

    def open_pxref(self):
        self.write('see ')
        self.startsaving()

    def close_pxref(self):
        self.makeref()

    def open_xref(self):
        self.write('See ')
        self.startsaving()

    def close_xref(self):
        self.makeref()

    def open_ref(self):
        self.startsaving()

    def close_ref(self):
        self.makeref()

    def open_inforef(self):
        self.write('See info file ')
        self.startsaving()

    def close_inforef(self):
        text = self.collectsavings()
        args = [s.strip() for s in text.split(',')]
        while (len(args) < 3):
            args.append('')
        node = args[0]
        file = args[2]
        self.write('`', file, "', node `", node, "'")

    def makeref(self):
        text = self.collectsavings()
        args = [s.strip() for s in text.split(',')]
        while (len(args) < 5):
            args.append('')
        nodename = label = args[0]
        if args[2]:
            label = args[2]
        file = args[3]
        title = args[4]
        href = makefile(nodename)
        if file:
            href = ((('../' + file) + '/') + href)
        self.write('<A HREF="', href, '">', label, '</A>')

    def open_uref(self):
        self.startsaving()

    def close_uref(self):
        text = self.collectsavings()
        args = [s.strip() for s in text.split(',')]
        while (len(args) < 2):
            args.append('')
        href = args[0]
        label = args[1]
        if (not label):
            label = href
        self.write('<A HREF="', href, '">', label, '</A>')

    def open_image(self):
        self.startsaving()

    def close_image(self):
        self.makeimage()

    def makeimage(self):
        text = self.collectsavings()
        args = [s.strip() for s in text.split(',')]
        while (len(args) < 5):
            args.append('')
        filename = args[0]
        width = args[1]
        height = args[2]
        alt = args[3]
        ext = args[4]
        imagelocation = ((self.dirname + '/') + filename)
        if os.path.exists((imagelocation + '.png')):
            filename += '.png'
        elif os.path.exists((imagelocation + '.jpg')):
            filename += '.jpg'
        elif os.path.exists((imagelocation + '.gif')):
            filename += '.gif'
        else:
            print(('*** Cannot find image ' + imagelocation))
        self.write('<IMG SRC="', filename, '"', ((width and ((' WIDTH="' + width) + '"')) or ''), ((height and ((' HEIGHT="' + height) + '"')) or ''), ((alt and ((' ALT="' + alt) + '"')) or ''), '/>')
        self.htmlhelp.addimage(imagelocation)

    def open_(self):
        pass

    def close_(self):
        pass
    open_asis = open_
    close_asis = close_

    def open_cite(self):
        self.write('<CITE>')

    def close_cite(self):
        self.write('</CITE>')

    def open_code(self):
        self.write('<CODE>')

    def close_code(self):
        self.write('</CODE>')

    def open_t(self):
        self.write('<TT>')

    def close_t(self):
        self.write('</TT>')

    def open_dfn(self):
        self.write('<DFN>')

    def close_dfn(self):
        self.write('</DFN>')

    def open_emph(self):
        self.write('<EM>')

    def close_emph(self):
        self.write('</EM>')

    def open_i(self):
        self.write('<I>')

    def close_i(self):
        self.write('</I>')

    def open_footnote(self):
        id = (len(self.footnotes) + 1)
        self.write((self.FN_SOURCE_PATTERN % {'id': repr(id)}))
        self.startsaving()

    def close_footnote(self):
        id = (len(self.footnotes) + 1)
        self.footnotes.append((id, self.collectsavings()))

    def writefootnotes(self):
        self.write(self.FN_HEADER)
        for (id, text) in self.footnotes:
            self.write((self.FN_TARGET_PATTERN % {'id': repr(id), 'text': text}))
        self.footnotes = []

    def open_file(self):
        self.write('<CODE>')

    def close_file(self):
        self.write('</CODE>')

    def open_kbd(self):
        self.write('<KBD>')

    def close_kbd(self):
        self.write('</KBD>')

    def open_key(self):
        self.write('<KEY>')

    def close_key(self):
        self.write('</KEY>')

    def open_r(self):
        self.write('<R>')

    def close_r(self):
        self.write('</R>')

    def open_samp(self):
        self.write('`<SAMP>')

    def close_samp(self):
        self.write("</SAMP>'")

    def open_sc(self):
        self.write('<SMALLCAPS>')

    def close_sc(self):
        self.write('</SMALLCAPS>')

    def open_strong(self):
        self.write('<STRONG>')

    def close_strong(self):
        self.write('</STRONG>')

    def open_b(self):
        self.write('<B>')

    def close_b(self):
        self.write('</B>')

    def open_var(self):
        self.write('<VAR>')

    def close_var(self):
        self.write('</VAR>')

    def open_w(self):
        self.write('<NOBREAK>')

    def close_w(self):
        self.write('</NOBREAK>')

    def open_url(self):
        self.startsaving()

    def close_url(self):
        text = self.collectsavings()
        self.write('<A HREF="', text, '">', text, '</A>')

    def open_email(self):
        self.startsaving()

    def close_email(self):
        text = self.collectsavings()
        self.write('<A HREF="mailto:', text, '">', text, '</A>')
    open_titlefont = open_
    close_titlefont = close_

    def open_small(self):
        pass

    def close_small(self):
        pass

    def command(self, line, mo):
        (a, b) = mo.span(1)
        cmd = line[a:b]
        args = line[b:].strip()
        if (self.debugging > 1):
            print(('!' * self.debugging), 'command:', self.skip, self.stack, ('@' + cmd), args)
        try:
            func = getattr(self, ('do_' + cmd))
        except AttributeError:
            try:
                func = getattr(self, ('bgn_' + cmd))
            except AttributeError:
                if (not self.skip):
                    self.unknown_cmd(cmd, args)
                return
            self.stack.append(cmd)
            func(args)
            return
        if ((not self.skip) or (cmd == 'end')):
            func(args)

    def unknown_cmd(self, cmd, args):
        print('*** unknown', ('@' + cmd), args)
        if (cmd not in self.unknown):
            self.unknown[cmd] = 1
        else:
            self.unknown[cmd] = (self.unknown[cmd] + 1)

    def do_end(self, args):
        words = args.split()
        if (not words):
            print('*** @end w/o args')
        else:
            cmd = words[0]
            if ((not self.stack) or (self.stack[(- 1)] != cmd)):
                print('*** @end', cmd, 'unexpected')
            else:
                del self.stack[(- 1)]
            try:
                func = getattr(self, ('end_' + cmd))
            except AttributeError:
                self.unknown_end(cmd)
                return
            func()

    def unknown_end(self, cmd):
        cmd = ('end ' + cmd)
        print('*** unknown', ('@' + cmd))
        if (cmd not in self.unknown):
            self.unknown[cmd] = 1
        else:
            self.unknown[cmd] = (self.unknown[cmd] + 1)

    def do_comment(self, args):
        pass
    do_c = do_comment

    def bgn_ifinfo(self, args):
        pass

    def end_ifinfo(self):
        pass

    def bgn_iftex(self, args):
        self.skip = (self.skip + 1)

    def end_iftex(self):
        self.skip = (self.skip - 1)

    def bgn_ignore(self, args):
        self.skip = (self.skip + 1)

    def end_ignore(self):
        self.skip = (self.skip - 1)

    def bgn_tex(self, args):
        self.skip = (self.skip + 1)

    def end_tex(self):
        self.skip = (self.skip - 1)

    def do_set(self, args):
        fields = args.split(' ')
        key = fields[0]
        if (len(fields) == 1):
            value = 1
        else:
            value = ' '.join(fields[1:])
        self.values[key] = value

    def do_clear(self, args):
        self.values[args] = None

    def bgn_ifset(self, args):
        if ((args not in self.values) or (self.values[args] is None)):
            self.skip = (self.skip + 1)
            self.stackinfo[len(self.stack)] = 1
        else:
            self.stackinfo[len(self.stack)] = 0

    def end_ifset(self):
        try:
            if self.stackinfo[(len(self.stack) + 1)]:
                self.skip = (self.skip - 1)
            del self.stackinfo[(len(self.stack) + 1)]
        except KeyError:
            print('*** end_ifset: KeyError :', (len(self.stack) + 1))

    def bgn_ifclear(self, args):
        if ((args in self.values) and (self.values[args] is not None)):
            self.skip = (self.skip + 1)
            self.stackinfo[len(self.stack)] = 1
        else:
            self.stackinfo[len(self.stack)] = 0

    def end_ifclear(self):
        try:
            if self.stackinfo[(len(self.stack) + 1)]:
                self.skip = (self.skip - 1)
            del self.stackinfo[(len(self.stack) + 1)]
        except KeyError:
            print('*** end_ifclear: KeyError :', (len(self.stack) + 1))

    def open_value(self):
        self.startsaving()

    def close_value(self):
        key = self.collectsavings()
        if (key in self.values):
            self.write(self.values[key])
        else:
            print('*** Undefined value: ', key)
    do_finalout = do_comment
    do_setchapternewpage = do_comment
    do_setfilename = do_comment

    def do_settitle(self, args):
        self.startsaving()
        self.expand(args)
        self.title = self.collectsavings()

    def do_parskip(self, args):
        pass

    def do_bye(self, args):
        self.endnode()
        self.done = 1

    def bgn_titlepage(self, args):
        self.skip = (self.skip + 1)

    def end_titlepage(self):
        self.skip = (self.skip - 1)

    def do_shorttitlepage(self, args):
        pass

    def do_center(self, args):
        self.write('<H1>')
        self.expand(args)
        self.write('</H1>\n')
    do_title = do_center
    do_subtitle = do_center
    do_author = do_center
    do_vskip = do_comment
    do_vfill = do_comment
    do_smallbook = do_comment
    do_paragraphindent = do_comment
    do_setchapternewpage = do_comment
    do_headings = do_comment
    do_footnotestyle = do_comment
    do_evenheading = do_comment
    do_evenfooting = do_comment
    do_oddheading = do_comment
    do_oddfooting = do_comment
    do_everyheading = do_comment
    do_everyfooting = do_comment

    def do_node(self, args):
        self.endnode()
        self.nodelineno = 0
        parts = [s.strip() for s in args.split(',')]
        while (len(parts) < 4):
            parts.append('')
        self.nodelinks = parts
        [name, next, prev, up] = parts[:4]
        file = ((self.dirname + '/') + makefile(name))
        if (file in self.filenames):
            print('*** Filename already in use: ', file)
        elif self.debugging:
            print(('!' * self.debugging), '--- writing', file)
        self.filenames[file] = 1
        self.nodename = name
        if (self.cont and self.nodestack):
            self.nodestack[(- 1)].cont = self.nodename
        if (not self.topname):
            self.topname = name
        title = name
        if self.title:
            title = ((title + ' -- ') + self.title)
        self.node = self.Node(self.dirname, self.nodename, self.topname, title, next, prev, up)
        self.htmlhelp.addnode(self.nodename, next, prev, up, file)

    def link(self, label, nodename):
        if nodename:
            if (nodename.lower() == '(dir)'):
                addr = '../dir.html'
            else:
                addr = makefile(nodename)
            self.write(label, ': <A HREF="', addr, '" TYPE="', label, '">', nodename, '</A>  \n')

    def popstack(self, type):
        if self.node:
            self.node.type = type
            while self.nodestack:
                if (self.nodestack[(- 1)].type > type):
                    self.nodestack[(- 1)].finalize()
                    self.nodestack[(- 1)].flush()
                    del self.nodestack[(- 1)]
                elif (self.nodestack[(- 1)].type == type):
                    if (not self.nodestack[(- 1)].next):
                        self.nodestack[(- 1)].next = self.node.name
                    if (not self.node.prev):
                        self.node.prev = self.nodestack[(- 1)].name
                    self.nodestack[(- 1)].finalize()
                    self.nodestack[(- 1)].flush()
                    del self.nodestack[(- 1)]
                else:
                    if ((type > 1) and (not self.node.up)):
                        self.node.up = self.nodestack[(- 1)].name
                    break

    def do_chapter(self, args):
        self.heading('H1', args, 0)
        self.popstack(1)

    def do_unnumbered(self, args):
        self.heading('H1', args, (- 1))
        self.popstack(1)

    def do_appendix(self, args):
        self.heading('H1', args, (- 1))
        self.popstack(1)

    def do_top(self, args):
        self.heading('H1', args, (- 1))

    def do_chapheading(self, args):
        self.heading('H1', args, (- 1))

    def do_majorheading(self, args):
        self.heading('H1', args, (- 1))

    def do_section(self, args):
        self.heading('H1', args, 1)
        self.popstack(2)

    def do_unnumberedsec(self, args):
        self.heading('H1', args, (- 1))
        self.popstack(2)

    def do_appendixsec(self, args):
        self.heading('H1', args, (- 1))
        self.popstack(2)
    do_appendixsection = do_appendixsec

    def do_heading(self, args):
        self.heading('H1', args, (- 1))

    def do_subsection(self, args):
        self.heading('H2', args, 2)
        self.popstack(3)

    def do_unnumberedsubsec(self, args):
        self.heading('H2', args, (- 1))
        self.popstack(3)

    def do_appendixsubsec(self, args):
        self.heading('H2', args, (- 1))
        self.popstack(3)

    def do_subheading(self, args):
        self.heading('H2', args, (- 1))

    def do_subsubsection(self, args):
        self.heading('H3', args, 3)
        self.popstack(4)

    def do_unnumberedsubsubsec(self, args):
        self.heading('H3', args, (- 1))
        self.popstack(4)

    def do_appendixsubsubsec(self, args):
        self.heading('H3', args, (- 1))
        self.popstack(4)

    def do_subsubheading(self, args):
        self.heading('H3', args, (- 1))

    def heading(self, type, args, level):
        if (level >= 0):
            while (len(self.numbering) <= level):
                self.numbering.append(0)
            del self.numbering[(level + 1):]
            self.numbering[level] = (self.numbering[level] + 1)
            x = ''
            for i in self.numbering:
                x = ((x + repr(i)) + '.')
            args = ((x + ' ') + args)
            self.contents.append((level, args, self.nodename))
        self.write('<', type, '>')
        self.expand(args)
        self.write('</', type, '>\n')
        if (self.debugging or self.print_headers):
            print('---', args)

    def do_contents(self, args):
        self.listcontents('Table of Contents', 999)

    def do_shortcontents(self, args):
        pass
    do_summarycontents = do_shortcontents

    def listcontents(self, title, maxlevel):
        self.write('<H1>', title, '</H1>\n<UL COMPACT PLAIN>\n')
        prevlevels = [0]
        for (level, title, node) in self.contents:
            if (level > maxlevel):
                continue
            if (level > prevlevels[(- 1)]):
                self.write(('  ' * prevlevels[(- 1)]), '<UL PLAIN>\n')
                prevlevels.append(level)
            elif (level < prevlevels[(- 1)]):
                while (level < prevlevels[(- 1)]):
                    del prevlevels[(- 1)]
                    self.write(('  ' * prevlevels[(- 1)]), '</UL>\n')
            self.write(('  ' * level), '<LI> <A HREF="', makefile(node), '">')
            self.expand(title)
            self.write('</A>\n')
        self.write(('</UL>\n' * len(prevlevels)))

    def do_page(self, args):
        pass

    def do_need(self, args):
        pass

    def bgn_group(self, args):
        pass

    def end_group(self):
        pass

    def do_sp(self, args):
        if self.nofill:
            self.write('\n')
        else:
            self.write('<P>\n')

    def do_hline(self, args):
        self.write('<HR>')

    def bgn_deffn(self, args):
        self.write('<DL>')
        self.do_deffnx(args)

    def end_deffn(self):
        self.write('</DL>\n')

    def do_deffnx(self, args):
        self.write('<DT>')
        words = splitwords(args, 2)
        ([category, name], rest) = (words[:2], words[2:])
        self.expand(('@b{%s}' % name))
        for word in rest:
            self.expand((' ' + makevar(word)))
        self.write('\n<DD>')
        self.index('fn', name)

    def bgn_defun(self, args):
        self.bgn_deffn(('Function ' + args))
    end_defun = end_deffn

    def do_defunx(self, args):
        self.do_deffnx(('Function ' + args))

    def bgn_defmac(self, args):
        self.bgn_deffn(('Macro ' + args))
    end_defmac = end_deffn

    def do_defmacx(self, args):
        self.do_deffnx(('Macro ' + args))

    def bgn_defspec(self, args):
        self.bgn_deffn(('{Special Form} ' + args))
    end_defspec = end_deffn

    def do_defspecx(self, args):
        self.do_deffnx(('{Special Form} ' + args))

    def bgn_defvr(self, args):
        self.write('<DL>')
        self.do_defvrx(args)
    end_defvr = end_deffn

    def do_defvrx(self, args):
        self.write('<DT>')
        words = splitwords(args, 2)
        ([category, name], rest) = (words[:2], words[2:])
        self.expand(('@code{%s}' % name))
        for word in rest:
            self.expand((' ' + word))
        self.write('\n<DD>')
        self.index('vr', name)

    def bgn_defvar(self, args):
        self.bgn_defvr(('Variable ' + args))
    end_defvar = end_defvr

    def do_defvarx(self, args):
        self.do_defvrx(('Variable ' + args))

    def bgn_defopt(self, args):
        self.bgn_defvr(('{User Option} ' + args))
    end_defopt = end_defvr

    def do_defoptx(self, args):
        self.do_defvrx(('{User Option} ' + args))

    def bgn_deftypefn(self, args):
        self.write('<DL>')
        self.do_deftypefnx(args)
    end_deftypefn = end_deffn

    def do_deftypefnx(self, args):
        self.write('<DT>')
        words = splitwords(args, 3)
        ([category, datatype, name], rest) = (words[:3], words[3:])
        self.expand(('@code{%s} @b{%s}' % (datatype, name)))
        for word in rest:
            self.expand((' ' + makevar(word)))
        self.write('\n<DD>')
        self.index('fn', name)

    def bgn_deftypefun(self, args):
        self.bgn_deftypefn(('Function ' + args))
    end_deftypefun = end_deftypefn

    def do_deftypefunx(self, args):
        self.do_deftypefnx(('Function ' + args))

    def bgn_deftypevr(self, args):
        self.write('<DL>')
        self.do_deftypevrx(args)
    end_deftypevr = end_deftypefn

    def do_deftypevrx(self, args):
        self.write('<DT>')
        words = splitwords(args, 3)
        ([category, datatype, name], rest) = (words[:3], words[3:])
        self.expand(('@code{%s} @b{%s}' % (datatype, name)))
        for word in rest:
            self.expand((' ' + word))
        self.write('\n<DD>')
        self.index('fn', name)

    def bgn_deftypevar(self, args):
        self.bgn_deftypevr(('Variable ' + args))
    end_deftypevar = end_deftypevr

    def do_deftypevarx(self, args):
        self.do_deftypevrx(('Variable ' + args))

    def bgn_defcv(self, args):
        self.write('<DL>')
        self.do_defcvx(args)
    end_defcv = end_deftypevr

    def do_defcvx(self, args):
        self.write('<DT>')
        words = splitwords(args, 3)
        ([category, classname, name], rest) = (words[:3], words[3:])
        self.expand(('@b{%s}' % name))
        for word in rest:
            self.expand((' ' + word))
        self.write('\n<DD>')
        self.index('vr', ('%s @r{on %s}' % (name, classname)))

    def bgn_defivar(self, args):
        self.bgn_defcv(('{Instance Variable} ' + args))
    end_defivar = end_defcv

    def do_defivarx(self, args):
        self.do_defcvx(('{Instance Variable} ' + args))

    def bgn_defop(self, args):
        self.write('<DL>')
        self.do_defopx(args)
    end_defop = end_defcv

    def do_defopx(self, args):
        self.write('<DT>')
        words = splitwords(args, 3)
        ([category, classname, name], rest) = (words[:3], words[3:])
        self.expand(('@b{%s}' % name))
        for word in rest:
            self.expand((' ' + makevar(word)))
        self.write('\n<DD>')
        self.index('fn', ('%s @r{on %s}' % (name, classname)))

    def bgn_defmethod(self, args):
        self.bgn_defop(('Method ' + args))
    end_defmethod = end_defop

    def do_defmethodx(self, args):
        self.do_defopx(('Method ' + args))

    def bgn_deftp(self, args):
        self.write('<DL>')
        self.do_deftpx(args)
    end_deftp = end_defcv

    def do_deftpx(self, args):
        self.write('<DT>')
        words = splitwords(args, 2)
        ([category, name], rest) = (words[:2], words[2:])
        self.expand(('@b{%s}' % name))
        for word in rest:
            self.expand((' ' + word))
        self.write('\n<DD>')
        self.index('tp', name)

    def bgn_enumerate(self, args):
        if (not args):
            self.write('<OL>\n')
            self.stackinfo[len(self.stack)] = '</OL>\n'
        else:
            self.itemnumber = args
            self.write('<UL>\n')
            self.stackinfo[len(self.stack)] = '</UL>\n'

    def end_enumerate(self):
        self.itemnumber = None
        self.write(self.stackinfo[(len(self.stack) + 1)])
        del self.stackinfo[(len(self.stack) + 1)]

    def bgn_itemize(self, args):
        self.itemarg = args
        self.write('<UL>\n')

    def end_itemize(self):
        self.itemarg = None
        self.write('</UL>\n')

    def bgn_table(self, args):
        self.itemarg = args
        self.write('<DL>\n')

    def end_table(self):
        self.itemarg = None
        self.write('</DL>\n')

    def bgn_ftable(self, args):
        self.itemindex = 'fn'
        self.bgn_table(args)

    def end_ftable(self):
        self.itemindex = None
        self.end_table()

    def bgn_vtable(self, args):
        self.itemindex = 'vr'
        self.bgn_table(args)

    def end_vtable(self):
        self.itemindex = None
        self.end_table()

    def do_item(self, args):
        if self.itemindex:
            self.index(self.itemindex, args)
        if self.itemarg:
            if ((self.itemarg[0] == '@') and self.itemarg[1] and (self.itemarg[1] in string.ascii_letters)):
                args = (((self.itemarg + '{') + args) + '}')
            else:
                args = ((self.itemarg + ' ') + args)
        if (self.itemnumber is not None):
            args = ((self.itemnumber + '. ') + args)
            self.itemnumber = increment(self.itemnumber)
        if (self.stack and (self.stack[(- 1)] == 'table')):
            self.write('<DT>')
            self.expand(args)
            self.write('\n<DD>')
        elif (self.stack and (self.stack[(- 1)] == 'multitable')):
            self.write('<TR><TD>')
            self.expand(args)
            self.write('</TD>\n</TR>\n')
        else:
            self.write('<LI>')
            self.expand(args)
            self.write('  ')
    do_itemx = do_item

    def bgn_multitable(self, args):
        self.itemarg = None
        self.write('<TABLE BORDER="">\n')

    def end_multitable(self):
        self.itemarg = None
        self.write('</TABLE>\n<BR>\n')

    def handle_columnfractions(self):
        self.itemarg = None

    def handle_tab(self):
        self.write('</TD>\n    <TD>')

    def bgn_quotation(self, args):
        self.write('<BLOCKQUOTE>')

    def end_quotation(self):
        self.write('</BLOCKQUOTE>\n')

    def bgn_example(self, args):
        self.nofill = (self.nofill + 1)
        self.write('<PRE>')

    def end_example(self):
        self.write('</PRE>\n')
        self.nofill = (self.nofill - 1)
    bgn_lisp = bgn_example
    end_lisp = end_example
    bgn_smallexample = bgn_example
    end_smallexample = end_example
    bgn_smalllisp = bgn_lisp
    end_smalllisp = end_lisp
    bgn_display = bgn_example
    end_display = end_example
    bgn_format = bgn_display
    end_format = end_display

    def do_exdent(self, args):
        self.expand((args + '\n'))

    def bgn_flushleft(self, args):
        self.nofill = (self.nofill + 1)
        self.write('<PRE>\n')

    def end_flushleft(self):
        self.write('</PRE>\n')
        self.nofill = (self.nofill - 1)

    def bgn_flushright(self, args):
        self.nofill = (self.nofill + 1)
        self.write('<ADDRESS COMPACT>\n')

    def end_flushright(self):
        self.write('</ADDRESS>\n')
        self.nofill = (self.nofill - 1)

    def bgn_menu(self, args):
        self.write('<DIR>\n')
        self.write('  <STRONG><EM>Menu</EM></STRONG><P>\n')
        self.htmlhelp.beginmenu()

    def end_menu(self):
        self.write('</DIR>\n')
        self.htmlhelp.endmenu()

    def bgn_cartouche(self, args):
        pass

    def end_cartouche(self):
        pass

    def resetindex(self):
        self.noncodeindices = ['cp']
        self.indextitle = {}
        self.indextitle['cp'] = 'Concept'
        self.indextitle['fn'] = 'Function'
        self.indextitle['ky'] = 'Keyword'
        self.indextitle['pg'] = 'Program'
        self.indextitle['tp'] = 'Type'
        self.indextitle['vr'] = 'Variable'
        self.whichindex = {}
        for name in self.indextitle:
            self.whichindex[name] = []

    def user_index(self, name, args):
        if (name in self.whichindex):
            self.index(name, args)
        else:
            print('*** No index named', repr(name))

    def do_cindex(self, args):
        self.index('cp', args)

    def do_findex(self, args):
        self.index('fn', args)

    def do_kindex(self, args):
        self.index('ky', args)

    def do_pindex(self, args):
        self.index('pg', args)

    def do_tindex(self, args):
        self.index('tp', args)

    def do_vindex(self, args):
        self.index('vr', args)

    def index(self, name, args):
        self.whichindex[name].append((args, self.nodename))
        self.htmlhelp.index(args, self.nodename)

    def do_synindex(self, args):
        words = args.split()
        if (len(words) != 2):
            print('*** bad @synindex', args)
            return
        [old, new] = words
        if ((old not in self.whichindex) or (new not in self.whichindex)):
            print('*** bad key(s) in @synindex', args)
            return
        if ((old != new) and (self.whichindex[old] is not self.whichindex[new])):
            inew = self.whichindex[new]
            inew[len(inew):] = self.whichindex[old]
            self.whichindex[old] = inew
    do_syncodeindex = do_synindex

    def do_printindex(self, args):
        words = args.split()
        for name in words:
            if (name in self.whichindex):
                self.prindex(name)
            else:
                print('*** No index named', repr(name))

    def prindex(self, name):
        iscodeindex = (name not in self.noncodeindices)
        index = self.whichindex[name]
        if (not index):
            return
        if self.debugging:
            print(('!' * self.debugging), '--- Generating', self.indextitle[name], 'index')
        index1 = []
        junkprog = re.compile('^(@[a-z]+)?{')
        for (key, node) in index:
            sortkey = key.lower()
            oldsortkey = sortkey
            while 1:
                mo = junkprog.match(sortkey)
                if (not mo):
                    break
                i = mo.end()
                sortkey = sortkey[i:]
            index1.append((sortkey, key, node))
        del index[:]
        index1.sort()
        self.write('<DL COMPACT>\n')
        prevkey = prevnode = None
        for (sortkey, key, node) in index1:
            if ((key, node) == (prevkey, prevnode)):
                continue
            if (self.debugging > 1):
                print(('!' * self.debugging), key, ':', node)
            self.write('<DT>')
            if iscodeindex:
                key = (('@code{' + key) + '}')
            if (key != prevkey):
                self.expand(key)
            self.write(('\n<DD><A HREF="%s">%s</A>\n' % (makefile(node), node)))
            (prevkey, prevnode) = (key, node)
        self.write('</DL>\n')

    def report(self):
        if self.unknown:
            print('--- Unrecognized commands ---')
            cmds = sorted(self.unknown.keys())
            for cmd in cmds:
                print(cmd.ljust(20), self.unknown[cmd])

class TexinfoParserHTML3(TexinfoParser):
    COPYRIGHT_SYMBOL = '&copy;'
    FN_ID_PATTERN = '[%(id)s]'
    FN_SOURCE_PATTERN = (('<A ID=footnoteref%(id)s HREF="#footnotetext%(id)s">' + FN_ID_PATTERN) + '</A>')
    FN_TARGET_PATTERN = (('<FN ID=footnotetext%(id)s>\n<P><A HREF="#footnoteref%(id)s">' + FN_ID_PATTERN) + '</A>\n%(text)s</P></FN>\n')
    FN_HEADER = '<DIV CLASS=footnotes>\n  <HR NOSHADE WIDTH=200>\n  <STRONG><EM>Footnotes</EM></STRONG>\n  <P>\n'
    Node = HTML3Node

    def bgn_quotation(self, args):
        self.write('<BQ>')

    def end_quotation(self):
        self.write('</BQ>\n')

    def bgn_example(self, args):
        self.nofill = (self.nofill + 1)
        self.write('<PRE CLASS=example><CODE>')

    def end_example(self):
        self.write('</CODE></PRE>\n')
        self.nofill = (self.nofill - 1)

    def bgn_flushleft(self, args):
        self.nofill = (self.nofill + 1)
        self.write('<PRE CLASS=flushleft>\n')

    def bgn_flushright(self, args):
        self.nofill = (self.nofill + 1)
        self.write('<DIV ALIGN=right CLASS=flushright><ADDRESS COMPACT>\n')

    def end_flushright(self):
        self.write('</ADDRESS></DIV>\n')
        self.nofill = (self.nofill - 1)

    def bgn_menu(self, args):
        self.write('<UL PLAIN CLASS=menu>\n')
        self.write('  <LH>Menu</LH>\n')

    def end_menu(self):
        self.write('</UL>\n')

class HTMLHelp():
    '\n    This class encapsulates support for HTML Help. Node names,\n    file names, menu items, index items, and image file names are\n    accumulated until a call to finalize(). At that time, three\n    output files are created in the current directory:\n\n        `helpbase`.hhp  is a HTML Help Workshop project file.\n                        It contains various information, some of\n                        which I do not understand; I just copied\n                        the default project info from a fresh\n                        installation.\n        `helpbase`.hhc  is the Contents file for the project.\n        `helpbase`.hhk  is the Index file for the project.\n\n    When these files are used as input to HTML Help Workshop,\n    the resulting file will be named:\n\n        `helpbase`.chm\n\n    If none of the defaults in `helpbase`.hhp are changed,\n    the .CHM file will have Contents, Index, Search, and\n    Favorites tabs.\n    '
    codeprog = re.compile('@code{(.*?)}')

    def __init__(self, helpbase, dirname):
        self.helpbase = helpbase
        self.dirname = dirname
        self.projectfile = None
        self.contentfile = None
        self.indexfile = None
        self.nodelist = []
        self.nodenames = {}
        self.nodeindex = {}
        self.filenames = {}
        self.indexlist = []
        self.current = ''
        self.menudict = {}
        self.dumped = {}

    def addnode(self, name, next, prev, up, filename):
        node = (name, next, prev, up, filename)
        self.filenames[filename] = filename
        self.nodeindex[name] = len(self.nodelist)
        self.nodelist.append(node)
        self.current = name
        self.menudict[self.current] = []

    def menuitem(self, nodename):
        menu = self.menudict[self.current]
        menu.append(nodename)

    def addimage(self, imagename):
        self.filenames[imagename] = imagename

    def index(self, args, nodename):
        self.indexlist.append((args, nodename))

    def beginmenu(self):
        pass

    def endmenu(self):
        pass

    def finalize(self):
        if (not self.helpbase):
            return
        resultfile = (self.helpbase + '.chm')
        projectfile = (self.helpbase + '.hhp')
        contentfile = (self.helpbase + '.hhc')
        indexfile = (self.helpbase + '.hhk')
        title = self.helpbase
        (topname, topnext, topprev, topup, topfile) = self.nodelist[0]
        defaulttopic = topfile
        try:
            with open(projectfile, 'w') as fp:
                print('[OPTIONS]', file=fp)
                print('Auto Index=Yes', file=fp)
                print('Binary TOC=No', file=fp)
                print('Binary Index=Yes', file=fp)
                print('Compatibility=1.1', file=fp)
                print((('Compiled file=' + resultfile) + ''), file=fp)
                print((('Contents file=' + contentfile) + ''), file=fp)
                print((('Default topic=' + defaulttopic) + ''), file=fp)
                print('Error log file=ErrorLog.log', file=fp)
                print((('Index file=' + indexfile) + ''), file=fp)
                print((('Title=' + title) + ''), file=fp)
                print('Display compile progress=Yes', file=fp)
                print('Full-text search=Yes', file=fp)
                print('Default window=main', file=fp)
                print('', file=fp)
                print('[WINDOWS]', file=fp)
                print((((('main=,"' + contentfile) + '","') + indexfile) + '","","",,,,,0x23520,222,0x1046,[10,10,780,560],0xB0000,,,,,,0'), file=fp)
                print('', file=fp)
                print('[FILES]', file=fp)
                print('', file=fp)
                self.dumpfiles(fp)
        except IOError as msg:
            print(projectfile, ':', msg)
            sys.exit(1)
        try:
            with open(contentfile, 'w') as fp:
                print('<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">', file=fp)
                print('<!-- This file defines the table of contents -->', file=fp)
                print('<HTML>', file=fp)
                print('<HEAD>', file=fp)
                print('<meta name="GENERATOR" content="Microsoft&reg; HTML Help Workshop 4.1">', file=fp)
                print('<!-- Sitemap 1.0 -->', file=fp)
                print('</HEAD>', file=fp)
                print('<BODY>', file=fp)
                print('   <OBJECT type="text/site properties">', file=fp)
                print('     <param name="Window Styles" value="0x800025">', file=fp)
                print('     <param name="comment" value="title:">', file=fp)
                print('     <param name="comment" value="base:">', file=fp)
                print('   </OBJECT>', file=fp)
                self.dumpnodes(fp)
                print('</BODY>', file=fp)
                print('</HTML>', file=fp)
        except IOError as msg:
            print(contentfile, ':', msg)
            sys.exit(1)
        try:
            with open(indexfile, 'w') as fp:
                print('<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">', file=fp)
                print('<!-- This file defines the index -->', file=fp)
                print('<HTML>', file=fp)
                print('<HEAD>', file=fp)
                print('<meta name="GENERATOR" content="Microsoft&reg; HTML Help Workshop 4.1">', file=fp)
                print('<!-- Sitemap 1.0 -->', file=fp)
                print('</HEAD>', file=fp)
                print('<BODY>', file=fp)
                print('<OBJECT type="text/site properties">', file=fp)
                print('</OBJECT>', file=fp)
                self.dumpindex(fp)
                print('</BODY>', file=fp)
                print('</HTML>', file=fp)
        except IOError as msg:
            print(indexfile, ':', msg)
            sys.exit(1)

    def dumpfiles(self, outfile=sys.stdout):
        filelist = sorted(self.filenames.values())
        for filename in filelist:
            print(filename, file=outfile)

    def dumpnodes(self, outfile=sys.stdout):
        self.dumped = {}
        if self.nodelist:
            (nodename, dummy, dummy, dummy, dummy) = self.nodelist[0]
            self.topnode = nodename
        print('<UL>', file=outfile)
        for node in self.nodelist:
            self.dumpnode(node, 0, outfile)
        print('</UL>', file=outfile)

    def dumpnode(self, node, indent=0, outfile=sys.stdout):
        if node:
            (nodename, next, prev, up, filename) = node
            self.current = nodename
            if (nodename in self.dumped):
                return
            self.dumped[nodename] = 1
            print((' ' * indent), end=' ', file=outfile)
            print('<LI><OBJECT type="text/sitemap">', end=' ', file=outfile)
            print((('<param name="Name" value="' + nodename) + '">'), end=' ', file=outfile)
            print((('<param name="Local" value="' + filename) + '">'), end=' ', file=outfile)
            print('</OBJECT>', file=outfile)
            try:
                menu = self.menudict[nodename]
                self.dumpmenu(menu, (indent + 2), outfile)
            except KeyError:
                pass

    def dumpmenu(self, menu, indent=0, outfile=sys.stdout):
        if menu:
            currentnode = self.current
            if (currentnode != self.topnode):
                print(((' ' * indent) + '<UL>'), file=outfile)
                indent += 2
            for item in menu:
                menunode = self.getnode(item)
                self.dumpnode(menunode, indent, outfile)
            if (currentnode != self.topnode):
                print(((' ' * indent) + '</UL>'), file=outfile)
                indent -= 2

    def getnode(self, nodename):
        try:
            index = self.nodeindex[nodename]
            return self.nodelist[index]
        except KeyError:
            return None
        except IndexError:
            return None

    def dumpindex(self, outfile=sys.stdout):
        print('<UL>', file=outfile)
        for (key, location) in self.indexlist:
            key = self.codeexpand(key)
            location = makefile(location)
            location = ((self.dirname + '/') + location)
            print('<LI><OBJECT type="text/sitemap">', end=' ', file=outfile)
            print((('<param name="Name" value="' + key) + '">'), end=' ', file=outfile)
            print((('<param name="Local" value="' + location) + '">'), end=' ', file=outfile)
            print('</OBJECT>', file=outfile)
        print('</UL>', file=outfile)

    def codeexpand(self, line):
        co = self.codeprog.match(line)
        if (not co):
            return line
        (bgn, end) = co.span(0)
        (a, b) = co.span(1)
        line = ((line[:bgn] + line[a:b]) + line[end:])
        return line

def makevar(str):
    return (('@var{' + str) + '}')

def splitwords(str, minlength):
    words = []
    i = 0
    n = len(str)
    while (i < n):
        while ((i < n) and (str[i] in ' \t\n')):
            i = (i + 1)
        if (i >= n):
            break
        start = i
        i = findwordend(str, i, n)
        words.append(str[start:i])
    while (len(words) < minlength):
        words.append('')
    return words
fwprog = re.compile('[@{} ]')

def findwordend(str, i, n):
    level = 0
    while (i < n):
        mo = fwprog.search(str, i)
        if (not mo):
            break
        i = mo.start()
        c = str[i]
        i = (i + 1)
        if (c == '@'):
            i = (i + 1)
        elif (c == '{'):
            level = (level + 1)
        elif (c == '}'):
            level = (level - 1)
        elif ((c == ' ') and (level <= 0)):
            return (i - 1)
    return n

def makefile(nodename):
    nodename = nodename.strip()
    return (fixfunnychars(nodename) + '.html')
goodchars = ((string.ascii_letters + string.digits) + '!@-=+.')

def fixfunnychars(addr):
    i = 0
    while (i < len(addr)):
        c = addr[i]
        if (c not in goodchars):
            c = '-'
            addr = ((addr[:i] + c) + addr[(i + 1):])
        i = (i + len(c))
    return addr

def increment(s):
    if (not s):
        return '1'
    for sequence in (string.digits, string.ascii_lowercase, string.ascii_uppercase):
        lastc = s[(- 1)]
        if (lastc in sequence):
            i = (sequence.index(lastc) + 1)
            if (i >= len(sequence)):
                if (len(s) == 1):
                    s = (sequence[0] * 2)
                    if (s == '00'):
                        s = '10'
                else:
                    s = (increment(s[:(- 1)]) + sequence[0])
            else:
                s = (s[:(- 1)] + sequence[i])
            return s
    return s

def test():
    import sys
    debugging = 0
    print_headers = 0
    cont = 0
    html3 = 0
    htmlhelp = ''
    while (sys.argv[1] == ['-d']):
        debugging = (debugging + 1)
        del sys.argv[1]
    if (sys.argv[1] == '-p'):
        print_headers = 1
        del sys.argv[1]
    if (sys.argv[1] == '-c'):
        cont = 1
        del sys.argv[1]
    if (sys.argv[1] == '-3'):
        html3 = 1
        del sys.argv[1]
    if (sys.argv[1] == '-H'):
        helpbase = sys.argv[2]
        del sys.argv[1:3]
    if (len(sys.argv) != 3):
        print('usage: texi2hh [-d [-d]] [-p] [-c] [-3] [-H htmlhelp]', 'inputfile outputdirectory')
        sys.exit(2)
    if html3:
        parser = TexinfoParserHTML3()
    else:
        parser = TexinfoParser()
    parser.cont = cont
    parser.debugging = debugging
    parser.print_headers = print_headers
    file = sys.argv[1]
    dirname = sys.argv[2]
    parser.setdirname(dirname)
    parser.setincludedir(os.path.dirname(file))
    htmlhelp = HTMLHelp(helpbase, dirname)
    parser.sethtmlhelp(htmlhelp)
    try:
        fp = open(file, 'r')
    except IOError as msg:
        print(file, ':', msg)
        sys.exit(1)
    with fp:
        parser.parse(fp)
    parser.report()
    htmlhelp.finalize()
if (__name__ == '__main__'):
    test()
