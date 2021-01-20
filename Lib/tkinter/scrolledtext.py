
'A ScrolledText widget feels like a text widget but also has a\nvertical scroll bar on its right.  (Later, options may be added to\nadd a horizontal bar as well, to make the bars disappear\nautomatically when not needed, to move them to the other side of the\nwindow, etc.)\n\nConfiguration options are passed to the Text widget.\nA Frame widget is inserted between the master and the text, to hold\nthe Scrollbar widget.\nMost methods calls are inherited from the Text widget; Pack, Grid and\nPlace methods are redirected to the Frame widget however.\n'
from tkinter import Frame, Text, Scrollbar, Pack, Grid, Place
from tkinter.constants import RIGHT, LEFT, Y, BOTH
__all__ = ['ScrolledText']

class ScrolledText(Text):

    def __init__(self, master=None, **kw):
        self.frame = Frame(master)
        self.vbar = Scrollbar(self.frame)
        self.vbar.pack(side=RIGHT, fill=Y)
        kw.update({'yscrollcommand': self.vbar.set})
        Text.__init__(self, self.frame, **kw)
        self.pack(side=LEFT, fill=BOTH, expand=True)
        self.vbar['command'] = self.yview
        text_meths = vars(Text).keys()
        methods = ((vars(Pack).keys() | vars(Grid).keys()) | vars(Place).keys())
        methods = methods.difference(text_meths)
        for m in methods:
            if ((m[0] != '_') and (m != 'config') and (m != 'configure')):
                setattr(self, m, getattr(self.frame, m))

    def __str__(self):
        return str(self.frame)

def example():
    from tkinter.constants import END
    stext = ScrolledText(bg='white', height=10)
    stext.insert(END, __doc__)
    stext.pack(fill=BOTH, side=LEFT, expand=True)
    stext.focus_set()
    stext.mainloop()
if (__name__ == '__main__'):
    example()
