"""POI AST -> 파이썬 소스.

emit() 로 파이썬 소스를 한 줄씩 쌓으면서, 파이썬 줄번호 -> POI 줄번호
매핑(linemap)을 같이 만든다. 실행 중 오류가 나면 이 매핑으로 POI 줄을 찾는다.
"""
from __future__ import annotations

import re
import textwrap

from .errors import POIError

_STD_MODULES = {"file", "json", "web", "math", "time", "ui", "gui"}


class Transpiler:
    def __init__(self, compiled_name: str = "<poi>", source: str = "",
                 trace: bool = False):
        self.compiled_name = compiled_name
        self.src_lines = source.splitlines()
        self.trace = trace
        self.lines: list[str] = []
        self.linemap: dict[int, int] = {}
        self.ind = 0
        self._hcount = 0
        self._gui_states: set[str] = set()

    def _src_at(self, line: int) -> str:
        if 0 < line <= len(self.src_lines):
            return self.src_lines[line - 1].strip()
        return ""

    # -- emit --------------------------------------------------
    def emit(self, text: str, line: int = 0):
        for piece in text.split("\n"):
            self.lines.append("    " * self.ind + piece if piece else "")
            self.linemap[len(self.lines)] = line

    def generate(self, program):
        for stmt in program.body:
            self.stmt(stmt)
        if not self.lines:
            self.emit("pass")
        return "\n".join(self.lines) + "\n", self.linemap

    # -- statements ------------------------------------------
    def block(self, body):
        if not body:
            self.emit("pass")
            return
        self.ind += 1
        for s in body:
            self.stmt(s)
        self.ind -= 1

    _NO_TRACE = {"PyBlock", "FnDecl", "App", "GWindow", "GText", "GButton",
                 "GRow", "GColumn", "GCard", "GInput", "GState", "GOn"}

    def stmt(self, n):
        k = n.kind
        if self.trace and n.line and k not in self._NO_TRACE:
            self.emit(f"_poi_trace({n.line}, {self._src_at(n.line)!r}, locals())", n.line)
        if k == "Show":
            self.emit(f"poi_show({self.ex(n.value)})", n.line)
        elif k == "ExprStmt":
            self.emit(self.ex(n.value), n.line)
        elif k == "Assign":
            self._assign(n)
        elif k == "FnDecl":
            self._fn(n)
        elif k == "Return":
            self.emit("return" if n.value is None else f"return {self.ex(n.value)}", n.line)
        elif k == "If":
            self._if(n)
        elif k == "Repeat":
            var = n.var or "_i"
            self.emit(f"for {var} in range(int({self.ex(n.count)})):", n.line)
            self.block(n.body)
        elif k == "ForIn":
            self.emit(f"for {n.var} in {self.ex(n.iterable)}:", n.line)
            self.block(n.body)
        elif k == "TryCatch":
            self._try(n)
        elif k == "Use":
            self._use(n)
        elif k == "PyBlock":
            self._pyblock(n)
        elif k == "App":
            self._app(n)
        elif k in ("GWindow", "GText", "GButton", "GRow", "GColumn", "GCard",
                   "GInput", "GState", "GOn"):
            self.gui_emit(n)
        else:
            raise POIError(f"아직 지원하지 않는 문장입니다: {k}", "P020", n.line)

    def _assign(self, n):
        t = n.target
        if t.kind == "Name":
            self.emit(f"{t.id} = {self.ex(n.value)}", n.line)
        elif t.kind == "Member":
            self.emit(f'poi_setattr({self.ex(t.obj)}, "{t.name}", {self.ex(n.value)})',
                      n.line)
        elif t.kind == "Index":
            self.emit(f"{self.ex(t.obj)}[{self.ex(t.index)}] = {self.ex(n.value)}", n.line)

    def _fn(self, n):
        params = []
        for pname, default in n.params:
            params.append(pname if default is None else f"{pname}={self.ex(default)}")
        self.emit(f"def {n.name}({', '.join(params)}):", n.line)
        if n.is_expr_body:
            self.ind += 1
            self.emit(f"return {self.ex(n.body)}", n.line)
            self.ind -= 1
        else:
            self.block(n.body)

    def _if(self, n):
        for idx, (cond, body) in enumerate(n.branches):
            kw = "if" if idx == 0 else "elif"
            self.emit(f"{kw} {self.ex(cond)}:", cond.line or n.line)
            self.block(body)
        if n.orelse is not None:
            self.emit("else:", n.line)
            self.block(n.orelse)

    def _try(self, n):
        self.emit("try:", n.line)
        self.block(n.body)
        var = n.name or "_err"
        self.emit(f"except Exception as {var}:", n.line)
        if n.name:
            self.ind += 1
            self.emit(f"{var} = poi_error_value({var})", n.line)
            self.ind -= 1
        self.block(n.handler)

    def _use(self, n):
        if n.use_kind == "py":
            self.emit(f"import {n.target}" + (f" as {n.alias}" if n.alias else ""), n.line)
        elif n.use_kind == "pyfile":
            self.emit(f"{n.alias} = poi_import_pyfile({n.target!r})", n.line)
        else:
            if n.target not in _STD_MODULES:
                raise POIError(
                    f"'{n.target}' 이라는 표준 모듈은 없습니다.", "P021", n.line,
                    hint="쓸 수 있는 것: " + ", ".join(sorted(_STD_MODULES)) +
                         "\n파이썬 라이브러리는 'use py:이름' 으로 불러오세요.")
            alias = n.alias or n.target
            self.emit(f"{alias} = poi_std({n.target!r})", n.line)

    def _pyblock(self, n):
        for raw_line in textwrap.dedent(n.raw).strip("\n").split("\n"):
            self.emit(raw_line, n.line)

    # -- GUI -------------------------------------------------
    def _app(self, n):
        self._gui_states = set()
        self.emit(f"_app = poi_app({self.str_lit(n.title)})", n.line)
        self.emit("app = _app", n.line)
        for child in n.body:
            self.gui_emit(child)
        self.emit("_app.run()", n.line)

    def gui_emit(self, n):
        k = n.kind
        if k == "GWindow":
            kw = ", ".join(f"{key}={self.ex(v)}" for key, v in n.props.items())
            self.emit(f"poi_window(_app, {kw})" if kw else "poi_window(_app)", n.line)
        elif k == "GText":
            self.emit(f"poi_text(_app, {self.ex(n.value)}, heading={n.heading})", n.line)
        elif k == "GButton":
            h = f"_handler{self._next_h()}"
            self.emit(f"def {h}():", n.line)
            self.ind += 1
            if n.body:
                for s in n.body:
                    self.gui_emit(s) if s.kind.startswith("G") else self.stmt(s)
            else:
                self.emit("pass", n.line)
            self.ind -= 1
            self.emit(f"poi_button(_app, {self.ex(n.label)}, {h})", n.line)
        elif k in ("GRow", "GColumn", "GCard"):
            fn = {"GRow": "poi_row", "GColumn": "poi_column", "GCard": "poi_card"}[k]
            self.emit(f"with {fn}(_app):", n.line)
            self.ind += 1
            body = n.body or []
            if body:
                for s in body:
                    self.gui_emit(s) if s.kind.startswith("G") else self.stmt(s)
            else:
                self.emit("pass", n.line)
            self.ind -= 1
        elif k == "GInput":
            if n.bind and n.bind not in self._gui_states:
                self.emit(f'{n.bind} = ""', n.line)
                self._gui_states.add(n.bind)
            cb = (f"lambda _v: globals().__setitem__({n.bind!r}, _v)"
                  if n.bind else "None")
            self.emit(
                f"poi_input(_app, {self.ex(n.label)}, {cb}, secret={n.secret})", n.line)
        elif k == "GState":
            self._gui_states.add(n.name)
            self.emit(f"{n.name} = {self.ex(n.value)}", n.line)
        elif k == "GOn":
            h = f"_on_{re.sub(r'[^0-9A-Za-z_]', '_', n.event)}_{self._next_h()}"
            self.emit(f"def {h}():", n.line)
            self.block_gui(n.body)
            self.emit(f"poi_on(_app, {n.event!r}, {h})", n.line)
        elif k == "If":
            for idx, (cond, body) in enumerate(n.branches):
                self.emit(f"{'if' if idx == 0 else 'elif'} {self.ex(cond)}:", n.line)
                self.block_gui(body)
            if n.orelse is not None:
                self.emit("else:", n.line)
                self.block_gui(n.orelse)
        elif k == "ForIn":
            self.emit(f"for {n.var} in {self.ex(n.iterable)}:", n.line)
            self.block_gui(n.body)
        else:
            self.stmt(n)

    def block_gui(self, body):
        if not body:
            self.emit("pass")
            return
        self.ind += 1
        for s in body:
            self.gui_emit(s) if s.kind.startswith("G") or s.kind in ("If", "ForIn") \
                else self.stmt(s)
        self.ind -= 1

    def _next_h(self):
        self._hcount += 1
        return self._hcount

    # -- expressions --------------------------------------
    def ex(self, n) -> str:
        k = n.kind
        if k == "Num":
            return repr(n.value)
        if k == "Str":
            return self.str_lit(n.value)
        if k == "Bool":
            return "True" if n.value else "False"
        if k == "Null":
            return "None"
        if k == "Name":
            return n.id
        if k == "Member":
            fn = "poi_getattr_safe" if n.safe else "poi_getattr"
            return f'{fn}({self.ex(n.obj)}, "{n.name}")'
        if k == "Index":
            return f"{self.ex(n.obj)}[{self.ex(n.index)}]"
        if k == "Call":
            parts = [self.ex(a) for a in n.args]
            parts += [f"{key}={self.ex(v)}" for key, v in n.kwargs]
            return f"{self.ex(n.func)}({', '.join(parts)})"
        if k == "BinOp":
            return f"({self.ex(n.left)} {n.op} {self.ex(n.right)})"
        if k == "UnaryOp":
            if n.op == "not":
                return f"(not {self.ex(n.operand)})"
            return f"({n.op}{self.ex(n.operand)})"
        if k == "BoolOp":
            joiner = f" {n.op} "
            return "(" + joiner.join(self.ex(v) for v in n.values) + ")"
        if k == "Compare":
            pieces = []
            prev = self.ex(n.left)
            for op, c in zip(n.ops, n.comparators):
                r = self.ex(c)
                pieces.append(f"({prev} {op} {r})")
                prev = r
            return "(" + " and ".join(pieces) + ")"
        if k == "Between":
            return f"({self.ex(n.low)} <= {self.ex(n.value)} <= {self.ex(n.high)})"
        if k == "Is":
            op = "!=" if n.negated else "=="
            return f"({self.ex(n.left)} {op} {self.ex(n.right)})"
        if k == "Ternary":
            return f"({self.ex(n.body)} if {self.ex(n.cond)} else {self.ex(n.alt)})"
        if k == "Coalesce":
            return (f"poi_coalesce(lambda: {self.ex(n.left)}, "
                    f"lambda: {self.ex(n.right)})")
        if k == "ArrayLit":
            return "[" + ", ".join(self.ex(e) for e in n.elements) + "]"
        if k == "ObjectLit":
            body = ", ".join(f"{key!r}: {self.ex(v)}" for key, v in n.pairs)
            return "Box({" + body + "})"
        if k == "Ask":
            return f"poi_ask({self.ex(n.prompt)})"
        raise POIError(f"아직 지원하지 않는 표현식입니다: {k}", "P022", n.line)

    # -- 문자열 리터럴 + 보간 -------------------------------------
    def str_lit(self, v: str) -> str:
        parts = _split_interp(v)
        # 보간 조각이 하나도 없으면 평범한 문자열
        if all(kind == "lit" for kind, _ in parts):
            return _raw_str(v, prefix="")

        out = []
        any_expr = False
        for kind, txt in parts:
            if kind == "lit":
                out.append(_escape_fstring_literal(txt))
                continue
            code = self._compile_interp(txt)
            if code is None:
                # POI 표현식으로 안 읽히면 (JSON 등) 그냥 글자로 둔다
                out.append(_escape_fstring_literal("{" + txt + "}"))
            else:
                any_expr = True
                out.append("{poi_fmt(" + code + ")}")
        if not any_expr:
            return _raw_str(v, prefix="")
        return 'f"""' + "".join(out) + '"""'

    def _compile_interp(self, fragment: str):
        from .lexer import Lexer
        from .parser import Parser
        try:
            toks = Lexer(fragment, "<interp>").tokenize()
            p = Parser(toks, fragment, "<interp>")
            node = p.expression()
        except POIError:
            return None
        # 조각을 전부 소비했는지 (JSON `{"a": 1}` 같은 건 여기서 걸러짐)
        if p.peek().type not in ("EOF", "NEWLINE"):
            return None
        if node.kind == "ObjectLit":
            return None
        try:
            return self.ex(node)
        except POIError:
            return None


def _split_interp(v: str):
    parts = []
    buf = []
    i = 0
    n = len(v)
    while i < n:
        two = v[i:i + 2]
        if two == "{{":
            buf.append("{")
            i += 2
            continue
        if two == "}}":
            buf.append("}")
            i += 2
            continue
        if v[i] == "{":
            j = v.find("}", i + 1)
            if j == -1:
                buf.append("{")
                i += 1
                continue
            parts.append(("lit", "".join(buf)))
            buf = []
            parts.append(("expr", v[i + 1:j]))
            i = j + 1
            continue
        buf.append(v[i])
        i += 1
    parts.append(("lit", "".join(buf)))
    return parts


def _escape_fstring_literal(txt: str) -> str:
    # 사용자가 쓴 \n \t 같은 이스케이프는 그대로 살린다.
    txt = txt.replace('"""', '\\"\\"\\"').replace("{", "{{").replace("}", "}}")
    if txt.endswith("\\") and not txt.endswith("\\\\"):
        txt += "\\"
    return txt


def _raw_str(v: str, prefix: str) -> str:
    if "\n" in v or '"' in v:
        body = v.replace('"""', '\\"\\"\\"')
        if body.endswith('"'):
            body += " "
        return f'{prefix}"""{body}"""'
    return f'{prefix}"{v}"'
