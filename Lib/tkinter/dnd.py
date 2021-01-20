
"Drag-and-drop support for Tkinter.\n\nThis is very preliminary.  I currently only support dnd *within* one\napplication, between different windows (or within the same window).\n\nI am trying to make this as generic as possible -- not dependent on\nthe use of a particular widget or icon type, etc.  I also hope that\nthis will work with Pmw.\n\nTo enable an object to be dragged, you must create an event binding\nfor it that starts the drag-and-drop process. Typically, you should\nbind <ButtonPress> to a callback function that you write. The function\nshould call Tkdnd.dnd_start(source, event), where 'source' is the\nobject to be dragged, and 'event' is the event that invoked the call\n(the argument to your callback function).  Even though this is a class\ninstantiation, the returned instance should not be stored -- it will\nbe kept alive automatically for the duration of the drag-and-drop.\n\nWhen a drag-and-drop is already in process for the Tk interpreter, the\ncall is *ignored*; this normally averts starting multiple simultaneous\ndnd processes, e.g. because different button callbacks all\ndnd_start().\n\nThe object is *not* necessarily a widget -- it can be any\napplication-specific object that is meaningful to potential\ndrag-and-drop targets.\n\nPotential drag-and-drop targets are discovered as follows.  Whenever\nthe mouse moves, and at the start and end of a drag-and-drop move, the\nTk widget directly under the mouse is inspected.  This is the target\nwidget (not to be confused with the target object, yet to be\ndetermined).  If there is no target widget, there is no dnd target\nobject.  If there is a target widget, and it has an attribute\ndnd_accept, this should be a function (or any callable object).  The\nfunction is called as dnd_accept(source, event), where 'source' is the\nobject being dragged (the object passed to dnd_start() above), and\n'event' is the most recent event object (generally a <Motion> event;\nit can also be <ButtonPress> or <ButtonRelease>).  If the dnd_accept()\nfunction returns something other than None, this is the new dnd target\nobject.  If dnd_accept() returns None, or if the target widget has no\ndnd_accept attribute, the target widget's parent is considered as the\ntarget widget, and the search for a target object is repeated from\nthere.  If necessary, the search is repeated all the way up to the\nroot widget.  If none of the target widgets can produce a target\nobject, there is no target object (the target object is None).\n\nThe target object thus produced, if any, is called the new target\nobject.  It is compared with the old target object (or None, if there\nwas no old target widget).  There are several cases ('source' is the\nsource object, and 'event' is the most recent event object):\n\n- Both the old and new target objects are None.  Nothing happens.\n\n- The old and new target objects are the same object.  Its method\ndnd_motion(source, event) is called.\n\n- The old target object was None, and the new target object is not\nNone.  The new target object's method dnd_enter(source, event) is\ncalled.\n\n- The new target object is None, and the old target object is not\nNone.  The old target object's method dnd_leave(source, event) is\ncalled.\n\n- The old and new target objects differ and neither is None.  The old\ntarget object's method dnd_leave(source, event), and then the new\ntarget object's method dnd_enter(source, event) is called.\n\nOnce this is done, the new target object replaces the old one, and the\nTk mainloop proceeds.  The return value of the methods mentioned above\nis ignored; if they raise an exception, the normal exception handling\nmechanisms take over.\n\nThe drag-and-drop processes can end in two ways: a final target object\nis selected, or no final target object is selected.  When a final\ntarget object is selected, it will always have been notified of the\npotential drop by a call to its dnd_enter() method, as described\nabove, and possibly one or more calls to its dnd_motion() method; its\ndnd_leave() method has not been called since the last call to\ndnd_enter().  The target is notified of the drop by a call to its\nmethod dnd_commit(source, event).\n\nIf no final target object is selected, and there was an old target\nobject, its dnd_leave(source, event) method is called to complete the\ndnd sequence.\n\nFinally, the source object is notified that the drag-and-drop process\nis over, by a call to source.dnd_end(target, event), specifying either\nthe selected target object, or None if no target object was selected.\nThe source object can use this to implement the commit action; this is\nsometimes simpler than to do it in the target's dnd_commit().  The\ntarget's dnd_commit() method could then simply be aliased to\ndnd_leave().\n\nAt any time during a dnd sequence, the application can cancel the\nsequence by calling the cancel() method on the object returned by\ndnd_start().  This will call dnd_leave() if a target is currently\nactive; it will never call dnd_commit().\n\n"
import tkinter
__all__ = ['dnd_start', 'DndHandler']

def dnd_start(source, event):
    h = DndHandler(source, event)
    if h.root:
        return h
    else:
        return None

class DndHandler():
    root = None

    def __init__(self, source, event):
        if (event.num > 5):
            return
        root = event.widget._root()
        try:
            root.__dnd
            return
        except AttributeError:
            root.__dnd = self
            self.root = root
        self.source = source
        self.target = None
        self.initial_button = button = event.num
        self.initial_widget = widget = event.widget
        self.release_pattern = ('<B%d-ButtonRelease-%d>' % (button, button))
        self.save_cursor = (widget['cursor'] or '')
        widget.bind(self.release_pattern, self.on_release)
        widget.bind('<Motion>', self.on_motion)
        widget['cursor'] = 'hand2'

    def __del__(self):
        root = self.root
        self.root = None
        if root:
            try:
                del root.__dnd
            except AttributeError:
                pass

    def on_motion(self, event):
        (x, y) = (event.x_root, event.y_root)
        target_widget = self.initial_widget.winfo_containing(x, y)
        source = self.source
        new_target = None
        while target_widget:
            try:
                attr = target_widget.dnd_accept
            except AttributeError:
                pass
            else:
                new_target = attr(source, event)
                if new_target:
                    break
            target_widget = target_widget.master
        old_target = self.target
        if (old_target is new_target):
            if old_target:
                old_target.dnd_motion(source, event)
        else:
            if old_target:
                self.target = None
                old_target.dnd_leave(source, event)
            if new_target:
                new_target.dnd_enter(source, event)
                self.target = new_target

    def on_release(self, event):
        self.finish(event, 1)

    def cancel(self, event=None):
        self.finish(event, 0)

    def finish(self, event, commit=0):
        target = self.target
        source = self.source
        widget = self.initial_widget
        root = self.root
        try:
            del root.__dnd
            self.initial_widget.unbind(self.release_pattern)
            self.initial_widget.unbind('<Motion>')
            widget['cursor'] = self.save_cursor
            self.target = self.source = self.initial_widget = self.root = None
            if target:
                if commit:
                    target.dnd_commit(source, event)
                else:
                    target.dnd_leave(source, event)
        finally:
            source.dnd_end(target, event)

class Icon():

    def __init__(self, name):
        self.name = name
        self.canvas = self.label = self.id = None

    def attach(self, canvas, x=10, y=10):
        if (canvas is self.canvas):
            self.canvas.coords(self.id, x, y)
            return
        if self.canvas:
            self.detach()
        if (not canvas):
            return
        label = tkinter.Label(canvas, text=self.name, borderwidth=2, relief='raised')
        id = canvas.create_window(x, y, window=label, anchor='nw')
        self.canvas = canvas
        self.label = label
        self.id = id
        label.bind('<ButtonPress>', self.press)

    def detach(self):
        canvas = self.canvas
        if (not canvas):
            return
        id = self.id
        label = self.label
        self.canvas = self.label = self.id = None
        canvas.delete(id)
        label.destroy()

    def press(self, event):
        if dnd_start(self, event):
            self.x_off = event.x
            self.y_off = event.y
            (self.x_orig, self.y_orig) = self.canvas.coords(self.id)

    def move(self, event):
        (x, y) = self.where(self.canvas, event)
        self.canvas.coords(self.id, x, y)

    def putback(self):
        self.canvas.coords(self.id, self.x_orig, self.y_orig)

    def where(self, canvas, event):
        x_org = canvas.winfo_rootx()
        y_org = canvas.winfo_rooty()
        x = (event.x_root - x_org)
        y = (event.y_root - y_org)
        return ((x - self.x_off), (y - self.y_off))

    def dnd_end(self, target, event):
        pass

class Tester():

    def __init__(self, root):
        self.top = tkinter.Toplevel(root)
        self.canvas = tkinter.Canvas(self.top, width=100, height=100)
        self.canvas.pack(fill='both', expand=1)
        self.canvas.dnd_accept = self.dnd_accept

    def dnd_accept(self, source, event):
        return self

    def dnd_enter(self, source, event):
        self.canvas.focus_set()
        (x, y) = source.where(self.canvas, event)
        (x1, y1, x2, y2) = source.canvas.bbox(source.id)
        (dx, dy) = ((x2 - x1), (y2 - y1))
        self.dndid = self.canvas.create_rectangle(x, y, (x + dx), (y + dy))
        self.dnd_motion(source, event)

    def dnd_motion(self, source, event):
        (x, y) = source.where(self.canvas, event)
        (x1, y1, x2, y2) = self.canvas.bbox(self.dndid)
        self.canvas.move(self.dndid, (x - x1), (y - y1))

    def dnd_leave(self, source, event):
        self.top.focus_set()
        self.canvas.delete(self.dndid)
        self.dndid = None

    def dnd_commit(self, source, event):
        self.dnd_leave(source, event)
        (x, y) = source.where(self.canvas, event)
        source.attach(self.canvas, x, y)

def test():
    root = tkinter.Tk()
    root.geometry('+1+1')
    tkinter.Button(command=root.quit, text='Quit').pack()
    t1 = Tester(root)
    t1.top.geometry('+1+60')
    t2 = Tester(root)
    t2.top.geometry('+120+60')
    t3 = Tester(root)
    t3.top.geometry('+240+60')
    i1 = Icon('ICON1')
    i2 = Icon('ICON2')
    i3 = Icon('ICON3')
    i1.attach(t1.canvas)
    i2.attach(t2.canvas)
    i3.attach(t3.canvas)
    root.mainloop()
if (__name__ == '__main__'):
    test()
