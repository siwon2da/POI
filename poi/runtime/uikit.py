# -*- coding: utf-8 -*-
"""uikit — POI 전용 GUI 라이브러리 (명령형, tkinter 위).

선언형 `app { window { } }` 와 달리 자유롭게 조립한다. 사진 편집기·에디터 같은
동적 UI 를 위한 것. import 없이 `uikit` 으로 바로.

    win = uikit.window("제목", 900, 600)
    bar = uikit.row(win)
    uikit.button(bar, "열기", on_open)
    s = uikit.slider(bar, 0, 100, on_change)
    cv = uikit.canvas(win, 800, 500)
    uikit.run(win)

상태:  st = uikit.state({ v: 0 });  st.v = 3   (uikit.watch(st, fn) 로 변화 감지)
"""
from __future__ import annotations

from types import SimpleNamespace

from .boxes import Box

_PAL = {  # 라이트 기본
    "bg": "#ffffff", "panel": "#f2f4f6", "ink": "#191f28", "ink2": "#4e5968",
    "line": "#e5e8eb", "accent": "#3182f6", "accent_ink": "#ffffff",
}


def _tk():
    import tkinter as tk
    from tkinter import filedialog, colorchooser, messagebox
    return tk, filedialog, colorchooser, messagebox


def window(title="POI", w=880, h=560, resizable=True):
    tk, *_ = _tk()
    root = tk.Tk()
    root.title(title)
    root.geometry(f"{w}x{h}")
    root.configure(bg=_PAL["bg"])
    if not resizable:
        root.resizable(False, False)
    root._poi_pal = dict(_PAL)
    return root


def _pack(w, side="top", fill="x", expand=False, pad=6):
    w.pack(side=side, fill=fill, expand=expand, padx=pad, pady=pad)
    return w


def row(parent, pad=0):
    tk, *_ = _tk()
    f = tk.Frame(parent, bg=_PAL["panel"])
    return _pack(f, side="top", fill="x", pad=pad)


def column(parent, pad=0, side="left"):
    tk, *_ = _tk()
    f = tk.Frame(parent, bg=_PAL["bg"])
    return _pack(f, side=side, fill="both", expand=True, pad=pad)


def label(parent, text="", size=10, muted=False):
    tk, *_ = _tk()
    lb = tk.Label(parent, text=text, bg=parent.cget("bg"),
                  fg=_PAL["ink2"] if muted else _PAL["ink"],
                  font=("Segoe UI", size))
    return _pack(lb, side="left")


def button(parent, text, on_click=None, primary=False):
    tk, *_ = _tk()
    b = tk.Button(parent, text=text, relief="flat", cursor="hand2",
                  font=("Segoe UI", 10), padx=12, pady=6, borderwidth=0,
                  bg=_PAL["accent"] if primary else _PAL["line"],
                  fg=_PAL["accent_ink"] if primary else _PAL["ink"],
                  command=(on_click or (lambda: None)))
    return _pack(b, side="left", pad=4)


def entry(parent, value="", width=24, on_enter=None):
    tk, *_ = _tk()
    e = tk.Entry(parent, font=("Segoe UI", 10), width=width, relief="flat",
                 bg="#ffffff", highlightthickness=1,
                 highlightbackground=_PAL["line"])
    e.insert(0, value)
    if on_enter:
        e.bind("<Return>", lambda _ev: on_enter(e.get()))
    return _pack(e, side="left", pad=4)


def slider(parent, lo=0, hi=100, on_change=None, value=None, length=180,
           label_text=None):
    tk, *_ = _tk()
    box = tk.Frame(parent, bg=parent.cget("bg"))
    if label_text:
        tk.Label(box, text=label_text, bg=box.cget("bg"), fg=_PAL["ink2"],
                 font=("Segoe UI", 9)).pack(side="top", anchor="w")
    var = tk.DoubleVar(value=(hi + lo) / 2 if value is None else value)
    sc = tk.Scale(box, from_=lo, to=hi, orient="horizontal", variable=var,
                  length=length, showvalue=True, bg=box.cget("bg"),
                  highlightthickness=0, troughcolor=_PAL["line"],
                  command=(lambda _v: on_change(var.get())) if on_change else None)
    sc.pack(side="top")
    box._poi_var = var
    _pack(box, side="left", pad=4)
    return box


def canvas(parent, w=760, h=460, bg="#111417"):
    tk, *_ = _tk()
    cv = tk.Canvas(parent, width=w, height=h, bg=bg, highlightthickness=0)
    return _pack(cv, side="top", fill="both", expand=True)


def listbox(parent, items=None, on_select=None, height=10):
    tk, *_ = _tk()
    lb = tk.Listbox(parent, font=("Segoe UI", 10), height=height,
                    relief="flat", highlightthickness=1,
                    highlightbackground=_PAL["line"], activestyle="none")
    for it in (items or []):
        lb.insert("end", it)
    if on_select:
        lb.bind("<<ListboxSelect>>",
                lambda _ev: on_select(lb.get(lb.curselection()[0])
                                      if lb.curselection() else None))
    return _pack(lb, side="left", fill="y")


def text_area(parent, value="", h=12):
    tk, *_ = _tk()
    t = tk.Text(parent, font=("Consolas", 11), height=h, relief="flat",
                highlightthickness=1, highlightbackground=_PAL["line"], wrap="word")
    if value:
        t.insert("1.0", value)
    return _pack(t, side="top", fill="both", expand=True)


def statusbar(win, text=""):
    tk, *_ = _tk()
    s = tk.Label(win, text=text, bg=_PAL["panel"], fg=_PAL["ink2"], anchor="w",
                 font=("Segoe UI", 9))
    s.pack(side="bottom", fill="x")
    return s


def set_text(widget, text):
    try:
        widget.config(text=str(text))
    except Exception:
        pass


def menu(win, tree):
    """tree = { "파일": [("열기", fn), ("저장", fn), None, ("끝", fn)], ... }"""
    tk, *_ = _tk()
    mb = tk.Menu(win)
    for name, items in dict(tree).items():
        m = tk.Menu(mb, tearoff=False)
        for it in items:
            if it is None:
                m.add_separator()
            else:
                m.add_command(label=it[0], command=it[1])
        mb.add_cascade(label=name, menu=m)
    win.config(menu=mb)
    return mb


def ask_open(title="열기", types=None):
    _tk_, fd, *_ = _tk()
    return fd.askopenfilename(title=title,
                              filetypes=types or [["모든 파일", "*.*"]]) or ""


def ask_save(title="저장", ext="", types=None):
    _tk_, fd, *_ = _tk()
    return fd.asksaveasfilename(title=title, defaultextension=ext,
                               filetypes=types or [["모든 파일", "*.*"]]) or ""


def ask_color(initial="#3182f6"):
    _tk_, _fd, cc, _mb = _tk()
    r = cc.askcolor(color=initial)
    return r[1] if r and r[1] else ""


def alert(msg, title="알림"):
    *_ , mb = _tk()
    mb.showinfo(title, str(msg))


def confirm(msg, title="확인"):
    *_ , mb = _tk()
    return bool(mb.askokcancel(title, str(msg)))


def every(win, ms, fn):
    def tick():
        try:
            fn()
        finally:
            win.after(int(ms), tick)
    win.after(int(ms), tick)


def on(widget, event, fn):
    widget.bind(event, lambda _ev: fn())


def run(win):
    win.mainloop()


def close(win):
    try:
        win.destroy()
    except Exception:
        pass


# ── 반응형 상태 ─────────────────────────────────────────────────────

class State(Box):
    def __init__(self, initial=None):
        super().__init__(initial or {})
        object.__setattr__(self, "_watchers", [])

    def __setattr__(self, k, v):
        super().__setattr__(k, v)
        for w in getattr(self, "_watchers", []):
            try:
                w(self)
            except Exception:
                pass

    __setitem__ = __setattr__


def state(initial=None):
    return State(dict(initial) if initial else {})


def watch(st, fn):
    getattr(st, "_watchers").append(fn)
    return st


uikit = SimpleNamespace(
    window=window, row=row, column=column, label=label, button=button,
    entry=entry, slider=slider, canvas=canvas, listbox=listbox,
    text=text_area, statusbar=statusbar, set_text=set_text, menu=menu,
    ask_open=ask_open, ask_save=ask_save, ask_color=ask_color,
    alert=alert, confirm=confirm, every=every, on=on, run=run, close=close,
    state=state, watch=watch, palette=_PAL,
)
