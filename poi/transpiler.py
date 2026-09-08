"""POI AST -> 파이썬 소스.

emit() 로 파이썬 소스를 한 줄씩 쌓으면서, 파이썬 줄번호 -> POI 줄번호
매핑(linemap)을 같이 만든다. 실행 중 오류가 나면 이 매핑으로 POI 줄을 찾는다.
"""
from __future__ import annotations

import re
import textwrap

from .errors import POIError

_STD_MODULES = {"file", "json", "web", "math", "time", "ui", "gui",
                "regex", "csv", "datetime", "random", "stats", "env", "shell",
                # v1.7 — 백엔드 · 보안 · 시스템
                "crypto", "password", "jwt", "path", "url", "html", "compress",
                "log", "cache", "bench", "dotenv", "system", "uuid",
                # v1.10 — AI
                "ai",
                # 한국어 별칭
                "암호", "비밀번호", "토큰", "경로", "주소", "압축", "기록",
                "캐시", "성능측정", "시스템"}


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
        self._const: set[str] = set()
        self._has_export = False
        self._loop_depth = 0

    def _src_at(self, line: int) -> str:
        if 0 < line <= len(self.src_lines):
            return self.src_lines[line - 1].strip()
        return ""

    # -- emit --------------------------------------------------
    def emit(self, text: str, line: int = 0):
        for piece in text.split("\n"):
            self.lines.append("    " * self.ind + piece if piece else "")
            self.linemap[len(self.lines)] = line

    _has_web = False

    def generate(self, program):
        body_start = len(self.lines)
        for stmt in program.body:
            self.stmt(stmt)
        if self._has_export:
            self.lines.insert(body_start, "__poi_exports__ = set()")
            self.linemap = {(k + 1 if k > body_start else k): v
                            for k, v in self.linemap.items()}
        if self._has_web:
            self.emit("__poi_has_web__ = True")
        if not self.lines:
            self.emit("pass")
        return "\n".join(self.lines) + "\n", self.linemap

    # -- statements ------------------------------------------
    def block(self, body):
        self.ind += 1
        if not body:
            self.emit("pass")
        else:
            for s in body:
                self.stmt(s)
        self.ind -= 1

    _NO_TRACE = {"PyBlock", "FnDecl", "App", "GWindow", "GText", "GButton",
                 "GRow", "GColumn", "GCard", "GInput", "GState", "GOn", "TestBlock"}

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
        elif k == "Destructure":
            self._destructure(n)
        elif k == "FnDecl":
            self._fn(n)
        elif k == "Return":
            self.emit("return" if n.value is None else f"return {self.ex(n.value)}", n.line)
        elif k == "If":
            self._if(n)
        elif k == "Repeat":
            var = n.var or "_i"
            self.emit(f"for {var} in range(int({self.ex(n.count)})):", n.line)
            self._loop_depth += 1
            self.block(n.body)
            self._loop_depth -= 1
        elif k == "ForIn":
            self.emit(f"for {n.var} in {self.ex(n.iterable)}:", n.line)
            self._loop_depth += 1
            self.block(n.body)
            self._loop_depth -= 1
        elif k == "While":
            self.emit(f"while {self.ex(n.cond)}:", n.line)
            self._loop_depth += 1
            self.block(n.body)
            self._loop_depth -= 1
        elif k == "Break":
            if self._loop_depth <= 0:
                raise POIError("break 는 반복문(repeat/for/while) 안에서만 쓸 수 있어요.",
                               "P018", n.line)
            self.emit("break", n.line)
        elif k == "Continue":
            if self._loop_depth <= 0:
                raise POIError("continue 는 반복문 안에서만 쓸 수 있어요.", "P018", n.line)
            self.emit("continue", n.line)
        elif k == "Export":
            self._has_export = True
            self.stmt(n.decl)
            for nm in n.names:
                self.emit(f"__poi_exports__.add({nm!r})", n.line)
        elif k == "TryCatch":
            self._try(n)
        elif k == "Use":
            self._use(n)
        elif k == "Raise":
            self.emit(f"raise poi_make_error({self.ex(n.value)})", n.line)
        elif k == "Assert":
            self.emit(f"poi_assert({self.ex(n.test)}, {n.src!r})", n.line)
        elif k == "TestBlock":
            self._testblock(n)
        elif k == "Match":
            self._match(n)
        elif k == "PyBlock":
            self._pyblock(n)
        elif k == "App":
            self._app(n)
        elif k == "Server":
            self._server(n)
        elif k == "WebApp":
            self._webapp(n)
        elif k in ("GWindow", "GText", "GButton", "GRow", "GColumn", "GCard",
                   "GInput", "GState", "GOn"):
            self.gui_emit(n)
        else:
            raise POIError(f"아직 지원하지 않는 문장입니다: {k}", "P020", n.line)

    def _assign(self, n):
        t = n.target
        if t.kind == "Name":
            if getattr(n, "is_const", False):
                self._const.add(t.id)
            elif t.id in self._const:
                raise POIError(
                    f"'{t.id}' 은(는) 상수(const)라서 다시 대입할 수 없어요.", "P019",
                    n.line, hint="값을 바꿔야 한다면 const 를 빼고 선언하세요.")
            self.emit(f"{t.id} = {self.ex(n.value)}", n.line)
        elif t.kind == "Member":
            self.emit(f'poi_setattr({self.ex(t.obj)}, "{t.name}", {self.ex(n.value)})',
                      n.line)
        elif t.kind == "Index":
            self.emit(f"{self.ex(t.obj)}[{self.ex(t.index)}] = {self.ex(n.value)}", n.line)

    def _destructure(self, n):
        tmp = f"_poi_de{self._next_h()}"
        self.emit(f"{tmp} = {self.ex(n.value)}", n.line)
        for nm in self._const_guard(n.names, n.line):
            pass
        if n.mode == "obj":
            for nm in n.names:
                self.emit(f'{nm} = poi_getattr({tmp}, "{nm}")', n.line)
        else:
            self.emit(f"{tmp} = list({tmp})", n.line)
            for i, nm in enumerate(n.names):
                self.emit(f"{nm} = {tmp}[{i}]", n.line)

    def _const_guard(self, names, line):
        for nm in names:
            if nm in self._const:
                raise POIError(
                    f"'{nm}' 은(는) 상수(const)라서 다시 대입할 수 없어요.", "P019",
                    line)
        return names

    def _fn(self, n):
        params = []
        for p in n.params:
            pname, default = p[0], p[1]
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
        et = getattr(n, "err_type", None)
        raw = f"_e{self._next_h()}"
        self.emit(f"except Exception as {raw}:", n.line)
        self.ind += 1
        if et:
            self.emit(f"if not poi_error_is({raw}, {et!r}): raise", n.line)
        if n.name:
            self.emit(f"{n.name} = poi_error_value({raw})", n.line)
        self.ind -= 1
        self.block(n.handler)

    def _use(self, n):
        if n.use_kind == "py":
            self.emit(f"import {n.target}" + (f" as {n.alias}" if n.alias else ""), n.line)
        elif n.use_kind == "pyfile":
            self.emit(f"{n.alias} = poi_import_pyfile({n.target!r})", n.line)
        elif n.use_kind == "poimod":
            self.emit(f"{n.alias} = poi_import_module({n.target!r})", n.line)
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

    def _testblock(self, n):
        h = f"_poi_test_{self._next_h()}"
        self.emit(f"def {h}():", n.line)
        self.block(n.body)
        self.emit(f"poi_register_test({n.name!r}, {h})", n.line)

    def _match(self, n):
        mv = f"_poi_m{self._next_h()}"
        self.emit(f"{mv} = {self.ex(n.subject)}", n.line)
        first = True
        for pats, body in n.clauses:
            cond = " or ".join(self._pat_cond(mv, p) for p in pats)
            self.emit(f"{'if' if first else 'elif'} {cond}:", n.line)
            self.block(body)
            first = False
        if n.default is not None:
            if first:
                self.emit("if True:", n.line)
            else:
                self.emit("else:", n.line)
            self.block(n.default)
        elif first:
            self.emit("pass", n.line)

    def _pat_cond(self, mv: str, p) -> str:
        if p.kind == "PatCompare":
            return f"({mv} {p.op} {self.ex(p.value)})"
        if p.kind == "PatRange":
            return f"({self.ex(p.low)} <= {mv} <= {self.ex(p.high)})"
        return f"({mv} == {self.ex(p.value)})"

    # -- WEB (v1.6) -----------------------------------------
    _HANDLER_SIG = "(params, query, body, headers, method)"

    def _server(self, n):
        self._has_web = True
        rd = f"_routes{self._next_h()}"
        self.emit(f"{rd} = {{}}", n.line)
        for method, path, body in n.routes:
            if method == "__setup__":
                for s in body:
                    self.stmt(s)
                continue
            h = f"_route{self._next_h()}"
            self.emit(f"def {h}{self._HANDLER_SIG}:", n.line)
            self.block(body)
            self.emit(f"{rd}[({method!r}, {path!r})] = {h}", n.line)
        statics = ", ".join(repr(s) for s in n.statics)
        self.emit(f"poi_web_register({{'routes': {rd}, 'static': [{statics}]}})", n.line)

    def _webapp(self, n):
        self._has_web = True
        rd = f"_routes{self._next_h()}"
        self.emit(f"{rd} = {{}}", n.line)
        for nm, val in n.states:
            self.emit(f"{nm} = {self.ex(val)}", n.line)
        for path, nodes in n.pages:
            h = f"_page{self._next_h()}"
            self.emit(f"def {h}{self._HANDLER_SIG}:", n.line)
            self.ind += 1
            self.emit(f"return poi_render_page({self._web_list(nodes)}, "
                      f"{n.title!r})", n.line)
            self.ind -= 1
            self.emit(f"{rd}[('GET', {path!r})] = {h}", n.line)
        action_paths = []
        for path, body in n.actions:
            h = f"_act{self._next_h()}"
            self.emit(f"def {h}{self._HANDLER_SIG}:", n.line)
            self.ind += 1
            self.emit("globals().update(dict(body))", n.line)
            self.ind -= 1
            self.block(body)
            if path == "__setup__":
                continue
            self.ind += 1
            self.emit("return poi_web_redirect(headers.get('Referer', '/'))", n.line)
            self.ind -= 1
            self.emit(f"{rd}[('POST', {path!r})] = {h}", n.line)
            action_paths.append(path)
        self.emit(f"poi_web_register({{'routes': {rd}, 'static': [], "
                  f"'title': {n.title!r}, 'csrf_paths': {action_paths!r}}})", n.line)

    def _web_list(self, nodes) -> str:
        parts = []
        for nd in nodes:
            k = nd.kind
            if k == "ForIn" and getattr(nd, "web", False):
                parts.append(f"*[_wn for {nd.var} in {self.ex(nd.iterable)} "
                             f"for _wn in {self._web_list(nd.body)}]")
            elif k == "If" and getattr(nd, "web", False):
                cond, body = nd.branches[0]
                els = self._web_list(nd.orelse) if nd.orelse else "[]"
                parts.append(f"*({self._web_list(body)} if {self.ex(cond)} else {els})")
            elif k.startswith("W"):
                parts.append(self._web_one(nd))
            # 그밖의 문장은 페이지 안에서 무시 (부작용용은 action 에서)
        return "[" + ", ".join(parts) + "]"

    def _web_one(self, nd) -> str:
        k = nd.kind
        if k == "WKind":
            t = nd.kind_[1:]  # 'title','heading','badge','divider','spacer','image',...
            if nd.value is None:
                return f"{{'t': {t!r}}}"
            key = "px" if t == "spacer" else ("src" if t == "image" else "text")
            return f"{{'t': {t!r}, {key!r}: {self.ex(nd.value)}}}"
        if k == "WField":
            opts = f", 'options': {self.ex(nd.opts)}" if nd.opts is not None else ""
            return (f"{{'t': {nd.ftype!r}, 'label': {self.ex(nd.label)}, "
                    f"'name': {nd.name!r}{opts}}}")
        if k == "WTitle":
            return f"{{'t': 'title', 'text': {self.ex(nd.value)}}}"
        if k == "WText":
            return f"{{'t': 'text', 'text': {self.ex(nd.value)}}}"
        if k == "WLink":
            return (f"{{'t': 'link', 'text': {self.ex(nd.text)}, "
                    f"'href': {self.ex(nd.href)}}}")
        if k in ("WCard", "WRow", "WCol"):
            tt = {"WCard": "card", "WRow": "row", "WCol": "col"}[k]
            return f"{{'t': {tt!r}, 'kids': {self._web_list(nd.body)}}}"
        if k == "WForm":
            return (f"{{'t': 'form', 'action': {nd.action!r}, "
                    f"'kids': {self._web_list(nd.body)}}}")
        if k == "WInput":
            return (f"{{'t': 'input', 'label': {self.ex(nd.label)}, "
                    f"'name': {nd.name!r}, 'secret': {nd.secret}, "
                    f"'multiline': {nd.multiline}}}")
        if k == "WButton":
            return f"{{'t': 'button', 'text': {self.ex(nd.value)}}}"
        if k == "WHtml":
            return f"poi_html_raw({self.ex(nd.value)})"
        return "{'t': 'text', 'text': ''}"

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
        self.ind += 1
        if not body:
            self.emit("pass")
        else:
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
        if k == "Lambda":
            params = ", ".join(n.params)
            return f"(lambda {params}: {self.ex(n.body)})"
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
        if k == "Range":
            return (f"poi_range({self.ex(n.lo)}, {self.ex(n.hi)}, "
                    f"{bool(n.inclusive)})")
        if k == "MatchExpr":
            return self._match_expr_ex(n)
        raise POIError(f"아직 지원하지 않는 표현식입니다: {k}", "P022", n.line)

    def _match_expr_ex(self, n) -> str:
        m = f"__ms{self._next_h()}"

        def cond(p):
            if p.kind == "PatCompare":
                return f"({m} {p.op} {self.ex(p.value)})"
            if p.kind == "PatRange":
                return f"({self.ex(p.low)} <= {m} <= {self.ex(p.high)})"
            return f"({m} == {self.ex(p.value)})"

        expr = self.ex(n.default) if n.default is not None else "None"
        for pats, val in reversed(n.clauses):
            c = " or ".join(cond(p) for p in pats)
            expr = f"({self.ex(val)} if ({c}) else {expr})"
        return f"(lambda {m}: {expr})({self.ex(n.subject)})"

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
        # `{3}` `{4}` 같은 순수 리터럴은 정규식 수량자 등 — 보간이 아니다
        if node.kind in ("ObjectLit", "Num", "Str", "Bool", "Null"):
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


_POI_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\",
                '"': '"', "'": "'", "0": "\0", "b": "\b", "f": "\f"}


def _poi_unescape(v: str) -> str:
    """POI 문자열의 이스케이프를 실제 문자로. 모르는 \\x 는 백슬래시 그대로."""
    out = []
    i = 0
    while i < len(v):
        c = v[i]
        if c == "\\" and i + 1 < len(v):
            nx = v[i + 1]
            if nx in _POI_ESCAPES:
                out.append(_POI_ESCAPES[nx])
                i += 2
                continue
            out.append("\\")  # 알 수 없는 이스케이프(\d 등) → 백슬래시 유지
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _escape_fstring_literal(txt: str) -> str:
    s = _poi_unescape(txt)
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    s = s.replace("{", "{{").replace("}", "}}")
    return s


def _raw_str(v: str, prefix: str) -> str:
    # repr 이 항상 유효한 파이썬 리터럴을 만든다 (SyntaxWarning 없음).
    return prefix + repr(_poi_unescape(v))
