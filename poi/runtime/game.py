# -*- coding: utf-8 -*-
"""game — POI 2D 게임 (v1.9.9).  tkinter Canvas 기반, 외부 의존 0.

    win = game.window("POI Jump", 800, 500)
    바닥 = game.sprite(win, { x: 0, y: 460, w: 800, h: 40, color: "#233" })
    p    = game.sprite(win, { x: 100, y: 300, w: 40, h: 40, color: "#5b9dff" })
    game.on_key(win, "space", () => p.jump(14))
    game.on_key(win, "Left",  () => p.move(-6, 0))
    game.on_key(win, "Right", () => p.move(6, 0))
    game.every_frame(win, (dt) => {
        p.vy = p.vy + 0.6                 # 중력
        p.move(0, p.vy)
        if game.hits(p, 바닥) { p.y = 420; p.vy = 0 }
    })
    game.run(win)
"""
from __future__ import annotations

from types import SimpleNamespace

from .boxes import Box


def _tk():
    import tkinter as tk
    from tkinter import font as tkfont
    return tk, tkfont


class Sprite:
    __slots__ = ("_c", "_id", "x", "y", "w", "h", "vx", "vy", "color", "tag",
                 "alive", "kind", "_txt")

    def __init__(self, canvas, o):
        self._c = canvas
        self.x = float(o.get("x", 0)); self.y = float(o.get("y", 0))
        self.w = float(o.get("w", 32)); self.h = float(o.get("h", 32))
        self.vx = float(o.get("vx", 0)); self.vy = float(o.get("vy", 0))
        self.color = o.get("color", "#5b9dff")
        self.tag = o.get("tag", "")
        self.kind = o.get("kind", "rect")
        self.alive = True
        self._txt = o.get("text", "")
        if self._txt:
            self._id = canvas.create_text(self.x, self.y, text=self._txt,
                                          fill=self.color, anchor="nw",
                                          font=("Segoe UI", int(self.h)))
        elif self.kind == "circle":
            self._id = canvas.create_oval(self.x, self.y, self.x + self.w,
                                          self.y + self.h, fill=self.color, width=0)
        else:
            self._id = canvas.create_rectangle(self.x, self.y, self.x + self.w,
                                               self.y + self.h, fill=self.color, width=0)

    def _draw(self):
        if self._txt:
            self._c.coords(self._id, self.x, self.y)
            self._c.itemconfig(self._id, text=self._txt, fill=self.color)
        else:
            self._c.coords(self._id, self.x, self.y, self.x + self.w, self.y + self.h)
            self._c.itemconfig(self._id, fill=self.color)

    def move(self, dx=0, dy=0):
        self.x += float(dx); self.y += float(dy); self._draw(); return self

    def to(self, x=None, y=None):
        if x is not None: self.x = float(x)
        if y is not None: self.y = float(y)
        self._draw(); return self

    def jump(self, power=12):
        self.vy = -abs(float(power)); return self

    def set(self, **kw):
        for k, v in kw.items():
            if k == "text":
                self._txt = str(v)
            elif hasattr(self, k):
                setattr(self, k, v)
        self._draw(); return self

    def remove(self):
        self.alive = False
        try:
            self._c.delete(self._id)
        except Exception:
            pass

    @property
    def cx(self): return self.x + self.w / 2

    @property
    def cy(self): return self.y + self.h / 2


class GameWin:
    def __init__(self, title, w, h, bg):
        tk, _f = _tk()
        self.root = tk.Tk()
        self.root.title(title)
        self.root.resizable(False, False)
        self.W, self.H = int(w), int(h)
        self.canvas = tk.Canvas(self.root, width=w, height=h, bg=bg,
                                highlightthickness=0)
        self.canvas.pack()
        self.sprites = []
        self._keys = set()
        self._keymap = {}       # keysym -> [fn,...]  (한 번 누름)
        self._hold = {}         # keysym -> [fn,...]  (누르고 있는 동안 매 프레임)
        self._frame_fns = []
        self._running = False
        self._score = Box({"value": 0})
        self.root.bind("<KeyPress>", self._on_press)
        self.root.bind("<KeyRelease>", self._on_release)

    def _norm(self, k):
        return {" ": "space", "space": "space"}.get(k, k)

    def _on_press(self, e):
        k = self._norm(e.keysym)
        if k not in self._keys:
            for fn in self._keymap.get(k, []):
                try: fn()
                except Exception: pass
        self._keys.add(k)

    def _on_release(self, e):
        self._keys.discard(self._norm(e.keysym))

    def key_down(self, k):
        return self._norm(k) in self._keys


def window(title="POI Game", w=800, h=500, bg="#0b0e14"):
    return GameWin(title, w, h, bg)


def sprite(win, opts=None):
    s = Sprite(win.canvas, dict(opts or {}))
    win.sprites.append(s)
    return s


def text(win, s, opts=None):
    o = dict(opts or {}); o["text"] = str(s); o.setdefault("h", 18)
    o.setdefault("color", "#e6e9ef")
    sp = Sprite(win.canvas, o)
    win.sprites.append(sp)
    return sp


def on_key(win, key, fn):
    win._keymap.setdefault(win._norm(key), []).append(fn)
    return win


def on_hold(win, key, fn):
    win._hold.setdefault(win._norm(key), []).append(fn)
    return win


def every_frame(win, fn):
    win._frame_fns.append(fn)
    return win


def hits(a, b):
    if not (getattr(a, "alive", True) and getattr(b, "alive", True)):
        return False
    return (a.x < b.x + b.w and a.x + a.w > b.x and
            a.y < b.y + b.h and a.y + a.h > b.y)


def out_of_bounds(win, s, margin=0):
    return (s.x + s.w < -margin or s.x > win.W + margin or
            s.y + s.h < -margin or s.y > win.H + margin)


def score(win, add=None):
    if add is not None:
        win._score["value"] += add
    return win._score["value"]


def close(win):
    win._running = False
    try:
        win.root.destroy()
    except Exception:
        pass


def run(win, fps=60):
    win._running = True
    dt_ms = max(8, int(1000 / max(1, fps)))

    def loop():
        if not win._running:
            return
        for k in list(win._keys):
            for fn in win._hold.get(k, []):
                try: fn()
                except Exception: pass
        for fn in list(win._frame_fns):
            try: fn(dt_ms / 1000.0)
            except Exception: pass
        win.sprites[:] = [s for s in win.sprites if getattr(s, "alive", True)]
        win.root.after(dt_ms, loop)

    win.root.after(dt_ms, loop)
    win.root.mainloop()


game = SimpleNamespace(
    window=window, sprite=sprite, text=text, on_key=on_key, on_hold=on_hold,
    every_frame=every_frame, hits=hits, collide=hits, out_of_bounds=out_of_bounds,
    score=score, close=close, run=run, key_down=lambda w, k: w.key_down(k),
)
