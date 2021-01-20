
'Main Pynche (Pythonically Natural Color and Hue Editor) widget.\n\nThis window provides the basic decorations, primarily including the menubar.\nIt is used to bring up other windows.\n'
import sys
import os
from tkinter import *
from tkinter import messagebox, filedialog
import ColorDB
KEEPALIVE_TIMER = 500

class PyncheWidget():

    def __init__(self, version, switchboard, master=None, extrapath=[]):
        self.__sb = switchboard
        self.__version = version
        self.__textwin = None
        self.__listwin = None
        self.__detailswin = None
        self.__helpwin = None
        self.__dialogstate = {}
        modal = self.__modal = (not (not master))
        if modal:
            self.__tkroot = tkroot = Toplevel(master, class_='Pynche')
            tkroot.grab_set()
            tkroot.withdraw()
        else:
            tkroot = None
            try:
                from Tkinter import _default_root
                tkroot = self.__tkroot = _default_root
            except ImportError:
                pass
            if (not tkroot):
                tkroot = self.__tkroot = Tk(className='Pynche')
            tkroot.withdraw()
        menubar = self.__menubar = Menu(tkroot)
        filemenu = self.__filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label='Load palette...', command=self.__load, underline=0)
        if (not modal):
            filemenu.add_command(label='Quit', command=self.__quit, accelerator='Alt-Q', underline=0)
        views = make_view_popups(self.__sb, self.__tkroot, extrapath)
        viewmenu = Menu(menubar, tearoff=0)
        for v in views:
            viewmenu.add_command(label=v.menutext(), command=v.popup, underline=v.underline())
        helpmenu = Menu(menubar, name='help', tearoff=0)
        helpmenu.add_command(label='About Pynche...', command=self.__popup_about, underline=0)
        helpmenu.add_command(label='Help...', command=self.__popup_usage, underline=0)
        menubar.add_cascade(label='File', menu=filemenu, underline=0)
        menubar.add_cascade(label='View', menu=viewmenu, underline=0)
        menubar.add_cascade(label='Help', menu=helpmenu, underline=0)
        root = self.__root = Toplevel(tkroot, class_='Pynche', menu=menubar)
        root.protocol('WM_DELETE_WINDOW', ((modal and self.__bell) or self.__quit))
        root.title(('Pynche %s' % version))
        root.iconname('Pynche')
        if (not modal):
            root.bind('<Alt-q>', self.__quit)
            root.bind('<Alt-Q>', self.__quit)
        else:
            bframe = Frame(root, borderwidth=1, relief=RAISED)
            bframe.grid(row=4, column=0, columnspan=2, sticky='EW', ipady=5)
            okay = Button(bframe, text='Okay', command=self.__okay)
            okay.pack(side=LEFT, expand=1)
            cancel = Button(bframe, text='Cancel', command=self.__cancel)
            cancel.pack(side=LEFT, expand=1)

    def __quit(self, event=None):
        self.__tkroot.quit()

    def __bell(self, event=None):
        self.__tkroot.bell()

    def __okay(self, event=None):
        self.__sb.withdraw_views()
        self.__tkroot.grab_release()
        self.__quit()

    def __cancel(self, event=None):
        self.__sb.canceled()
        self.__okay()

    def __keepalive(self):
        self.__tkroot.tk.createtimerhandler(KEEPALIVE_TIMER, self.__keepalive)

    def start(self):
        if (not self.__modal):
            self.__keepalive()
        self.__tkroot.mainloop()

    def window(self):
        return self.__root

    def __popup_about(self, event=None):
        from Main import __version__
        messagebox.showinfo(('About Pynche ' + __version__), ('Pynche %s\nThe PYthonically Natural\nColor and Hue Editor\n\nFor information\ncontact: Barry A. Warsaw\nemail:   bwarsaw@python.org' % __version__))

    def __popup_usage(self, event=None):
        if (not self.__helpwin):
            self.__helpwin = Helpwin(self.__root, self.__quit)
        self.__helpwin.deiconify()

    def __load(self, event=None):
        while 1:
            (idir, ifile) = os.path.split(self.__sb.colordb().filename())
            file = filedialog.askopenfilename(filetypes=[('Text files', '*.txt'), ('All files', '*')], initialdir=idir, initialfile=ifile)
            if (not file):
                return
            try:
                colordb = ColorDB.get_colordb(file)
            except IOError:
                messagebox.showerror('Read error', ('Could not open file for reading:\n%s' % file))
                continue
            if (colordb is None):
                messagebox.showerror('Unrecognized color file type', ('Unrecognized color file type in file:\n%s' % file))
                continue
            break
        self.__sb.set_colordb(colordb)

    def withdraw(self):
        self.__root.withdraw()

    def deiconify(self):
        self.__root.deiconify()

class Helpwin():

    def __init__(self, master, quitfunc):
        from Main import docstring
        self.__root = root = Toplevel(master, class_='Pynche')
        root.protocol('WM_DELETE_WINDOW', self.__withdraw)
        root.title('Pynche Help Window')
        root.iconname('Pynche Help Window')
        root.bind('<Alt-q>', quitfunc)
        root.bind('<Alt-Q>', quitfunc)
        root.bind('<Alt-w>', self.__withdraw)
        root.bind('<Alt-W>', self.__withdraw)
        readmefile = os.path.join(sys.path[0], 'README')
        try:
            fp = None
            try:
                fp = open(readmefile)
                contents = fp.read()
                i = contents.rfind('\x0c')
                if (i > 0):
                    contents = contents[:i].rstrip()
            finally:
                if fp:
                    fp.close()
        except IOError:
            sys.stderr.write("Couldn't open Pynche's README, using docstring instead.\n")
            contents = docstring()
        self.__text = text = Text(root, relief=SUNKEN, width=80, height=24)
        self.__text.focus_set()
        text.insert(0.0, contents)
        scrollbar = Scrollbar(root)
        scrollbar.pack(fill=Y, side=RIGHT)
        text.pack(fill=BOTH, expand=YES)
        text.configure(yscrollcommand=(scrollbar, 'set'))
        scrollbar.configure(command=(text, 'yview'))

    def __withdraw(self, event=None):
        self.__root.withdraw()

    def deiconify(self):
        self.__root.deiconify()
import functools

@functools.total_ordering
class PopupViewer():

    def __init__(self, module, name, switchboard, root):
        self.__m = module
        self.__name = name
        self.__sb = switchboard
        self.__root = root
        self.__menutext = module.ADDTOVIEW
        underline = module.ADDTOVIEW.find('%')
        if (underline == (- 1)):
            underline = 0
        else:
            self.__menutext = module.ADDTOVIEW.replace('%', '', 1)
        self.__underline = underline
        self.__window = None

    def menutext(self):
        return self.__menutext

    def underline(self):
        return self.__underline

    def popup(self, event=None):
        if (not self.__window):
            class_ = getattr(self.__m, self.__name)
            self.__window = class_(self.__sb, self.__root)
            self.__sb.add_view(self.__window)
        self.__window.deiconify()

    def __eq__(self, other):
        if isinstance(self, PopupViewer):
            return (self.__menutext == other.__menutext)
        return NotImplemented

    def __lt__(self, other):
        if isinstance(self, PopupViewer):
            return (self.__menutext < other.__menutext)
        return NotImplemented

def make_view_popups(switchboard, root, extrapath):
    viewers = []
    dirs = ([os.path.dirname(__file__)] + extrapath)
    for dir in dirs:
        if (dir == ''):
            dir = '.'
        for file in os.listdir(dir):
            if (file[(- 9):] == 'Viewer.py'):
                name = file[:(- 3)]
                try:
                    module = __import__(name)
                except ImportError:
                    pkg = __import__(('pynche.' + name))
                    module = getattr(pkg, name)
                if (hasattr(module, 'ADDTOVIEW') and module.ADDTOVIEW):
                    v = PopupViewer(module, name, switchboard, root)
                    viewers.append(v)
    viewers.sort()
    return viewers
