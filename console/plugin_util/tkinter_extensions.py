#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)
__all__ = ['DragDropListbox', 'MultiListbox', 'Tooltip']


import tkinter

from types import MappingProxyType
from typing import Mapping


# TODO: Support [TkinterDnD2](http://tkinterdnd.sourceforge.net/)
class DragDropListbox(tkinter.Listbox):

    def __init__(self, *args, data=None, **kwds):
        super().__init__(*args, **kwds)
        if data is None:
            self._data = []
        else:
            self._data = data
            super().insert(0, *data)
        self.curIndex = None
        self.bind('<Button-1>', self.setCurrent)
        self.bind('<B1-Motion>', self.shiftSelection)
        self.bind("<Up>", self.onKeyUp)
        self.bind("<Down>", self.onKeyDown)
        self.bind("<BackSpace>", self.onKeyBackSpace)

    def delete(self, first, last=None):
        super().delete(first, last)
        if last is None:
            del self._data[first]
        elif last == 'end':
            del self._data[first:]
        else:
            del self._data[first:last+1]

    def insert(self, index, *elements):
        if elements:
            if index == 'end':
                index = self.size()
            super().insert(index, *elements)
            self._data[index:index] = elements

    def replace(self, data):
        super().delete(0, 'end')
        super().insert(0, *data)
        self._data = data

    def setCurrent(self, event):
        self.curIndex = event.widget.nearest(event.y)

    def shiftSelection(self, event):
        if self.curIndex is None:
            return "break"
        i = event.widget.nearest(event.y)
        if i == self.curIndex:
            return "break"
        item = self._data[i]
        self.delete(i)
        self.insert(i + (1 if i < self.curIndex else -1), item)
        self.curIndex = i
        return "break"

    def moveTop(self):
        sels = self.curselection()
        if not sels:
            return
        if sels:
            insert_pos = 0
            items = [self.get(sel) for sel in sels]
            for sel in reversed(sels):
                self.delete(sel)
            self.insert(insert_pos, *items)
            self.selection_set(insert_pos, insert_pos + len(sels) - 1)

    def moveBottom(self):
        sels = self.curselection()
        if not sels:
            return
        if sels:
            insert_pos = self.size() - len(sels)
            items = [self.get(sel) for sel in sels]
            for sel in reversed(sels):
                self.delete(sel)
            self.insert(insert_pos, *items)
            self.selection_set(insert_pos, insert_pos + len(sels) - 1)

    def onKeyUp(self, event=None):
        if event is None:
            sels = self.curselection()
        else:
            sels = event.widget.curselection()
        if sels:
            insert_pos = max(0, min(sels) - 1)
            items = [self.get(sel) for sel in sels]
            for sel in reversed(sels):
                self.delete(sel)
            self.insert(insert_pos, *items)
            self.selection_set(insert_pos, insert_pos + len(sels) - 1)
        return "break"

    def onKeyDown(self, event=None):
        if event is None:
            sels = self.curselection()
        else:
            sels = event.widget.curselection()
        if sels:
            insert_pos = min(self.size() - len(sels), min(sels) + 1)
            items = [self.get(sel) for sel in sels]
            for sel in reversed(sels):
                self.delete(sel)
            self.insert(insert_pos, *items)
            self.selection_set(insert_pos, insert_pos + len(items) - 1)
        return "break"

    def onKeyBackSpace(self, event=None):
        if event is None:
            sels = self.curselection()
        else:
            sels = event.widget.curselection()
        if sels:
            for sel in reversed(sels):
                self.delete(sel)


class MultiListbox(tkinter.Frame):

    def __init__(self, master, header_list, data=None, **kwds):
        super().__init__(master)
        self._listbox_list = []
        self._listbox_dict = {}
        for header in header_list:
            kwargs = kwds.copy()
            frame = tkinter.Frame(self)
            frame.pack(side='left', expand='yes', fill='both')
            if isinstance(header, str):
                label = header
                tkinter.Label(frame, text=label, borderwidth=1, relief='raised').pack(fill='x')
            else:
                label, *rest = header
                if rest:
                    kwargs['width'] = rest[0]
                tk_label = tkinter.Label(frame, text=label, borderwidth=1, relief='raised')
                tk_label.pack(fill='x')
                if len(rest) >= 2:
                    Tooltip(tk_label, text=rest[1])
            lb = tkinter.Listbox(frame, **kwargs)
            lb.pack(expand='yes', fill='both')
            lb.bind("<Button-1>", self.setCurrent)
            lb.bind("<ButtonRelease-1>", self.onButton1Release)
            lb.bind("<B1-Motion>", self.shiftSelection)
            lb.bind('<MouseWheel>', self.onMouseWheel)
            lb.bind("<Up>", self.onKeyUp)
            lb.bind("<Down>", self.onKeyDown)
            lb.bind("<BackSpace>", self.onKeyBackSpace)
            #lb.bind("<Leave>", lambda e: "break")
            lb.bind("<B2-Motion>", lambda e, _f=self._b2motion: _f(e.x, e.y))
            lb.bind("<Button-2>", lambda e, _f=self._button2: _f(e.x, e.y))
            self._listbox_list.append(lb)
            self._listbox_dict[label] = lb
        frame = tkinter.Frame(self)
        frame.pack(side='left', fill='y')
        tkinter.Label(frame, borderwidth=1, relief='raised').pack(fill='x')
        sb = tkinter.Scrollbar(frame, orient='vertical', command=self._scroll)
        sb.pack(side='left', fill='y')
        if data is None:
            self._data = []
        else:
            self._data = data
            for lb, vals in zip(self._listbox_list, zip(*data)):
                lb.insert(0, *vals)
        self._listbox_list[0]["yscrollcommand"] = sb.set
        self.curIndex = None

    @property
    def listboxes(self) -> Mapping[str, tkinter.Listbox]:
        return MappingProxyType(self._listbox_dict)

    def setCurrent(self, event):
        self.curIndex = event.widget.nearest(event.y)

    def onButton1Release(self, event):
        sels = event.widget.curselection()
        self.selection_clear(0, 'end')
        for sel in sels:
            self.selection_set(sel)
        return "break"

    def shiftSelection(self, event):
        if self.curIndex is None:
            return "break"
        i = event.widget.nearest(event.y)
        if i == self.curIndex:
            return "break"
        item = self._data[i]
        self.delete(i)
        self.insert(i + (1 if i < self.curIndex else - 1), item)
        self.curIndex = i
        self._select(i)
        return "break"

    def onMouseWheel(self, event):
        delta = event.delta
        for lb in self._listbox_list:
            lb.yview("scroll", delta, "units")
        return "break"

    def onKeyUp(self, event=None):
        if event is None:
            sels = self.curselection()
        else:
            sels = event.widget.curselection()
        if sels:
            insert_pos = max(0, min(sels) - 1)
            items = [self.get(sel) for sel in sels]
            for sel in reversed(sels):
                self.delete(sel)
            self.insert(insert_pos, *items)
            self.selection_set(insert_pos, insert_pos + len(sels) - 1)
        return "break"

    def onKeyDown(self, event=None):
        if event is None:
            sels = self.curselection()
        else:
            sels = event.widget.curselection()
        if sels:
            insert_pos = min(self.size() - len(sels), min(sels) + 1)
            items = [self.get(sel) for sel in sels]
            for sel in reversed(sels):
                self.delete(sel)
            self.insert(insert_pos, *items)
            self.selection_set(insert_pos, insert_pos + len(items) - 1)
        return "break"

    def onKeyBackSpace(self, event=None):
        if event is None:
            sels = self.curselection()
        else:
            sels = event.widget.curselection()
        if sels:
            for sel in reversed(sels):
                self.delete(sel)

    def _button2(self, x, y):
        for l in self._listbox_list:
            l.scan_mark(x,y)
        return "break"

    def _b2motion(self, x, y):
        for l in self._listbox_list:
            l.scan_dragto(x, y)
        return "break"

    def _scroll(self, *args):
        for l in self._listbox_list:
            l.yview(*args)
        return "break"

    def _select(self, *idx):
        self.selection_clear(0, 'end')
        for row in idx:
            self.selection_set(row)

    def bind(self, sequence=None, func=None, add=None):
        for lb in self._listbox_list:
            lb.bind(sequence, func, add)

    def curselection(self):
        return self._listbox_list[0].curselection()

    def _delete(self, first, last=None):
        for lb in self._listbox_list:
            lb.delete(first, last)

    def delete(self, first, last=None):
        self._delete(first, last)
        if last is None:
            del self._data[first]
        elif last == 'end':
            del self._data[first:]
        else:
            del self._data[first:last+1]

    def get(self, first, last=None):
        if last is None:
            return self._data[first]
        elif last == 'end':
            return self._data[first:]
        else:
            return self._data[first:last+1]

    def index(self, index):
        return self._listbox_list[0].index(index)

    def _insert(self, index, elements):
        if index == 'end':
            index = self.size()
        for lb, vals in zip(self._listbox_list, zip(*elements)):
            lb.insert(index, *vals)

    def insert(self, index, *elements):
        if elements:
            self._insert(index, elements)
            self._data[index:index] = elements

    def replace(self, data):
        self._delete(0, 'end')
        self._insert(0, *data)
        self._data = data

    def size(self):
        return self._listbox_list[0].size()

    def see(self, index):
        for lb in self._listbox_list:
            lb.see(index)

    def selection_anchor(self, index):
        for lb in self._listbox_list:
            lb.selection_anchor(index)

    select_anchor = selection_anchor

    def selection_clear(self, first, last=None):
        for lb in self._listbox_list:
            lb.selection_clear(first, last)

    select_clear = selection_clear

    def selection_includes(self, index):
        return self._listbox_list[0].seleciton_includes(index)

    select_includes = selection_includes

    def selection_set(self, first, last=None):
        for l in self._listbox_list:
            l.selection_set(first, last)

    select_set = selection_set


# Fork from [python - How to display tool tips in Tkinter?](https://try2explore.com/questions/10367355)
class Tooltip(object):
    'Create a tooltip for a given widget.'
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     # miliseconds
        self.wraplength = 180   # pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = tkinter.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tkinter.Label(
            self.tw, text=self.text, justify='left',
            background="#ffffff", relief='solid', borderwidth=1,
            wraplength = self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

