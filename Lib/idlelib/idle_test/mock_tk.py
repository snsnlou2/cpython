
'Classes that replace tkinter gui objects used by an object being tested.\n\nA gui object is anything with a master or parent parameter, which is\ntypically required in spite of what the doc strings say.\n'

class Event():
    "Minimal mock with attributes for testing event handlers.\n\n    This is not a gui object, but is used as an argument for callbacks\n    that access attributes of the event passed. If a callback ignores\n    the event, other than the fact that is happened, pass 'event'.\n\n    Keyboard, mouse, window, and other sources generate Event instances.\n    Event instances have the following attributes: serial (number of\n    event), time (of event), type (of event as number), widget (in which\n    event occurred), and x,y (position of mouse). There are other\n    attributes for specific events, such as keycode for key events.\n    tkinter.Event.__doc__ has more but is still not complete.\n    "

    def __init__(self, **kwds):
        'Create event with attributes needed for test'
        self.__dict__.update(kwds)

class Var():
    'Use for String/Int/BooleanVar: incomplete'

    def __init__(self, master=None, value=None, name=None):
        self.master = master
        self.value = value
        self.name = name

    def set(self, value):
        self.value = value

    def get(self):
        return self.value

class Mbox_func():
    "Generic mock for messagebox functions, which all have the same signature.\n\n    Instead of displaying a message box, the mock's call method saves the\n    arguments as instance attributes, which test functions can then examine.\n    The test can set the result returned to ask function\n    "

    def __init__(self, result=None):
        self.result = result

    def __call__(self, title, message, *args, **kwds):
        self.title = title
        self.message = message
        self.args = args
        self.kwds = kwds
        return self.result

class Mbox():
    "Mock for tkinter.messagebox with an Mbox_func for each function.\n\n    This module was 'tkMessageBox' in 2.x; hence the 'import as' in  3.x.\n    Example usage in test_module.py for testing functions in module.py:\n    ---\nfrom idlelib.idle_test.mock_tk import Mbox\nimport module\n\norig_mbox = module.tkMessageBox\nshowerror = Mbox.showerror  # example, for attribute access in test methods\n\nclass Test(unittest.TestCase):\n\n    @classmethod\n    def setUpClass(cls):\n        module.tkMessageBox = Mbox\n\n    @classmethod\n    def tearDownClass(cls):\n        module.tkMessageBox = orig_mbox\n    ---\n    For 'ask' functions, set func.result return value before calling the method\n    that uses the message function. When tkMessageBox functions are the\n    only gui alls in a method, this replacement makes the method gui-free,\n    "
    askokcancel = Mbox_func()
    askquestion = Mbox_func()
    askretrycancel = Mbox_func()
    askyesno = Mbox_func()
    askyesnocancel = Mbox_func()
    showerror = Mbox_func()
    showinfo = Mbox_func()
    showwarning = Mbox_func()
from _tkinter import TclError

class Text():
    "A semi-functional non-gui replacement for tkinter.Text text editors.\n\n    The mock's data model is that a text is a list of \n-terminated lines.\n    The mock adds an empty string at  the beginning of the list so that the\n    index of actual lines start at 1, as with Tk. The methods never see this.\n    Tk initializes files with a terminal \n that cannot be deleted. It is\n    invisible in the sense that one cannot move the cursor beyond it.\n\n    This class is only tested (and valid) with strings of ascii chars.\n    For testing, we are not concerned with Tk Text's treatment of,\n    for instance, 0-width characters or character + accent.\n   "

    def __init__(self, master=None, cnf={}, **kw):
        'Initialize mock, non-gui, text-only Text widget.\n\n        At present, all args are ignored. Almost all affect visual behavior.\n        There are just a few Text-only options that affect text behavior.\n        '
        self.data = ['', '\n']

    def index(self, index):
        'Return string version of index decoded according to current text.'
        return ('%s.%s' % self._decode(index, endflag=1))

    def _decode(self, index, endflag=0):
        "Return a (line, char) tuple of int indexes into self.data.\n\n        This implements .index without converting the result back to a string.\n        The result is constrained by the number of lines and linelengths of\n        self.data. For many indexes, the result is initially (1, 0).\n\n        The input index may have any of several possible forms:\n        * line.char float: converted to 'line.char' string;\n        * 'line.char' string, where line and char are decimal integers;\n        * 'line.char lineend', where lineend='lineend' (and char is ignored);\n        * 'line.end', where end='end' (same as above);\n        * 'insert', the positions before terminal \n;\n        * 'end', whose meaning depends on the endflag passed to ._endex.\n        * 'sel.first' or 'sel.last', where sel is a tag -- not implemented.\n        "
        if isinstance(index, (float, bytes)):
            index = str(index)
        try:
            index = index.lower()
        except AttributeError:
            raise TclError(('bad text index "%s"' % index)) from None
        lastline = (len(self.data) - 1)
        if (index == 'insert'):
            return (lastline, (len(self.data[lastline]) - 1))
        elif (index == 'end'):
            return self._endex(endflag)
        (line, char) = index.split('.')
        line = int(line)
        if (line < 1):
            return (1, 0)
        elif (line > lastline):
            return self._endex(endflag)
        linelength = (len(self.data[line]) - 1)
        if (char.endswith(' lineend') or (char == 'end')):
            return (line, linelength)
        char = int(char)
        if (char < 0):
            char = 0
        elif (char > linelength):
            char = linelength
        return (line, char)

    def _endex(self, endflag):
        "Return position for 'end' or line overflow corresponding to endflag.\n\n       -1: position before terminal \n; for .insert(), .delete\n       0: position after terminal \n; for .get, .delete index 1\n       1: same viewed as beginning of non-existent next line (for .index)\n       "
        n = len(self.data)
        if (endflag == 1):
            return (n, 0)
        else:
            n -= 1
            return (n, (len(self.data[n]) + endflag))

    def insert(self, index, chars):
        'Insert chars before the character at index.'
        if (not chars):
            return
        chars = chars.splitlines(True)
        if (chars[(- 1)][(- 1)] == '\n'):
            chars.append('')
        (line, char) = self._decode(index, (- 1))
        before = self.data[line][:char]
        after = self.data[line][char:]
        self.data[line] = (before + chars[0])
        self.data[(line + 1):(line + 1)] = chars[1:]
        self.data[((line + len(chars)) - 1)] += after

    def get(self, index1, index2=None):
        "Return slice from index1 to index2 (default is 'index1+1')."
        (startline, startchar) = self._decode(index1)
        if (index2 is None):
            (endline, endchar) = (startline, (startchar + 1))
        else:
            (endline, endchar) = self._decode(index2)
        if (startline == endline):
            return self.data[startline][startchar:endchar]
        else:
            lines = [self.data[startline][startchar:]]
            for i in range((startline + 1), endline):
                lines.append(self.data[i])
            lines.append(self.data[endline][:endchar])
            return ''.join(lines)

    def delete(self, index1, index2=None):
        "Delete slice from index1 to index2 (default is 'index1+1').\n\n        Adjust default index2 ('index+1) for line ends.\n        Do not delete the terminal \n at the very end of self.data ([-1][-1]).\n        "
        (startline, startchar) = self._decode(index1, (- 1))
        if (index2 is None):
            if (startchar < (len(self.data[startline]) - 1)):
                (endline, endchar) = (startline, (startchar + 1))
            elif (startline < (len(self.data) - 1)):
                (endline, endchar) = ((startline + 1), 0)
            else:
                return
        else:
            (endline, endchar) = self._decode(index2, (- 1))
        if ((startline == endline) and (startchar < endchar)):
            self.data[startline] = (self.data[startline][:startchar] + self.data[startline][endchar:])
        elif (startline < endline):
            self.data[startline] = (self.data[startline][:startchar] + self.data[endline][endchar:])
            startline += 1
            for i in range(startline, (endline + 1)):
                del self.data[startline]

    def compare(self, index1, op, index2):
        (line1, char1) = self._decode(index1)
        (line2, char2) = self._decode(index2)
        if (op == '<'):
            return ((line1 < line2) or ((line1 == line2) and (char1 < char2)))
        elif (op == '<='):
            return ((line1 < line2) or ((line1 == line2) and (char1 <= char2)))
        elif (op == '>'):
            return ((line1 > line2) or ((line1 == line2) and (char1 > char2)))
        elif (op == '>='):
            return ((line1 > line2) or ((line1 == line2) and (char1 >= char2)))
        elif (op == '=='):
            return ((line1 == line2) and (char1 == char2))
        elif (op == '!='):
            return ((line1 != line2) or (char1 != char2))
        else:
            raise TclError(('bad comparison operator "%s": must be <, <=, ==, >=, >, or !=' % op))

    def mark_set(self, name, index):
        'Set mark *name* before the character at index.'
        pass

    def mark_unset(self, *markNames):
        'Delete all marks in markNames.'

    def tag_remove(self, tagName, index1, index2=None):
        'Remove tag tagName from all characters between index1 and index2.'
        pass

    def scan_dragto(self, x, y):
        'Adjust the view of the text according to scan_mark'

    def scan_mark(self, x, y):
        'Remember the current X, Y coordinates.'

    def see(self, index):
        'Scroll screen to make the character at INDEX is visible.'
        pass

    def bind(sequence=None, func=None, add=None):
        'Bind to this widget at event sequence a call to function func.'
        pass

class Entry():
    'Mock for tkinter.Entry.'

    def focus_set(self):
        pass
