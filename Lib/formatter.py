
"Generic output formatting.\n\nFormatter objects transform an abstract flow of formatting events into\nspecific output events on writer objects. Formatters manage several stack\nstructures to allow various properties of a writer object to be changed and\nrestored; writers need not be able to handle relative changes nor any sort\nof ``change back'' operation. Specific writer properties which may be\ncontrolled via formatter objects are horizontal alignment, font, and left\nmargin indentations. A mechanism is provided which supports providing\narbitrary, non-exclusive style settings to a writer as well. Additional\ninterfaces facilitate formatting events which are not reversible, such as\nparagraph separation.\n\nWriter objects encapsulate device interfaces. Abstract devices, such as\nfile formats, are supported as well as physical devices. The provided\nimplementations all work with abstract devices. The interface makes\navailable mechanisms for setting the properties which formatter objects\nmanage and inserting data into the output.\n"
import sys
import warnings
warnings.warn('the formatter module is deprecated', DeprecationWarning, stacklevel=2)
AS_IS = None

class NullFormatter():
    "A formatter which does nothing.\n\n    If the writer parameter is omitted, a NullWriter instance is created.\n    No methods of the writer are called by NullFormatter instances.\n\n    Implementations should inherit from this class if implementing a writer\n    interface but don't need to inherit any implementation.\n\n    "

    def __init__(self, writer=None):
        if (writer is None):
            writer = NullWriter()
        self.writer = writer

    def end_paragraph(self, blankline):
        pass

    def add_line_break(self):
        pass

    def add_hor_rule(self, *args, **kw):
        pass

    def add_label_data(self, format, counter, blankline=None):
        pass

    def add_flowing_data(self, data):
        pass

    def add_literal_data(self, data):
        pass

    def flush_softspace(self):
        pass

    def push_alignment(self, align):
        pass

    def pop_alignment(self):
        pass

    def push_font(self, x):
        pass

    def pop_font(self):
        pass

    def push_margin(self, margin):
        pass

    def pop_margin(self):
        pass

    def set_spacing(self, spacing):
        pass

    def push_style(self, *styles):
        pass

    def pop_style(self, n=1):
        pass

    def assert_line_data(self, flag=1):
        pass

class AbstractFormatter():
    'The standard formatter.\n\n    This implementation has demonstrated wide applicability to many writers,\n    and may be used directly in most circumstances.  It has been used to\n    implement a full-featured World Wide Web browser.\n\n    '

    def __init__(self, writer):
        self.writer = writer
        self.align = None
        self.align_stack = []
        self.font_stack = []
        self.margin_stack = []
        self.spacing = None
        self.style_stack = []
        self.nospace = 1
        self.softspace = 0
        self.para_end = 1
        self.parskip = 0
        self.hard_break = 1
        self.have_label = 0

    def end_paragraph(self, blankline):
        if (not self.hard_break):
            self.writer.send_line_break()
            self.have_label = 0
        if ((self.parskip < blankline) and (not self.have_label)):
            self.writer.send_paragraph((blankline - self.parskip))
            self.parskip = blankline
            self.have_label = 0
        self.hard_break = self.nospace = self.para_end = 1
        self.softspace = 0

    def add_line_break(self):
        if (not (self.hard_break or self.para_end)):
            self.writer.send_line_break()
            self.have_label = self.parskip = 0
        self.hard_break = self.nospace = 1
        self.softspace = 0

    def add_hor_rule(self, *args, **kw):
        if (not self.hard_break):
            self.writer.send_line_break()
        self.writer.send_hor_rule(*args, **kw)
        self.hard_break = self.nospace = 1
        self.have_label = self.para_end = self.softspace = self.parskip = 0

    def add_label_data(self, format, counter, blankline=None):
        if (self.have_label or (not self.hard_break)):
            self.writer.send_line_break()
        if (not self.para_end):
            self.writer.send_paragraph(((blankline and 1) or 0))
        if isinstance(format, str):
            self.writer.send_label_data(self.format_counter(format, counter))
        else:
            self.writer.send_label_data(format)
        self.nospace = self.have_label = self.hard_break = self.para_end = 1
        self.softspace = self.parskip = 0

    def format_counter(self, format, counter):
        label = ''
        for c in format:
            if (c == '1'):
                label = (label + ('%d' % counter))
            elif (c in 'aA'):
                if (counter > 0):
                    label = (label + self.format_letter(c, counter))
            elif (c in 'iI'):
                if (counter > 0):
                    label = (label + self.format_roman(c, counter))
            else:
                label = (label + c)
        return label

    def format_letter(self, case, counter):
        label = ''
        while (counter > 0):
            (counter, x) = divmod((counter - 1), 26)
            s = chr((ord(case) + x))
            label = (s + label)
        return label

    def format_roman(self, case, counter):
        ones = ['i', 'x', 'c', 'm']
        fives = ['v', 'l', 'd']
        (label, index) = ('', 0)
        while (counter > 0):
            (counter, x) = divmod(counter, 10)
            if (x == 9):
                label = ((ones[index] + ones[(index + 1)]) + label)
            elif (x == 4):
                label = ((ones[index] + fives[index]) + label)
            else:
                if (x >= 5):
                    s = fives[index]
                    x = (x - 5)
                else:
                    s = ''
                s = (s + (ones[index] * x))
                label = (s + label)
            index = (index + 1)
        if (case == 'I'):
            return label.upper()
        return label

    def add_flowing_data(self, data):
        if (not data):
            return
        prespace = data[:1].isspace()
        postspace = data[(- 1):].isspace()
        data = ' '.join(data.split())
        if (self.nospace and (not data)):
            return
        elif (prespace or self.softspace):
            if (not data):
                if (not self.nospace):
                    self.softspace = 1
                    self.parskip = 0
                return
            if (not self.nospace):
                data = (' ' + data)
        self.hard_break = self.nospace = self.para_end = self.parskip = self.have_label = 0
        self.softspace = postspace
        self.writer.send_flowing_data(data)

    def add_literal_data(self, data):
        if (not data):
            return
        if self.softspace:
            self.writer.send_flowing_data(' ')
        self.hard_break = (data[(- 1):] == '\n')
        self.nospace = self.para_end = self.softspace = self.parskip = self.have_label = 0
        self.writer.send_literal_data(data)

    def flush_softspace(self):
        if self.softspace:
            self.hard_break = self.para_end = self.parskip = self.have_label = self.softspace = 0
            self.nospace = 1
            self.writer.send_flowing_data(' ')

    def push_alignment(self, align):
        if (align and (align != self.align)):
            self.writer.new_alignment(align)
            self.align = align
            self.align_stack.append(align)
        else:
            self.align_stack.append(self.align)

    def pop_alignment(self):
        if self.align_stack:
            del self.align_stack[(- 1)]
        if self.align_stack:
            self.align = align = self.align_stack[(- 1)]
            self.writer.new_alignment(align)
        else:
            self.align = None
            self.writer.new_alignment(None)

    def push_font(self, font):
        (size, i, b, tt) = font
        if self.softspace:
            self.hard_break = self.para_end = self.softspace = 0
            self.nospace = 1
            self.writer.send_flowing_data(' ')
        if self.font_stack:
            (csize, ci, cb, ctt) = self.font_stack[(- 1)]
            if (size is AS_IS):
                size = csize
            if (i is AS_IS):
                i = ci
            if (b is AS_IS):
                b = cb
            if (tt is AS_IS):
                tt = ctt
        font = (size, i, b, tt)
        self.font_stack.append(font)
        self.writer.new_font(font)

    def pop_font(self):
        if self.font_stack:
            del self.font_stack[(- 1)]
        if self.font_stack:
            font = self.font_stack[(- 1)]
        else:
            font = None
        self.writer.new_font(font)

    def push_margin(self, margin):
        self.margin_stack.append(margin)
        fstack = [m for m in self.margin_stack if m]
        if ((not margin) and fstack):
            margin = fstack[(- 1)]
        self.writer.new_margin(margin, len(fstack))

    def pop_margin(self):
        if self.margin_stack:
            del self.margin_stack[(- 1)]
        fstack = [m for m in self.margin_stack if m]
        if fstack:
            margin = fstack[(- 1)]
        else:
            margin = None
        self.writer.new_margin(margin, len(fstack))

    def set_spacing(self, spacing):
        self.spacing = spacing
        self.writer.new_spacing(spacing)

    def push_style(self, *styles):
        if self.softspace:
            self.hard_break = self.para_end = self.softspace = 0
            self.nospace = 1
            self.writer.send_flowing_data(' ')
        for style in styles:
            self.style_stack.append(style)
        self.writer.new_styles(tuple(self.style_stack))

    def pop_style(self, n=1):
        del self.style_stack[(- n):]
        self.writer.new_styles(tuple(self.style_stack))

    def assert_line_data(self, flag=1):
        self.nospace = self.hard_break = (not flag)
        self.para_end = self.parskip = self.have_label = 0

class NullWriter():
    'Minimal writer interface to use in testing & inheritance.\n\n    A writer which only provides the interface definition; no actions are\n    taken on any methods.  This should be the base class for all writers\n    which do not need to inherit any implementation methods.\n\n    '

    def __init__(self):
        pass

    def flush(self):
        pass

    def new_alignment(self, align):
        pass

    def new_font(self, font):
        pass

    def new_margin(self, margin, level):
        pass

    def new_spacing(self, spacing):
        pass

    def new_styles(self, styles):
        pass

    def send_paragraph(self, blankline):
        pass

    def send_line_break(self):
        pass

    def send_hor_rule(self, *args, **kw):
        pass

    def send_label_data(self, data):
        pass

    def send_flowing_data(self, data):
        pass

    def send_literal_data(self, data):
        pass

class AbstractWriter(NullWriter):
    'A writer which can be used in debugging formatters, but not much else.\n\n    Each method simply announces itself by printing its name and\n    arguments on standard output.\n\n    '

    def new_alignment(self, align):
        print(('new_alignment(%r)' % (align,)))

    def new_font(self, font):
        print(('new_font(%r)' % (font,)))

    def new_margin(self, margin, level):
        print(('new_margin(%r, %d)' % (margin, level)))

    def new_spacing(self, spacing):
        print(('new_spacing(%r)' % (spacing,)))

    def new_styles(self, styles):
        print(('new_styles(%r)' % (styles,)))

    def send_paragraph(self, blankline):
        print(('send_paragraph(%r)' % (blankline,)))

    def send_line_break(self):
        print('send_line_break()')

    def send_hor_rule(self, *args, **kw):
        print('send_hor_rule()')

    def send_label_data(self, data):
        print(('send_label_data(%r)' % (data,)))

    def send_flowing_data(self, data):
        print(('send_flowing_data(%r)' % (data,)))

    def send_literal_data(self, data):
        print(('send_literal_data(%r)' % (data,)))

class DumbWriter(NullWriter):
    'Simple writer class which writes output on the file object passed in\n    as the file parameter or, if file is omitted, on standard output.  The\n    output is simply word-wrapped to the number of columns specified by\n    the maxcol parameter.  This class is suitable for reflowing a sequence\n    of paragraphs.\n\n    '

    def __init__(self, file=None, maxcol=72):
        self.file = (file or sys.stdout)
        self.maxcol = maxcol
        NullWriter.__init__(self)
        self.reset()

    def reset(self):
        self.col = 0
        self.atbreak = 0

    def send_paragraph(self, blankline):
        self.file.write(('\n' * blankline))
        self.col = 0
        self.atbreak = 0

    def send_line_break(self):
        self.file.write('\n')
        self.col = 0
        self.atbreak = 0

    def send_hor_rule(self, *args, **kw):
        self.file.write('\n')
        self.file.write(('-' * self.maxcol))
        self.file.write('\n')
        self.col = 0
        self.atbreak = 0

    def send_literal_data(self, data):
        self.file.write(data)
        i = data.rfind('\n')
        if (i >= 0):
            self.col = 0
            data = data[(i + 1):]
        data = data.expandtabs()
        self.col = (self.col + len(data))
        self.atbreak = 0

    def send_flowing_data(self, data):
        if (not data):
            return
        atbreak = (self.atbreak or data[0].isspace())
        col = self.col
        maxcol = self.maxcol
        write = self.file.write
        for word in data.split():
            if atbreak:
                if ((col + len(word)) >= maxcol):
                    write('\n')
                    col = 0
                else:
                    write(' ')
                    col = (col + 1)
            write(word)
            col = (col + len(word))
            atbreak = 1
        self.col = col
        self.atbreak = data[(- 1)].isspace()

def test(file=None):
    w = DumbWriter()
    f = AbstractFormatter(w)
    if (file is not None):
        fp = open(file)
    elif sys.argv[1:]:
        fp = open(sys.argv[1])
    else:
        fp = sys.stdin
    try:
        for line in fp:
            if (line == '\n'):
                f.end_paragraph(1)
            else:
                f.add_flowing_data(line)
    finally:
        if (fp is not sys.stdin):
            fp.close()
    f.end_paragraph(0)
if (__name__ == '__main__'):
    test()
