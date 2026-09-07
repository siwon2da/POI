"""선언형 GUI 를 tkinter 로 구현.

트랜스파일러는 app 블록을 아래 함수들의 호출로 바꾼다:
    _app = poi_app("제목")
    poi_window(_app, size="500x300")
    poi_text(_app, "안녕")
    poi_button(_app, "눌러", 핸들러)
    with poi_column(_app): ...
    _app.run()
"""
from __future__ import annotations

import contextlib

from ..errors import POIError

_PALETTE = {"bg": "#f7f8fa", "fg": "#1b1f24", "accent": "#2b6cb0"}


class App:
    def __init__(self, title="POI"):
        try:
            import tkinter as tk
        except Exception as e:  # noqa: BLE001
            raise POIError(f"tkinter 를 불러올 수 없습니다: {e}", "P200",
                           hint="파이썬에 tkinter 가 설치돼 있어야 GUI 를 쓸 수 있어요.")
        try:
            self._tk = tk
            self.root = tk.Tk()
        except tk.TclError as e:
            raise POIError(f"화면(디스플레이)을 열 수 없습니다: {e}", "P201",
                           hint="GUI 앱은 데스크톱 환경에서 실행하세요.")
        self.root.title(title)
        self.root.configure(bg=_PALETTE["bg"])
        self.root.minsize(240, 160)
        self._stack = [self.root]

    @property
    def parent(self):
        return self._stack[-1]

    def _side(self):
        return getattr(self.parent, "_poi_side", "top")

    def close(self):
        with contextlib.suppress(Exception):
            self.root.destroy()

    def run(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.close()


def poi_app(title="POI"):
    return App(title)


def poi_window(app, title=None, size=None, center=False, resizable=None, **_ignored):
    if title:
        app.root.title(title)
    if size:
        app.root.geometry(str(size).replace(" ", ""))
    if resizable is not None:
        app.root.resizable(bool(resizable), bool(resizable))
    if center:
        app.root.update_idletasks()
        w = app.root.winfo_width() or 480
        h = app.root.winfo_height() or 320
        sw = app.root.winfo_screenwidth()
        sh = app.root.winfo_screenheight()
        app.root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")


def _pack(widget, side):
    if side == "left":
        widget.pack(side="left", padx=6, pady=6)
    else:
        widget.pack(side="top", fill="x", padx=10, pady=5)


def poi_text(app, value, heading=False):
    tk = app._tk
    lbl = tk.Label(app.parent, text=str(value), bg=_PALETTE["bg"], fg=_PALETTE["fg"],
                   anchor="w", justify="left",
                   font=("Segoe UI", 16, "bold") if heading else ("Segoe UI", 11))
    _pack(lbl, app._side())
    return lbl


def poi_button(app, label, handler):
    tk = app._tk
    btn = tk.Button(app.parent, text=str(label), command=handler,
                    font=("Segoe UI", 11), relief="flat",
                    bg=_PALETTE["accent"], fg="white", activebackground="#1f4f9e",
                    padx=12, pady=6, cursor="hand2")
    _pack(btn, app._side())
    return btn


def poi_input(app, label, on_change=None, secret=False):
    tk = app._tk
    frame = tk.Frame(app.parent, bg=_PALETTE["bg"])
    tk.Label(frame, text=str(label), bg=_PALETTE["bg"], fg=_PALETTE["fg"],
             font=("Segoe UI", 10)).pack(anchor="w")
    var = tk.StringVar()
    entry = tk.Entry(frame, textvariable=var, show="*" if secret else "",
                     font=("Segoe UI", 11))
    entry.pack(fill="x", pady=(2, 0))
    if on_change:
        var.trace_add("write", lambda *_a: on_change(var.get()))
    _pack(frame, app._side())
    return var


@contextlib.contextmanager
def _container(app, relief=None, side="top"):
    tk = app._tk
    kw = {"bg": _PALETTE["bg"]}
    if relief:
        kw.update(relief=relief, borderwidth=1, padx=10, pady=10)
    frame = tk.Frame(app.parent, **kw)
    frame._poi_side = side
    _pack(frame, app._side())
    app._stack.append(frame)
    try:
        yield frame
    finally:
        app._stack.pop()


def poi_row(app):
    return _container(app, side="left")


def poi_column(app):
    return _container(app, side="top")


def poi_card(app):
    return _container(app, relief="groove", side="top")


def poi_on(app, event, handler):
    ev = str(event).lower()
    if ev in ("start", "load", "ready", "open"):
        app.root.after(0, lambda: handler())
    elif ev in ("close", "exit", "quit"):
        app.root.protocol("WM_DELETE_WINDOW", lambda: (handler(), app.close()))
    elif ev.startswith("key "):
        key = event.split(" ", 1)[1].strip()
        app.root.bind(f"<{key}>", lambda _e: handler())
    else:
        app.root.bind(f"<{event}>", lambda _e: handler())
