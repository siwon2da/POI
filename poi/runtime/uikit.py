# -*- coding: utf-8 -*-
"""uikit — POI 전용 GUI 라이브러리 (명령형, tkinter 위).

tkinter 를 그대로 쓰면 매번 색·폰트·pack 옵션·이벤트 바인딩 보일러플레이트가 붙는다.
uikit 은 그걸 다 없앤다:
  · 통일된 라이트/다크 테마 (uikit.theme("dark"))
  · 위젯 한 줄 생성 + 자동 배치
  · 반응형 상태  st = uikit.state({v:0});  st.v = 3  →  watcher 자동 호출
  · grid·tabs·select·checkbox·radio·progress·image·scroll·tree·dialog·tooltip

    win = uikit.window("제목", 900, 600)
    bar = uikit.row(win)
    uikit.button(bar, "열기", on_open, true)
    s = uikit.slider(bar, 0, 100, on_change)
    cv = uikit.canvas(win, 800, 500)
    uikit.run(win)
"""
from __future__ import annotations

from types import SimpleNamespace

from .boxes import Box

_LIGHT = {
    "bg": "#ffffff", "panel": "#f2f4f6", "ink": "#191f28", "ink2": "#4e5968",
    "line": "#e5e8eb", "accent": "#3182f6", "accent_ink": "#ffffff",
    "field": "#ffffff", "sel": "#d7e6ff",
}
_DARK = {
    "bg": "#15181e", "panel": "#1e222a", "ink": "#e6e9ef", "ink2": "#a9aeb8",
    "line": "#2b2f38", "accent": "#4b93f8", "accent_ink": "#ffffff",
    "field": "#1a1e25", "sel": "#2a3b57",
}
_PAL = dict(_LIGHT)
UIFONT = ("Segoe UI", 10)


def theme(name="light"):
    """전역 테마 전환. 이후 만드는 위젯에 적용된다."""
    _PAL.clear()
    _PAL.update(_DARK if str(name).lower() == "dark" else _LIGHT)
    return dict(_PAL)


def _tk():
    import tkinter as tk
    from tkinter import filedialog, colorchooser, messagebox, ttk
    return tk, filedialog, colorchooser, messagebox, ttk


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
    _tk_, _fd, cc, _mb, _tt = _tk()
    r = cc.askcolor(color=initial)
    return r[1] if r and r[1] else ""


def alert(msg, title="알림"):
    _t, _f, _c, mb, _tt = _tk()
    mb.showinfo(title, str(msg))


def confirm(msg, title="확인"):
    _t, _f, _c, mb, _tt = _tk()
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


def bind_key(win, key, fn):
    win.bind(f"<{key}>", lambda _ev: fn())


def title(win, text):
    win.title(str(text))


# ── 더 많은 위젯 ──────────────────────────────────────────────────

def grid(parent, cols=2, gap=6):
    """열 개수를 고정한 그리드 컨테이너. uikit.cell 로 칸을 채운다."""
    tk, *_ = _tk()
    f = tk.Frame(parent, bg=parent.cget("bg"))
    for c in range(cols):
        f.grid_columnconfigure(c, weight=1)
    f._poi_cols = cols
    f._poi_i = 0
    f._poi_gap = gap
    return _pack(f, side="top", fill="both", expand=True)


def cell(gridf, widget=None):
    i = gridf._poi_i
    gridf._poi_i += 1
    r, c = divmod(i, gridf._poi_cols)
    if widget is not None:
        widget.grid(row=r, column=c, padx=gridf._poi_gap, pady=gridf._poi_gap,
                    sticky="nsew")
    return (r, c)


def tabs(parent, names):
    """names 리스트 → 탭. 각 탭의 내용 프레임 리스트를 돌려준다."""
    _t, _f, _c, _m, ttk = _tk()
    nb = ttk.Notebook(parent)
    frames = []
    for nm in names:
        fr = _t.Frame(nb, bg=_PAL["bg"])
        nb.add(fr, text=str(nm))
        frames.append(fr)
    _pack(nb, side="top", fill="both", expand=True)
    return frames


def checkbox(parent, text, checked=False, on_toggle=None):
    tk, *_ = _tk()
    var = tk.BooleanVar(value=bool(checked))
    cb = tk.Checkbutton(parent, text=text, variable=var, bg=parent.cget("bg"),
                        fg=_PAL["ink"], activebackground=parent.cget("bg"),
                        selectcolor=_PAL["field"], font=("Segoe UI", 10),
                        command=(lambda: on_toggle(var.get())) if on_toggle else None)
    cb._poi_var = var
    return _pack(cb, side="left", pad=4)


def radio(parent, options, value=None, on_change=None):
    tk, *_ = _tk()
    var = tk.StringVar(value=value if value is not None else (options[0] if options else ""))
    box = tk.Frame(parent, bg=parent.cget("bg"))
    for opt in options:
        tk.Radiobutton(box, text=str(opt), value=str(opt), variable=var,
                       bg=box.cget("bg"), fg=_PAL["ink"], font=("Segoe UI", 10),
                       activebackground=box.cget("bg"), selectcolor=_PAL["field"],
                       command=(lambda: on_change(var.get())) if on_change else None
                       ).pack(side="left")
    box._poi_var = var
    return _pack(box, side="left", pad=4)


def select(parent, options, value=None, on_change=None, width=18):
    _t, _f, _c, _m, ttk = _tk()
    box = _t.Frame(parent, bg=parent.cget("bg"))
    var = _t.StringVar(value=value if value is not None else (options[0] if options else ""))
    cb = ttk.Combobox(box, textvariable=var, values=list(options), width=width,
                      state="readonly")
    cb.pack(side="left")
    if on_change:
        cb.bind("<<ComboboxSelected>>", lambda _e: on_change(var.get()))
    box._poi_var = var
    return _pack(box, side="left", pad=4)


def progress(parent, value=0, maximum=100):
    _t, _f, _c, _m, ttk = _tk()
    pb = ttk.Progressbar(parent, maximum=maximum, value=value, length=220)
    return _pack(pb, side="top", pad=6)


def image(parent, path=None, w=None, h=None):
    """이미지 뷰. path 주면 바로 로드. .set(path) 로 교체."""
    tk, *_ = _tk()
    lb = tk.Label(parent, bg=parent.cget("bg"))

    def _set(p):
        try:
            from PIL import Image as _I, ImageTk as _IT
            im = _I.open(p)
            if w or h:
                im.thumbnail((w or 10000, h or 10000))
            lb._poi_img = _IT.PhotoImage(im)
        except Exception:
            lb._poi_img = tk.PhotoImage(file=p)
        lb.config(image=lb._poi_img)
    lb.set = _set
    if path:
        _set(path)
    return _pack(lb, side="top")


def scroll(parent, h=300):
    """세로 스크롤 되는 프레임. 안쪽 프레임을 돌려준다."""
    tk, *_ = _tk()
    outer = tk.Frame(parent, bg=parent.cget("bg"))
    cv = tk.Canvas(outer, bg=_PAL["bg"], highlightthickness=0, height=h)
    sb = tk.Scrollbar(outer, orient="vertical", command=cv.yview)
    inner = tk.Frame(cv, bg=_PAL["bg"])
    inner.bind("<Configure>",
               lambda _e: cv.configure(scrollregion=cv.bbox("all")))
    cv.create_window((0, 0), window=inner, anchor="nw")
    cv.configure(yscrollcommand=sb.set)
    cv.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    _pack(outer, side="top", fill="both", expand=True)
    return inner


def tree(parent, columns, rows=None, on_select=None, height=12):
    """표(treeview). columns=["이름","나이"], rows=[["시원","16"], ...]."""
    _t, _f, _c, _m, ttk = _tk()
    tv = ttk.Treeview(parent, columns=list(columns), show="headings",
                      height=height)
    for c in columns:
        tv.heading(c, text=str(c))
        tv.column(c, width=120)
    for r in (rows or []):
        tv.insert("", "end", values=list(r))
    if on_select:
        tv.bind("<<TreeviewSelect>>",
                lambda _e: on_select(tv.item(tv.selection()[0])["values"]
                                     if tv.selection() else None))
    _pack(tv, side="top", fill="both", expand=True)
    return tv


def dialog(parent, title_text="", w=360, h=220):
    """모달 창. 내용 프레임을 돌려준다. uikit.close 로 닫는다."""
    tk, *_ = _tk()
    top = tk.Toplevel(parent)
    top.title(str(title_text))
    top.geometry(f"{w}x{h}")
    top.configure(bg=_PAL["bg"])
    top.transient(parent)
    top.grab_set()
    return top


def tooltip(widget, text):
    tk, *_ = _tk()
    tip = {"w": None}

    def enter(_e):
        if tip["w"]:
            return
        x = widget.winfo_rootx() + 12
        y = widget.winfo_rooty() + widget.winfo_height() + 4
        t = tk.Toplevel(widget)
        t.wm_overrideredirect(True)
        t.wm_geometry(f"+{x}+{y}")
        tk.Label(t, text=str(text), bg="#191f28", fg="#ffffff",
                 font=("Segoe UI", 9), padx=8, pady=3).pack()
        tip["w"] = t

    def leave(_e):
        if tip["w"]:
            tip["w"].destroy()
            tip["w"] = None
    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)


def value(widget, v=None):
    """위젯 값 읽기/쓰기 (slider·checkbox·radio·select·entry)."""
    var = getattr(widget, "_poi_var", None)
    if var is None and hasattr(widget, "get"):     # Entry
        if v is None:
            return widget.get()
        widget.delete(0, "end")
        widget.insert(0, str(v))
        return v
    if var is None:
        return None
    if v is None:
        return var.get()
    var.set(v)
    return v


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

    def _fire(self):
        for w in list(object.__getattribute__(self, "_watchers")):
            try:
                w(self)
            except Exception:
                pass

    def __setattr__(self, k, v):
        dict.__setitem__(self, k, v)
        self._fire()

    def __setitem__(self, k, v):
        dict.__setitem__(self, k, v)
        self._fire()


def state(initial=None):
    return State(dict(initial) if initial else {})


def watch(st, fn):
    getattr(st, "_watchers").append(fn)
    return st


# ── 전문화 (v1.13): 데이터 바인딩 · 폼 · 토스트 · 차트 · 카드 · 분할 ──

def bind(widget, st, field):
    """위젯 ↔ 상태 양방향 바인딩.  st[field] 가 바뀌면 위젯도, 위젯이 바뀌면 st 도."""
    var = getattr(widget, "_poi_var", None)
    if var is None and widget.__class__.__name__ == "Entry":
        tk, *_ = _tk()
        var = tk.StringVar(value=widget.get())
        widget.config(textvariable=var)
        widget._poi_var = var
    guard = {"on": False}

    def to_state(*_a):
        if guard["on"]:
            return
        guard["on"] = True
        try:
            st[field] = var.get() if var is not None else widget.get()
        finally:
            guard["on"] = False

    def to_widget(_s=None):
        if guard["on"]:
            return
        guard["on"] = True
        try:
            v = st.get(field)
            if var is not None:
                var.set(v)
            elif hasattr(widget, "delete"):
                widget.delete(0, "end")
                widget.insert(0, "" if v is None else str(v))
        finally:
            guard["on"] = False

    if var is not None:
        try:
            var.trace_add("write", to_state)
        except Exception:
            var.trace("w", to_state)
    else:
        widget.bind("<KeyRelease>", to_state, add="+")
    if field in st:
        to_widget()
    else:
        to_state()
    if hasattr(st, "_watchers"):
        getattr(st, "_watchers").append(to_widget)
    return widget


def card(parent, title_text=""):
    """제목 있는 테두리 프레임.  안쪽 프레임을 돌려준다 (여기에 위젯을 넣는다)."""
    tk, *_ = _tk()
    outer = tk.Frame(parent, bg=_PAL["panel"], highlightthickness=1,
                     highlightbackground=_PAL["line"])
    _pack(outer, fill="both", expand=False, pad=8)
    if title_text:
        tk.Label(outer, text=title_text, bg=_PAL["panel"], fg=_PAL["ink2"],
                 font=(UIFONT[0], 9, "bold"), anchor="w").pack(
            fill="x", padx=12, pady=(10, 2))
    inner = tk.Frame(outer, bg=_PAL["panel"])
    inner.pack(fill="both", expand=True, padx=12, pady=(2, 12))
    return inner


def split(parent, orient="h"):
    """드래그로 크기 조절되는 분할 패널.  .add(자식) 으로 칸을 채운다."""
    _t, _f, _c, _m, ttk = _tk()
    p = ttk.PanedWindow(parent,
                        orient="horizontal" if str(orient).startswith("h") else "vertical")
    _pack(p, fill="both", expand=True)
    return p


def toast(win, msg, kind="info", ms=2600):
    """화면 아래쪽에 잠깐 뜨는 알림."""
    tk, *_ = _tk()
    colors = {"info": _PAL["accent"], "ok": "#12b886", "warn": "#f59f00",
              "error": "#e03131"}
    bg = colors.get(str(kind), _PAL["accent"])
    lab = tk.Label(win, text="  " + str(msg) + "  ", bg=bg, fg="#ffffff",
                   font=(UIFONT[0], 10, "bold"), padx=14, pady=9)
    lab.place(relx=0.5, rely=1.0, anchor="s", y=-24)
    lab.lift()

    def die():
        try:
            lab.destroy()
        except Exception:
            pass
    win.after(int(ms), die)
    return lab


def chart(parent, kind="bar", data=None, w=440, h=240, title_text=""):
    """막대/선 차트 (Canvas).  data = [값,...]  또는  [[라벨, 값], ...]."""
    tk, *_ = _tk()
    rows = list(data or [])
    pairs = []
    for i, d in enumerate(rows):
        if isinstance(d, (list, tuple)) and len(d) >= 2:
            pairs.append((str(d[0]), float(d[1])))
        else:
            pairs.append((str(i + 1), float(d)))
    cv = tk.Canvas(parent, width=w, height=h, bg=_PAL["bg"],
                   highlightthickness=1, highlightbackground=_PAL["line"])
    _pack(cv, fill="x", expand=False)
    if not pairs:
        return cv
    pad_l, pad_b, pad_t, pad_r = 44, 26, 24 if title_text else 12, 14
    plot_w = w - pad_l - pad_r
    plot_h = h - pad_b - pad_t
    vmax = max(v for _, v in pairs) or 1.0
    vmin = min(0.0, min(v for _, v in pairs))
    span = (vmax - vmin) or 1.0
    if title_text:
        cv.create_text(pad_l, 12, text=title_text, anchor="w",
                       fill=_PAL["ink2"], font=(UIFONT[0], 9, "bold"))
    # 축
    cv.create_line(pad_l, pad_t, pad_l, h - pad_b, fill=_PAL["line"])
    cv.create_line(pad_l, h - pad_b, w - pad_r, h - pad_b, fill=_PAL["line"])
    for frac in (0.0, 0.5, 1.0):
        yv = vmin + span * frac
        y = h - pad_b - frac * plot_h
        cv.create_text(pad_l - 6, y, text=("%g" % round(yv, 2)), anchor="e",
                       fill=_PAL["ink2"], font=(UIFONT[0], 8))
        cv.create_line(pad_l, y, w - pad_r, y, fill=_PAL["line"], dash=(2, 3))
    n = len(pairs)
    acc = _PAL["accent"]
    if str(kind) == "line":
        pts = []
        for i, (lab, v) in enumerate(pairs):
            x = pad_l + (plot_w * (i / (n - 1)) if n > 1 else plot_w / 2)
            y = h - pad_b - ((v - vmin) / span) * plot_h
            pts.append((x, y))
        for a, b in zip(pts, pts[1:]):
            cv.create_line(*a, *b, fill=acc, width=2)
        for (x, y) in pts:
            cv.create_oval(x - 3, y - 3, x + 3, y + 3, fill=acc, outline="")
        for i, (lab, _v) in enumerate(pairs):
            cv.create_text(pts[i][0], h - pad_b + 12, text=lab,
                           fill=_PAL["ink2"], font=(UIFONT[0], 8))
    else:
        gap = plot_w / n
        bw = gap * 0.6
        for i, (lab, v) in enumerate(pairs):
            x0 = pad_l + i * gap + (gap - bw) / 2
            y0 = h - pad_b - ((v - vmin) / span) * plot_h
            cv.create_rectangle(x0, y0, x0 + bw, h - pad_b, fill=acc, outline="")
            cv.create_text(x0 + bw / 2, h - pad_b + 12, text=lab,
                           fill=_PAL["ink2"], font=(UIFONT[0], 8))
    return cv


def form(parent, fields, on_submit=None, submit_text="확인"):
    """필드 정의로 라벨+입력 폼을 만든다.
    fields = [{name, label?, type?("text"|"password"|"number"|"check"|"select"),
               options?, required?, value?}]
    돌려주는 Box: .values() .get(name) .set(name,v) .errors() .valid()"""
    tk, _fd, _cc, _mb, ttk = _tk()
    wrap = tk.Frame(parent, bg=_PAL["bg"])
    _pack(wrap, fill="x", expand=False)
    widgets = {}
    specs = {}
    for f in fields:
        name = f["name"]
        specs[name] = f
        r = tk.Frame(wrap, bg=_PAL["bg"])
        r.pack(fill="x", pady=4)
        tk.Label(r, text=f.get("label", name), bg=_PAL["bg"], fg=_PAL["ink2"],
                 width=12, anchor="w", font=UIFONT).pack(side="left")
        ftype = f.get("type", "text")
        if ftype == "check":
            var = tk.BooleanVar(value=bool(f.get("value", False)))
            cb = tk.Checkbutton(r, variable=var, bg=_PAL["bg"],
                                activebackground=_PAL["bg"], selectcolor=_PAL["field"])
            cb.pack(side="left")
            cb._poi_var = var
            widgets[name] = cb
        elif ftype == "select":
            var = tk.StringVar(value=f.get("value", (f.get("options") or [""])[0]))
            om = ttk.Combobox(r, textvariable=var, values=list(f.get("options") or []),
                              state="readonly", font=UIFONT)
            om.pack(side="left", fill="x", expand=True)
            om._poi_var = var
            widgets[name] = om
        else:
            e = tk.Entry(r, font=UIFONT, bg=_PAL["field"], fg=_PAL["ink"],
                         relief="flat", show="•" if ftype == "password" else "")
            e.insert(0, str(f.get("value", "")))
            e.pack(side="left", fill="x", expand=True, ipady=4)
            widgets[name] = e

    def _get(name):
        w = widgets[name]
        var = getattr(w, "_poi_var", None)
        raw = var.get() if var is not None else w.get()
        if specs[name].get("type") == "number":
            try:
                return float(raw) if raw not in ("", None) else None
            except ValueError:
                return None
        return raw

    def _set(name, v):
        w = widgets[name]
        var = getattr(w, "_poi_var", None)
        if var is not None:
            var.set(v)
        else:
            w.delete(0, "end")
            w.insert(0, "" if v is None else str(v))

    def _errors():
        errs = {}
        for name, sp in specs.items():
            v = _get(name)
            if sp.get("required") and (v in ("", None, False)):
                errs[name] = (sp.get("label", name) + " 은(는) 필수입니다.")
            if sp.get("type") == "number" and v is None \
                    and (widgets[name].get() if hasattr(widgets[name], "get") else "") != "":
                errs[name] = (sp.get("label", name) + " 은(는) 숫자여야 합니다.")
        return Box(errs)

    def _values():
        return Box({n: _get(n) for n in specs})

    api = Box({
        "get": _get, "set": _set, "values": _values, "errors": _errors,
        "valid": lambda: len(_errors()) == 0, "widgets": widgets,
    })

    def _do_submit():
        errs = _errors()
        if errs:
            _mb.showwarning("확인", "\n".join(errs.values()))
            return
        if on_submit:
            on_submit(_values())

    if on_submit:
        btn = tk.Button(wrap, text=submit_text, command=_do_submit,
                        bg=_PAL["accent"], fg=_PAL["accent_ink"], relief="flat",
                        font=(UIFONT[0], 10, "bold"), padx=16, pady=7, cursor="hand2")
        btn.pack(anchor="e", pady=(8, 2))
        api["submit"] = _do_submit
    return api


uikit = SimpleNamespace(
    theme=theme, window=window, title=title, row=row, column=column,
    label=label, button=button, entry=entry, slider=slider, canvas=canvas,
    listbox=listbox, text=text_area, statusbar=statusbar, set_text=set_text,
    menu=menu, grid=grid, cell=cell, tabs=tabs, checkbox=checkbox, radio=radio,
    select=select, progress=progress, image=image, scroll=scroll, tree=tree,
    dialog=dialog, tooltip=tooltip, value=value,
    ask_open=ask_open, ask_save=ask_save, ask_color=ask_color,
    alert=alert, confirm=confirm, every=every, on=on, bind_key=bind_key,
    run=run, close=close, state=state, watch=watch, palette=_PAL,
    # v1.13 — 전문화
    bind=bind, form=form, toast=toast, chart=chart, card=card, split=split,
)
