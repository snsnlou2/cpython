
'Search dialog for Find, Find Again, and Find Selection\n   functionality.\n\n   Inherits from SearchDialogBase for GUI and uses searchengine\n   to prepare search pattern.\n'
from tkinter import TclError
from idlelib import searchengine
from idlelib.searchbase import SearchDialogBase

def _setup(text):
    'Return the new or existing singleton SearchDialog instance.\n\n    The singleton dialog saves user entries and preferences\n    across instances.\n\n    Args:\n        text: Text widget containing the text to be searched.\n    '
    root = text._root()
    engine = searchengine.get(root)
    if (not hasattr(engine, '_searchdialog')):
        engine._searchdialog = SearchDialog(root, engine)
    return engine._searchdialog

def find(text):
    'Open the search dialog.\n\n    Module-level function to access the singleton SearchDialog\n    instance and open the dialog.  If text is selected, it is\n    used as the search phrase; otherwise, the previous entry\n    is used.  No search is done with this command.\n    '
    pat = text.get('sel.first', 'sel.last')
    return _setup(text).open(text, pat)

def find_again(text):
    'Repeat the search for the last pattern and preferences.\n\n    Module-level function to access the singleton SearchDialog\n    instance to search again using the user entries and preferences\n    from the last dialog.  If there was no prior search, open the\n    search dialog; otherwise, perform the search without showing the\n    dialog.\n    '
    return _setup(text).find_again(text)

def find_selection(text):
    "Search for the selected pattern in the text.\n\n    Module-level function to access the singleton SearchDialog\n    instance to search using the selected text.  With a text\n    selection, perform the search without displaying the dialog.\n    Without a selection, use the prior entry as the search phrase\n    and don't display the dialog.  If there has been no prior\n    search, open the search dialog.\n    "
    return _setup(text).find_selection(text)

class SearchDialog(SearchDialogBase):
    'Dialog for finding a pattern in text.'

    def create_widgets(self):
        'Create the base search dialog and add a button for Find Next.'
        SearchDialogBase.create_widgets(self)
        self.make_button('Find Next', self.default_command, isdef=True)

    def default_command(self, event=None):
        'Handle the Find Next button as the default command.'
        if (not self.engine.getprog()):
            return
        self.find_again(self.text)

    def find_again(self, text):
        "Repeat the last search.\n\n        If no search was previously run, open a new search dialog.  In\n        this case, no search is done.\n\n        If a search was previously run, the search dialog won't be\n        shown and the options from the previous search (including the\n        search pattern) will be used to find the next occurrence\n        of the pattern.  Next is relative based on direction.\n\n        Position the window to display the located occurrence in the\n        text.\n\n        Return True if the search was successful and False otherwise.\n        "
        if (not self.engine.getpat()):
            self.open(text)
            return False
        if (not self.engine.getprog()):
            return False
        res = self.engine.search_text(text)
        if res:
            (line, m) = res
            (i, j) = m.span()
            first = ('%d.%d' % (line, i))
            last = ('%d.%d' % (line, j))
            try:
                selfirst = text.index('sel.first')
                sellast = text.index('sel.last')
                if ((selfirst == first) and (sellast == last)):
                    self.bell()
                    return False
            except TclError:
                pass
            text.tag_remove('sel', '1.0', 'end')
            text.tag_add('sel', first, last)
            text.mark_set('insert', ((self.engine.isback() and first) or last))
            text.see('insert')
            return True
        else:
            self.bell()
            return False

    def find_selection(self, text):
        "Search for selected text with previous dialog preferences.\n\n        Instead of using the same pattern for searching (as Find\n        Again does), this first resets the pattern to the currently\n        selected text.  If the selected text isn't changed, then use\n        the prior search phrase.\n        "
        pat = text.get('sel.first', 'sel.last')
        if pat:
            self.engine.setcookedpat(pat)
        return self.find_again(text)

def _search_dialog(parent):
    'Display search test box.'
    from tkinter import Toplevel, Text
    from tkinter.ttk import Frame, Button
    top = Toplevel(parent)
    top.title('Test SearchDialog')
    (x, y) = map(int, parent.geometry().split('+')[1:])
    top.geometry(('+%d+%d' % (x, (y + 175))))
    frame = Frame(top)
    frame.pack()
    text = Text(frame, inactiveselectbackground='gray')
    text.pack()
    text.insert('insert', ('This is a sample string.\n' * 5))

    def show_find():
        text.tag_add('sel', '1.0', 'end')
        _setup(text).open(text)
        text.tag_remove('sel', '1.0', 'end')
    button = Button(frame, text='Search (selection ignored)', command=show_find)
    button.pack()
if (__name__ == '__main__'):
    from unittest import main
    main('idlelib.idle_test.test_search', verbosity=2, exit=False)
    from idlelib.idle_test.htest import run
    run(_search_dialog)
