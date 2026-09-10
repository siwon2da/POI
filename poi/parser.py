"""POI 파서 (재귀 하강).

토큰 스트림 -> POI AST(Node).
"""
from __future__ import annotations

from .ast_nodes import Node
from .errors import POIError

_COMPARE_OPS = {"==", "!=", "<", ">", "<=", ">="}
_ADD_OPS = {"+", "-"}
_MUL_OPS = {"*", "/", "%"}
_GUI_WORDS = {"window", "text", "title", "button", "row", "column",
              "grid", "card", "input", "password", "state", "on"}
_EXPR_START_KEYWORDS = {"true", "false", "null", "not", "ask", "match"}

# every 1 <단위> { }  — 시간 단위 → 초
_TIME_UNITS = {
    "ms": 0.001, "msec": 0.001, "millis": 0.001,
    "millisecond": 0.001, "milliseconds": 0.001, "밀리초": 0.001,
    "s": 1.0, "sec": 1.0, "secs": 1.0, "second": 1.0, "seconds": 1.0, "초": 1.0,
    "m": 60.0, "min": 60.0, "mins": 60.0, "minute": 60.0, "minutes": 60.0, "분": 60.0,
    "h": 3600.0, "hr": 3600.0, "hour": 3600.0, "hours": 3600.0, "시간": 3600.0,
}

# 다른 언어 습관 → POI 로 안내 (문장 첫머리에서만).
# def/func/function/fun/elif/lambda/pass/True/False/None 은 이제 그냥 동작하므로 여기 없음.
_FOREIGN_HINT = {
    "elsif": "else if", "elseif": "else if",
    "foreach": "for", "switch": "match", "case": "when",
    "var": "(선언 키워드 없이 바로  이름 = 값)", "let": "(선언 키워드 없이 바로  이름 = 값)",
    "echo": "show", "puts": "show", "console": "show",
    "then": "{ 또는 들여쓰기", "do": "{ 또는 들여쓰기",
}


class Parser:
    def __init__(self, tokens, source: str = "", filename: str = "<poi>"):
        self.toks = tokens
        self.src = source
        self.filename = filename
        self.i = 0

    # -- token helpers -------------------------------------------------
    def peek(self, k=0):
        j = self.i + k
        return self.toks[j] if j < len(self.toks) else self.toks[-1]

    def at_end(self):
        return self.peek().type == "EOF"

    def advance(self):
        t = self.toks[self.i]
        if self.i < len(self.toks) - 1:
            self.i += 1
        return t

    def check(self, type_, value=None):
        t = self.peek()
        if t.type != type_:
            return False
        return value is None or t.value == value

    def check_any(self, type_, values):
        t = self.peek()
        return t.type == type_ and t.value in values

    def match(self, type_, value=None):
        if self.check(type_, value):
            return self.advance()
        return None

    def expect(self, type_, value=None, what=None):
        if self.check(type_, value):
            return self.advance()
        t = self.peek()
        want = what or (value or type_)
        raise POIError(f"'{want}' 이(가) 필요한데 '{_tok_desc(t)}' 이(가) 왔습니다.",
                       "P010", t.line, t.col,
                       hint="괄호나 중괄호 { } 짝이 맞는지, 줄 끝이 맞는지 확인하세요.")

    def skip_nl(self):
        while self.check("NEWLINE") or self.check("OP", ";"):
            self.advance()

    # -- entry ------------------------------------------------------
    def parse(self) -> Node:
        body = []
        self.skip_nl()
        while not self.at_end():
            body.append(self.statement())
            self.skip_nl()
        return Node("Program", body=body)

    # -- blocks --------------------------------------------------
    # 세 가지 방식 다 됨 (섞어도 됨):
    #   1)  ... { 문장들 }          중괄호
    #   2)  ... : 문장              한 줄 (콜론)
    #   3)  ...\n 문장들\n end       중괄호·들여쓰기 없이, end 로 닫기
    def _brace_block(self):
        self.expect("OP", "{")
        self.skip_nl()
        body = []
        while not self.check("OP", "}"):
            if self.at_end():
                raise POIError("중괄호 } 가 닫히지 않았습니다.", "P011", self.peek().line)
            body.append(self.statement())
            self.skip_nl()
        self.expect("OP", "}")
        return body

    def block(self, stops=(), opener_col: int = 0):
        """(문장리스트, style) 반환.  style ∈ {brace, colon, indent, end}.
        'end' 스타일이면 호출부가 반드시 'end' 를 소비해야 하고,
        나머지는 뒤에 'end' 가 있으면 선택적으로 먹는다 (호환용).
        """
        if self.check("OP", "{"):
            return self._brace_block(), "brace"
        stopset = set(stops) | {"end"}
        if self.match("OP", ":"):
            # 콜론 다음이 줄바꿈이면 → 들여쓰기 블록, 아니면 → 한 줄
            if self.check("NEWLINE"):
                self.skip_nl()
                return self._indent_block(stopset, opener_col), "indent"
            return [self.statement()], "colon"
        self.skip_nl()
        # 첫 문장이 여는 줄보다 더 들여써졌으면 → 들여쓰기 블록
        if not self.at_end() and not self.check_any("KEYWORD", stopset) \
                and self.peek().col > opener_col > 0:
            return self._indent_block(stopset, opener_col), "indent"
        # 아니면 end 로 닫는 형태 (중괄호·들여쓰기 불필요)
        body = []
        while not (self.check_any("KEYWORD", stopset) or self.at_end()):
            body.append(self.statement())
            self.skip_nl()
        return body, "end"

    def _indent_block(self, stopset, opener_col):
        body = []
        while not self.at_end() and not self.check_any("KEYWORD", stopset) \
                and self.peek().col > opener_col:
            body.append(self.statement())
            self.skip_nl()
        return body

    def _end(self, style: str):
        if style == "end":
            if not self.match("KEYWORD", "end"):
                t = self.peek()
                raise POIError("블록을 닫는 'end' 가 필요합니다.", "P016", t.line, t.col,
                               hint="중괄호 { } 나 들여쓰기를 쓰거나, 블록 끝에 end 를 넣으세요.")
        else:
            self.match("KEYWORD", "end")  # 있으면 먹고, 없어도 됨

    def statement(self):
        t = self.peek()

        if t.type == "PYBLOCK":
            self.advance()
            return Node("PyBlock", line=t.line, raw=t.value)

        # 다른 언어 습관을 문장 첫머리에서 잡아 친절하게 안내
        if t.type == "IDENT" and t.value in _FOREIGN_HINT \
                and not (self.peek(1).type == "OP" and self.peek(1).value in ("=", "(", ".", ":", "[")):
            raise POIError(
                f"'{t.value}' 는 POI 문법이 아닙니다.", "P014", t.line, t.col,
                hint=f"혹시 '{_FOREIGN_HINT[t.value]}' 를 쓰려고 하셨나요?")

        if t.type == "KEYWORD":
            if t.value == "show":
                self.advance()
                return Node("Show", line=t.line, value=self.expression())
            if t.value == "const":
                return self._const_decl()
            if t.value == "export":
                return self._export_stmt()
            if t.value in ("break", "continue"):
                self.advance()
                return Node("Break" if t.value == "break" else "Continue", line=t.line)
            if t.value == "pass":
                self.advance()
                return Node("Pass", line=t.line)
            if t.value == "while":
                return self._while_stmt()
            if t.value == "fn":
                return self._fn_decl()
            if t.value == "if":
                return self._if_stmt()
            if t.value == "repeat":
                return self._repeat_stmt()
            if t.value == "for":
                return self._for_stmt()
            if t.value == "return":
                self.advance()
                if self.check("NEWLINE") or self.check("OP", "}") or self.at_end() \
                        or self.check("OP", ";"):
                    return Node("Return", line=t.line, value=None)
                return Node("Return", line=t.line, value=self.expression())
            if t.value == "use":
                return self._use_stmt()
            if t.value == "try":
                return self._try_stmt()
            if t.value == "raise":
                self.advance()
                return Node("Raise", line=t.line, value=self.expression())
            if t.value == "assert":
                self.advance()
                start = self.i
                ex = self.expression()
                src = _join_tokens(self.toks[start:self.i])
                message = None
                if self.match("OP", ","):
                    message = self.expression()
                return Node("Assert", line=t.line, test=ex, src=src,
                            message=message)
            if t.value == "test" and self.peek(1).type == "STRING":
                self.advance()
                name = self.advance().value
                body, style = self.block(opener_col=t.col)
                self._end(style)
                return Node("TestBlock", line=t.line, name=name, body=body)
            # 그밖의 'test' 는 값/변수 이름 (이스터에그, `test = ...` 등) → 아래로 흘려보냄
            if t.value == "match":
                return self._match_stmt()

        # background { ... }  — 백그라운드 스레드로 실행
        if t.type == "IDENT" and t.value == "background" \
                and self.peek(1).type == "OP" and self.peek(1).value == "{":
            self.advance()
            return Node("Background", line=t.line, body=self._brace_block())

        # every 1 second { ... }  — 프로그램이 사는 동안 반복
        if t.type == "IDENT" and t.value == "every" \
                and not (self.peek(1).type == "OP"
                         and self.peek(1).value in ("=", ".", "(", "[", ",")):
            ev = self._every_stmt()
            if ev is not None:
                return ev

        # app "제목" { ... }
        if t.type == "IDENT" and t.value == "app" and self.peek(1).type == "STRING" \
                and self.peek(2).type == "OP" and self.peek(2).value == "{":
            self.advance()
            title = self.advance().value
            return Node("App", line=t.line, title=title, body=self._gui_block())

        # server { get "/" { ... } ... }
        if t.type == "IDENT" and t.value == "server" \
                and self.peek(1).type == "OP" and self.peek(1).value == "{":
            return self._server_stmt()

        # webapp "제목" { page "/" { ... } ... }
        if t.type == "IDENT" and t.value == "webapp" and self.peek(1).type == "STRING" \
                and self.peek(2).type == "OP" and self.peek(2).value == "{":
            return self._webapp_stmt()

        # 타입 붙은 선언:  name: Type = value
        if t.type == "IDENT" and self.peek(1).type == "OP" and self.peek(1).value == ":":
            save = self.i
            self.advance()  # name
            self.advance()  # :
            dtype = self.read_type()
            if self.check("OP", "="):
                self.advance()
                return Node("Assign", line=t.line, target=Node("Name", id=t.value),
                            value=self.expression(), is_const=False,
                            declared_type=dtype)
            self.i = save  # 되돌리기 (객체 접근 등 다른 문장)

        # 구조 분해:  { a, b } = obj   또는   [ a, b ] = list
        if t.type == "OP" and t.value in ("{", "["):
            de = self._try_destructure()
            if de is not None:
                return de

        # 표현식 또는 대입
        expr = self.expression()
        if self.check("OP", "="):
            self.advance()
            value = self.expression()
            if expr.kind not in ("Name", "Member", "Index"):
                raise POIError("여기에는 값을 넣을 수 없습니다.", "P012", t.line,
                               hint="왼쪽은 변수 이름이거나 a.b / a[0] 형태여야 합니다.")
            return Node("Assign", line=t.line, target=expr, value=value, is_const=False)
        return Node("ExprStmt", line=t.line, value=expr)

    def _try_destructure(self):
        """{ a, b } = obj  /  [ a, b ] = list  이면 Destructure, 아니면 None(되돌림)."""
        save = self.i
        t = self.advance()               # { 또는 [
        close = "}" if t.value == "{" else "]"
        de_mode = "obj" if t.value == "{" else "arr"
        names = []
        self.skip_nl()
        while not self.check("OP", close):
            if not self.check("IDENT"):
                self.i = save
                return None
            names.append(self.advance().value)
            self.skip_nl()
            if not self.match("OP", ","):
                break
            self.skip_nl()
        if not self.match("OP", close) or not names or not self.check("OP", "="):
            self.i = save
            return None
        self.advance()                   # =
        return Node("Destructure", line=t.line, mode=de_mode, names=names,
                    value=self.expression())

    def _const_decl(self):
        t = self.advance()
        name = self.expect("IDENT", what="상수 이름").value
        dtype = None
        if self.match("OP", ":"):
            dtype = self.read_type()
        self.expect("OP", "=")
        return Node("Assign", line=t.line, target=Node("Name", id=name),
                    value=self.expression(), is_const=True, declared_type=dtype)

    def _export_stmt(self):
        t = self.advance()  # export
        inner = self.statement()
        names = []
        if inner.kind == "FnDecl":
            names = [inner.name]
        elif inner.kind == "Assign" and getattr(inner.target, "kind", "") == "Name":
            names = [inner.target.id]
        else:
            raise POIError("export 는 fn / const / 이름 = 값 앞에만 붙일 수 있어요.",
                           "P017", t.line)
        return Node("Export", line=t.line, decl=inner, names=names)

    def _while_stmt(self):
        t = self.advance()
        cond = self.expression()
        body, style = self.block(opener_col=t.col)
        self._end(style)
        return Node("While", line=t.line, cond=cond, body=body)

    def _every_stmt(self):
        """every <수> <단위>? { ... }  → Every.  아니면 되돌리고 None."""
        save = self.i
        t = self.advance()  # every
        try:
            amount = self._addsub()
        except POIError:
            self.i = save
            return None
        secs = amount
        if self.check("IDENT") and self.peek().value in _TIME_UNITS:
            mult = _TIME_UNITS[self.advance().value]
            if mult != 1.0:
                secs = Node("BinOp", line=t.line, op="*", left=amount,
                            right=Node("Num", line=t.line, value=mult))
        if not self.check("OP", "{"):
            self.i = save
            return None
        return Node("Every", line=t.line, seconds=secs, body=self._brace_block())

    def _range(self):
        node = self._addsub()
        if self.check("OP", "..") or self.check("OP", "..<"):
            op = self.advance().value
            hi = self._addsub()
            return Node("Range", line=node.line, lo=node, hi=hi,
                        inclusive=(op == ".."))
        return node

    def _fn_decl(self):
        t = self.advance()
        name = self.expect("IDENT", what="함수 이름").value
        self.expect("OP", "(")
        params = []
        param_names = set()
        saw_default = False
        self.skip_nl()
        while not self.check("OP", ")"):
            param_token = self.expect("IDENT", what="매개변수 이름")
            pname = param_token.value
            if pname in param_names:
                raise POIError(
                    f"'{pname}' 매개변수 이름을 두 번 선언했습니다.",
                    "P024", param_token.line, param_token.col,
                    hint="각 매개변수에는 서로 다른 이름을 사용하세요.")
            param_names.add(pname)
            ptype = None
            if self.match("OP", ":"):
                ptype = self.read_type()
            default = None
            if self.match("OP", "="):
                default = self.expression()
                saw_default = True
            elif saw_default:
                raise POIError(
                    f"기본값이 있는 인자 뒤에는 필수 인자 '{pname}' 을 둘 수 없습니다.",
                    "P023", param_token.line, param_token.col,
                    hint=f"'{pname}' 에도 기본값을 주거나, 기본값이 있는 인자보다 앞으로 옮기세요.")
            params.append((pname, default, ptype))
            self.skip_nl()
            if not self.match("OP", ","):
                break
            self.skip_nl()
        self.expect("OP", ")")
        ret_type = None
        if self.match("OP", "->"):
            ret_type = self.read_type()
        if self.match("OP", "=>"):
            return Node("FnDecl", line=t.line, name=name, params=params,
                        body=self.expression(), is_expr_body=True, ret_type=ret_type)
        body, style = self.block(opener_col=t.col)
        self._end(style)
        return Node("FnDecl", line=t.line, name=name, params=params,
                    body=body, is_expr_body=False, ret_type=ret_type)

    def _if_stmt(self):
        t = self.advance()
        cond = self.expression()
        first, style = self.block(("else", "elif"), opener_col=t.col)
        branches = [(cond, first)]
        orelse = None
        self.skip_nl()
        while self.check("KEYWORD", "else") or self.check("KEYWORD", "elif"):
            is_elif = self.check("KEYWORD", "elif")
            self.advance()
            self.skip_nl()
            if is_elif or self.match("KEYWORD", "if"):
                c2 = self.expression()
                b2, _ = self.block(("else", "elif"), opener_col=t.col)
                branches.append((c2, b2))
                self.skip_nl()
            else:
                orelse, _ = self.block(("elif",), opener_col=t.col)
                break
        self._end(style)
        return Node("If", line=t.line, branches=branches, orelse=orelse)

    def _repeat_stmt(self):
        t = self.advance()
        count = self.expression()
        var = None
        if self.match("KEYWORD", "as"):
            var = self._var_name("반복 변수")
        body, style = self.block(opener_col=t.col)
        self._end(style)
        return Node("Repeat", line=t.line, count=count, var=var, body=body)

    def _for_stmt(self, gui=False):
        t = self.advance()
        var = self._var_name("반복 변수")
        self.expect("KEYWORD", "in")
        it = self.expression()
        if gui:
            return Node("ForIn", line=t.line, var=var, iterable=it,
                        body=self._gui_block(), gui=True)
        body, style = self.block(opener_col=t.col)
        self._end(style)
        return Node("ForIn", line=t.line, var=var, iterable=it, body=body, gui=False)

    def _match_stmt(self):
        t = self.advance()  # match
        subject = self.expression()
        brace = bool(self.match("OP", "{"))
        self.skip_nl()
        clauses = []
        default = None
        while True:
            self.skip_nl()
            if brace and self.match("OP", "}"):
                break
            if not brace and self.match("KEYWORD", "end"):
                break
            if self.at_end():
                if brace:
                    self.expect("OP", "}")
                break
            if self.match("KEYWORD", "else"):
                default, _ = self.block(("when", "else"), opener_col=t.col)
                self.skip_nl()
                continue
            self.expect("KEYWORD", "when")
            pats = [self._pattern()]
            while self.match("OP", ","):
                pats.append(self._pattern())
            body, _ = self.block(("when", "else"), opener_col=t.col)
            clauses.append((pats, body))
            self.skip_nl()
        return Node("Match", line=t.line, subject=subject, clauses=clauses,
                    default=default)

    def _match_expr(self):
        t = self.advance()  # match
        subject = self.expression()
        brace = bool(self.match("OP", "{"))
        if not brace:
            self.match("OP", ":")
        self.skip_nl()
        clauses = []
        default = None
        while True:
            self.skip_nl()
            if brace and self.match("OP", "}"):
                break
            if not brace and self.match("KEYWORD", "end"):
                break
            if self.at_end():
                if brace:
                    self.expect("OP", "}")
                break
            if self.match("KEYWORD", "else"):
                self.expect("OP", "=>")
                default = self.expression()
                self.skip_nl()
                continue
            self.expect("KEYWORD", "when")
            pats = [self._pattern()]
            while self.match("OP", ","):
                pats.append(self._pattern())
            self.expect("OP", "=>")
            clauses.append((pats, self.expression()))
            self.skip_nl()
        return Node("MatchExpr", line=t.line, subject=subject, clauses=clauses,
                    default=default)

    def _pattern(self):
        if self.check_any("OP", {">", "<", ">=", "<=", "==", "!="}):
            op = self.advance().value
            return Node("PatCompare", op=op, value=self._addsub())
        if self.match("KEYWORD", "between"):
            lo = self._addsub()
            self.expect("KEYWORD", "and")
            hi = self._addsub()
            return Node("PatRange", low=lo, high=hi)
        return Node("PatValue", value=self.expression())

    def _use_stmt(self):
        t = self.advance()
        nxt = self.peek()
        if nxt.type == "IDENT" and nxt.value == "py" and self.peek(1).value == ":":
            self.advance()
            self.advance()
            parts = [self.expect("IDENT", what="모듈 이름").value]
            while self.match("OP", "."):
                parts.append(self.expect("IDENT").value)
            alias = None
            if self.match("KEYWORD", "as"):
                alias = self.expect("IDENT").value
            return Node("Use", line=t.line, use_kind="py", target=".".join(parts), alias=alias)
        if nxt.type == "IDENT" and nxt.value == "pkg" and self.peek(1).value == ":":
            self.advance()
            self.advance()
            name = self.expect("IDENT", what="패키지 이름").value
            alias = None
            if self.match("KEYWORD", "as"):
                alias = self.expect("IDENT").value
            return Node("Use", line=t.line, use_kind="pkgmod", target=name,
                        alias=alias or name)
        if nxt.type == "IDENT" and nxt.value == "pyfile":
            self.advance()
            path = self.expect("STRING", what="파일 경로").value
            stem = _stem(path)
            return Node("Use", line=t.line, use_kind="pyfile", target=path, alias=stem)
        if nxt.type == "STRING":
            path = self.advance().value
            alias = None
            if self.match("KEYWORD", "as"):
                alias = self.expect("IDENT").value
            return Node("Use", line=t.line, use_kind="poimod", target=path,
                        alias=alias or _stem(path))
        name = self.expect("IDENT", what="모듈 이름").value
        alias = None
        if self.match("KEYWORD", "as"):
            alias = self.expect("IDENT").value
        return Node("Use", line=t.line, use_kind="std", target=name, alias=alias)

    def _try_stmt(self):
        t = self.advance()
        body, s1 = self.block(("catch",), opener_col=t.col)
        self.skip_nl()
        self.expect("KEYWORD", "catch")
        name = None
        err_type = None
        if self.check("IDENT"):
            first = self.advance().value
            if self.match("KEYWORD", "as"):          # catch ValueError as e
                err_type = first
                name = self.expect("IDENT", what="오류 변수").value
            else:                                     # catch e
                name = first
        handler, s2 = self.block(opener_col=t.col)
        self._end("end" if "end" in (s1, s2) else s2)
        return Node("TryCatch", line=t.line, body=body, name=name,
                    handler=handler, err_type=err_type)

    # -- WEB (v1.6) ---------------------------------------------
    _HTTP_METHODS = {"get", "post", "put", "delete", "patch"}

    def _server_stmt(self):
        t = self.advance()  # 'server'
        self.expect("OP", "{")
        self.skip_nl()
        routes = []
        statics = []
        while not self.check("OP", "}"):
            if self.at_end():
                raise POIError("server { 가 닫히지 않았습니다.", "P013", self.peek().line)
            w = self.peek()
            if w.type == "IDENT" and w.value in self._HTTP_METHODS:
                self.advance()
                path = self.expect("STRING", what="라우트 경로").value
                body, style = self.block(opener_col=w.col)
                self._end(style)
                routes.append((w.value.upper(), path, body))
            elif w.type == "IDENT" and w.value == "static":
                self.advance()
                statics.append(self.expect("STRING", what="정적 폴더").value)
            else:
                # 그밖의 문장(변수 선언 등)은 서버 시작 전에 실행
                routes.append(("__setup__", None, [self.statement()]))
            self.skip_nl()
        self.expect("OP", "}")
        return Node("Server", line=t.line, routes=routes, statics=statics)

    def _webapp_stmt(self):
        t = self.advance()  # 'webapp'
        title = self.advance().value  # STRING
        self.expect("OP", "{")
        self.skip_nl()
        states, pages, actions = [], [], []
        while not self.check("OP", "}"):
            if self.at_end():
                raise POIError("webapp { 가 닫히지 않았습니다.", "P013", self.peek().line)
            w = self.peek()
            if w.type == "IDENT" and w.value == "state":
                self.advance()
                nm = self.expect("IDENT", what="상태 이름").value
                self.expect("OP", "=")
                states.append((nm, self.expression()))
            elif w.type == "IDENT" and w.value == "page":
                self.advance()
                path = self.expect("STRING", what="페이지 경로").value
                pages.append((path, self._web_block(w.col)))
            elif w.type == "IDENT" and w.value == "action":
                self.advance()
                path = self.expect("STRING", what="액션 경로").value
                body, style = self.block(opener_col=w.col)
                self._end(style)
                actions.append((path, body))
            else:
                actions.append(("__setup__", [self.statement()]))
            self.skip_nl()
        self.expect("OP", "}")
        return Node("WebApp", line=t.line, title=title, states=states,
                    pages=pages, actions=actions)

    _WEB_WORDS = {"title", "text", "link", "card", "row", "column", "form",
                  "input", "password", "textarea", "button", "html",
                  "heading", "subtitle", "badge", "divider", "spacer",
                  "image", "alert", "notice", "field", "select", "checkbox"}

    def _web_block(self, opener_col):
        self.expect("OP", "{")
        self.skip_nl()
        nodes = []
        while not self.check("OP", "}"):
            if self.at_end():
                raise POIError("페이지 블록의 } 가 닫히지 않았습니다.", "P013",
                               self.peek().line)
            nodes.append(self._web_node())
            self.skip_nl()
        self.expect("OP", "}")
        return nodes

    def _web_node(self):
        t = self.peek()
        if t.type == "KEYWORD" and t.value == "for":
            tk = self.advance()
            var = self._var_name("반복 변수")
            self.expect("KEYWORD", "in")
            it = self.expression()
            return Node("ForIn", line=tk.line, var=var, iterable=it,
                        body=self._web_block(tk.col), gui=False, web=True)
        if t.type == "KEYWORD" and t.value == "if":
            tk = self.advance()
            cond = self.expression()
            body = self._web_block(tk.col)
            orelse = None
            self.skip_nl()
            if self.match("KEYWORD", "else"):
                orelse = self._web_block(tk.col)
            return Node("If", line=tk.line, branches=[(cond, body)], orelse=orelse,
                        web=True)
        if t.type == "IDENT" and t.value in self._WEB_WORDS:
            w = self.advance().value
            if w in ("title", "text", "heading", "subtitle", "badge",
                     "alert", "notice"):
                return Node("WKind", line=t.line, kind_="W" + w, value=self.expression())
            if w == "divider":
                return Node("WKind", line=t.line, kind_="Wdivider", value=None)
            if w == "spacer":
                amt = self.expression() if self._starts_expr() else Node("Num", value=24)
                return Node("WKind", line=t.line, kind_="Wspacer", value=amt)
            if w == "image":
                return Node("WKind", line=t.line, kind_="Wimage", value=self.expression())
            if w in ("field", "select", "checkbox"):
                label = self.expression()
                self.expect("OP", "->")
                name = self.expect("IDENT", what="입력 이름").value
                opts = None
                if w == "select":
                    opts = self.expression()  # 옵션 배열
                return Node("WField", line=t.line, ftype=w, label=label,
                            name=name, opts=opts)
            if w == "link":
                label = self.expression()
                self.expect("OP", "->")
                href = self.expression()
                return Node("WLink", line=t.line, text=label, href=href)
            if w in ("card", "row", "column"):
                kind = {"card": "WCard", "row": "WRow", "column": "WCol"}[w]
                return Node(kind, line=t.line, body=self._web_block(t.col))
            if w == "form":
                action = self.expect("STRING", what="폼 액션 경로").value
                return Node("WForm", line=t.line, action=action,
                            body=self._web_block(t.col))
            if w in ("input", "password", "textarea"):
                label = self.expression()
                name = None
                if self.match("OP", "->"):
                    name = self.expect("IDENT", what="입력 이름").value
                return Node("WInput", line=t.line, label=label,
                            name=name or "field", secret=(w == "password"),
                            multiline=(w == "textarea"))
            if w == "button":
                return Node("WButton", line=t.line, value=self.expression())
            if w == "html":
                return Node("WHtml", line=t.line, value=self.expression())
        return self.statement()

    # -- GUI ------------------------------------------------------
    def _gui_block(self):
        self.expect("OP", "{")
        self.skip_nl()
        nodes = []
        while not self.check("OP", "}"):
            if self.at_end():
                raise POIError("app 블록의 } 가 닫히지 않았습니다.", "P013", self.peek().line)
            nodes.append(self._gui_stmt())
            self.skip_nl()
        self.expect("OP", "}")
        return nodes

    def _gui_stmt(self):
        t = self.peek()
        if t.type == "KEYWORD" and t.value == "for":
            return self._for_stmt(gui=True)
        if t.type == "KEYWORD" and t.value == "if":
            return self._gui_if()

        if t.type == "IDENT" and t.value in _GUI_WORDS:
            w = self.advance().value
            if w == "window":
                return Node("GWindow", line=t.line, props=self._prop_bag())
            if w == "text":
                return Node("GText", line=t.line, value=self.expression(), heading=False)
            if w == "title":
                return Node("GText", line=t.line, value=self.expression(), heading=True)
            if w == "button":
                label = self.expression()
                body = self._gui_block() if self.check("OP", "{") else []
                return Node("GButton", line=t.line, label=label, body=body)
            if w in ("row", "column", "grid", "card"):
                kind = {"row": "GRow", "column": "GColumn",
                        "grid": "GColumn", "card": "GCard"}[w]
                return Node(kind, line=t.line, body=self._gui_block())
            if w in ("input", "password"):
                label = self.expression()
                bind = None
                if self.match("OP", "->"):
                    bind = self.expect("IDENT", what="연결할 변수").value
                return Node("GInput", line=t.line, label=label, bind=bind,
                            secret=(w == "password"))
            if w == "state":
                name = self.expect("IDENT", what="상태 이름").value
                self.expect("OP", "=")
                return Node("GState", line=t.line, name=name, value=self.expression())
            if w == "on":
                ev = self.advance().value
                return Node("GOn", line=t.line, event=str(ev), body=self._gui_block())

        # 그밖에는 일반 문장 (예: db = database("x.db"))
        return self.statement()

    def _gui_if(self):
        t = self.advance()
        branches = [(self.expression(), self._gui_block())]
        orelse = None
        self.skip_nl()
        while self.check("KEYWORD", "else"):
            self.advance()
            self.skip_nl()
            if self.match("KEYWORD", "if"):
                branches.append((self.expression(), self._gui_block()))
                self.skip_nl()
            else:
                orelse = self._gui_block()
                break
        return Node("If", line=t.line, branches=branches, orelse=orelse)

    def _prop_bag(self):
        self.expect("OP", "{")
        self.skip_nl()
        props = {}
        while not self.check("OP", "}"):
            key = self.expect("IDENT", what="속성 이름").value
            self.expect("OP", ":")
            props[key] = self._prop_value()
            if self.match("OP", ","):
                pass
            self.skip_nl()
        self.expect("OP", "}")
        return props

    def _prop_value(self):
        t = self.peek()
        if t.type == "DIM":
            self.advance()
            return Node("Str", value=t.value)
        if t.type == "KEYWORD" and t.value in ("true", "false"):
            self.advance()
            return Node("Bool", value=(t.value == "true"))
        if t.type == "IDENT":
            self.advance()
            return Node("Str", value=t.value)
        return self.expression()

    # -- expressions --------------------------------------------
    def expression(self):
        lam = self._try_lambda()
        if lam is not None:
            return lam
        node = self._pipeline()
        # 삼항식:  값  if  조건  else  다른값   (파이썬과 같은 순서)
        if self.check("KEYWORD", "if"):
            self.advance()
            cond = self._pipeline()
            self.expect("KEYWORD", "else", what="삼항식의 else")
            alt = self.expression()
            return Node("Ternary", line=node.line, body=node, cond=cond, alt=alt)
        return node

    def _try_lambda(self):
        """ x => 식   또는   (a, b) => 식   을 익명 함수로."""
        t = self.peek()
        # x => ...
        if t.type == "IDENT" and self.peek(1).type == "OP" and self.peek(1).value == "=>":
            self.advance()
            self.advance()
            if self.check("OP", "{"):
                return Node("Lambda", line=t.line, params=[t.value],
                            body=self._brace_block(), is_block=True)
            return Node("Lambda", line=t.line, params=[t.value], body=self.expression())
        # ( a, b ) => ...
        if t.type == "OP" and t.value == "(":
            save = self.i
            self.advance()
            params = []
            ok = True
            if not self.check("OP", ")"):
                while True:
                    if not self.check("IDENT"):
                        ok = False
                        break
                    params.append(self.advance().value)
                    if self.match("OP", ":"):
                        self._skip_type()
                    if self.match("OP", ","):
                        continue
                    break
            if ok and self.match("OP", ")") and self.check("OP", "=>"):
                self.advance()
                if self.check("OP", "{"):
                    return Node("Lambda", line=t.line, params=params,
                                body=self._brace_block(), is_block=True)
                return Node("Lambda", line=t.line, params=params, body=self.expression())
            self.i = save
        return None

    def _pipeline(self):
        node = self._coalesce()
        while self.match("OP", "|>"):
            self.skip_nl()
            stage = self._unary()
            if stage.kind == "Call":
                node = Node("Call", line=node.line, func=stage.func,
                            args=[node] + stage.args, kwargs=stage.kwargs)
            else:
                node = Node("Call", line=node.line, func=stage, args=[node], kwargs=[])
        return node

    def _coalesce(self):
        node = self._or()
        while self.match("OP", "??"):
            node = Node("Coalesce", line=node.line, left=node, right=self._or())
        return node

    def _or(self):
        node = self._and()
        vals = [node]
        while self.check("KEYWORD", "or") or self.check("OP", "||"):
            self.advance()
            vals.append(self._and())
        if len(vals) == 1:
            return node
        return Node("BoolOp", line=node.line, op="or", values=vals)

    def _and(self):
        node = self._not()
        vals = [node]
        while self.check("KEYWORD", "and") or self.check("OP", "&&"):
            self.advance()
            vals.append(self._not())
        if len(vals) == 1:
            return node
        return Node("BoolOp", line=node.line, op="and", values=vals)

    def _not(self):
        if self.check("KEYWORD", "not") or self.check("OP", "!"):
            t = self.advance()
            return Node("UnaryOp", line=t.line, op="not", operand=self._not())
        return self._comparison()

    def _comparison(self):
        left = self._range()
        if self.match("KEYWORD", "between"):
            low = self._addsub()
            self.expect("KEYWORD", "and")
            high = self._addsub()
            return Node("Between", line=left.line, value=left, low=low, high=high)
        if self.match("KEYWORD", "is"):
            neg = bool(self.match("KEYWORD", "not"))
            right = self._addsub()
            return Node("Is", line=left.line, left=left, right=right, negated=neg)
        ops, comps = [], []
        while self.check_any("OP", _COMPARE_OPS):
            ops.append(self.advance().value)
            comps.append(self._range())
        if ops:
            return Node("Compare", line=left.line, left=left, ops=ops, comparators=comps)
        return left

    def _addsub(self):
        node = self._muldiv()
        while self.check_any("OP", _ADD_OPS):
            op = self.advance().value
            node = Node("BinOp", line=node.line, op=op, left=node, right=self._muldiv())
        return node

    def _muldiv(self):
        node = self._unary()
        while self.check_any("OP", _MUL_OPS):
            op = self.advance().value
            node = Node("BinOp", line=node.line, op=op, left=node, right=self._unary())
        return node

    def _unary(self):
        if self.check_any("OP", {"-", "+"}):
            t = self.advance()
            return Node("UnaryOp", line=t.line, op=t.value, operand=self._unary())
        return self._postfix()

    def _var_name(self, what="변수 이름"):
        """변수 이름 자리 — IDENT, 또는 값으로도 쓰이는 문맥 키워드('test')."""
        t = self.peek()
        if t.type == "IDENT" or (t.type == "KEYWORD" and t.value == "test"):
            self.advance()
            return str(t.value)
        raise POIError(f"{what}이(가) 필요합니다.", "P010", t.line, t.col)

    def _member_name(self):
        # `.` 뒤에는 이름 자리이므로 예약어(test/end/is 등)도 속성 이름으로 허용
        t = self.peek()
        if t.type in ("IDENT", "KEYWORD"):
            self.advance()
            return str(t.value)
        raise POIError("'.' 뒤에는 속성 이름이 와야 합니다.", "P010", t.line, t.col)

    def _postfix(self):
        node = self._primary()
        while True:
            if self.match("OP", "."):
                node = Node("Member", line=node.line, obj=node,
                            name=self._member_name(), safe=False)
            elif self.match("OP", "?."):
                node = Node("Member", line=node.line, obj=node,
                            name=self._member_name(), safe=True)
            elif self.match("OP", "("):
                args, kwargs = self._arglist()
                self.expect("OP", ")")
                node = Node("Call", line=node.line, func=node, args=args, kwargs=kwargs)
            elif self.match("OP", "["):
                idx = self.expression()
                self.expect("OP", "]")
                node = Node("Index", line=node.line, obj=node, index=idx)
            else:
                break
        return node

    def _arglist(self):
        args, kwargs = [], []
        self.skip_nl()
        if self.check("OP", ")"):
            return args, kwargs
        while True:
            self.skip_nl()
            if self.check("IDENT") and self.peek(1).type == "OP" \
                    and self.peek(1).value == ":":
                key = self.advance().value
                self.advance()
                kwargs.append((key, self.expression()))
            else:
                args.append(self.expression())
            self.skip_nl()
            if not self.match("OP", ","):
                break
        return args, kwargs

    def _primary(self):
        t = self.peek()
        if t.type == "NUMBER":
            self.advance()
            return Node("Num", line=t.line, value=t.value)
        if t.type == "STRING":
            self.advance()
            return Node("Str", line=t.line, value=t.value)
        if t.type == "DIM":
            self.advance()
            return Node("Str", line=t.line, value=t.value)
        if t.type == "KEYWORD":
            if t.value in ("true", "false"):
                self.advance()
                return Node("Bool", line=t.line, value=(t.value == "true"))
            if t.value == "null":
                self.advance()
                return Node("Null", line=t.line)
            if t.value == "ask":
                self.advance()
                if self._starts_expr():
                    return Node("Ask", line=t.line, prompt=self._unary())
                return Node("Ask", line=t.line, prompt=Node("Str", value=""))
            if t.value == "test":  # 'test' 는 이스터에그 값으로도 쓰인다
                self.advance()
                return Node("Name", line=t.line, id="test")
            if t.value == "match":  # 식으로서의 match — 값을 돌려준다
                return self._match_expr()
            if t.value == "lambda":  # 파이썬식 lambda a, b: 식  →  화살표 함수
                self.advance()
                params = []
                while self.check("IDENT"):
                    params.append(self.advance().value)
                    if not self.match("OP", ","):
                        break
                self.expect("OP", ":", what="lambda 의 ':'")
                return Node("Lambda", line=t.line, params=params,
                            body=self.expression())
        if t.type == "OP" and t.value == "(":
            self.advance()
            self.skip_nl()
            inner = self.expression()
            self.skip_nl()
            self.expect("OP", ")")
            return inner
        if t.type == "OP" and t.value == "[":
            return self._array_lit()
        if t.type == "OP" and t.value == "{":
            return self._object_lit()
        if t.type == "IDENT":
            self.advance()
            return Node("Name", line=t.line, id=t.value)
        raise POIError(f"여기서 '{_tok_desc(t)}' 은(는) 올 수 없습니다.", "P014",
                       t.line, t.col,
                       hint="값(숫자/문자/변수)이나 여는 괄호가 와야 합니다.")

    def _array_lit(self):
        t = self.advance()  # [
        self.skip_nl()
        elems = []
        while not self.check("OP", "]"):
            elems.append(self.expression())
            self.skip_nl()
            if not self.match("OP", ","):
                break
            self.skip_nl()
        self.expect("OP", "]")
        return Node("ArrayLit", line=t.line, elements=elems)

    def _object_lit(self):
        t = self.advance()  # {
        self.skip_nl()
        pairs = []
        while not self.check("OP", "}"):
            if self.check("IDENT") or self.check("STRING"):
                key = self.advance().value
            else:
                kt = self.peek()
                raise POIError(f"객체의 키 이름이 필요합니다 (받은 것: '{_tok_desc(kt)}').",
                               "P015", kt.line, kt.col)
            self.expect("OP", ":")
            pairs.append((key, self.expression()))
            self.skip_nl()
            if not self.match("OP", ","):
                break
            self.skip_nl()
        self.expect("OP", "}")
        return Node("ObjectLit", line=t.line, pairs=pairs)

    # -- misc ---------------------------------------------------
    def _starts_expr(self):
        t = self.peek()
        if t.type in ("NUMBER", "STRING", "IDENT", "DIM"):
            return True
        if t.type == "KEYWORD" and t.value in _EXPR_START_KEYWORDS:
            return True
        if t.type == "OP" and t.value in ("(", "[", "{", "-", "+", "!"):
            return True
        return False

    _KOREAN_TYPES = {
        "정수": "Int", "실수": "Float", "숫자": "Number",
        "문자": "Text", "문자열": "Text", "글": "Text",
        "참거짓": "Bool", "불": "Bool", "불리언": "Bool",
        "목록": "List", "배열": "List",
        "사전": "Map", "맵": "Map", "객체": "Map",
        "함수": "Fn", "기능": "Fn",
        "아무": "Any", "아무거나": "Any", "무엇이든": "Any",
        "없음": "Null",
    }
    _TYPE_NORM = {
        "int": "Int", "integer": "Int", "Integer": "Int",
        "float": "Float", "Float64": "Float", "double": "Float",
        "num": "Number", "number": "Number",
        "str": "Text", "string": "Text", "String": "Text",
        "bool": "Bool", "boolean": "Bool", "Boolean": "Bool",
        "list": "List", "array": "List", "Array": "List",
        "map": "Map", "dict": "Map", "object": "Map", "Object": "Map",
        "fn": "Fn", "function": "Fn", "Function": "Fn", "func": "Fn",
        "any": "Any", "Any": "Any", "void": "Null", "none": "Null", "null": "Null",
    }

    def read_type(self) -> str:
        """타입 표기를 읽어 정규화된 이름을 돌려준다. 검사(typecheck)에만 쓰인다.

        제네릭 인자를 버리지 않고 보존해 `List<Int>`와 `List<Text>`를
        구분할 수 있게 한다.
        """
        t = self.peek()
        if t.type in ("IDENT", "KEYWORD"):
            self.advance()
            name = str(t.value)
        else:
            raise POIError("타입 이름이 필요합니다.", "P010", t.line, t.col)
        while self.match("OP", "."):
            if self.check("IDENT"):
                name = self.advance().value
        generic_args = []
        for op_open, op_close in (("<", ">"), ("[", "]")):
            if self.check("OP", op_open):
                self.advance()
                if not self.check("OP", op_close):
                    while not self.at_end() and not self.check("OP", op_close):
                        generic_args.append(self.read_type())
                        if not self.match("OP", ","):
                            break
                if not self.match("OP", op_close):
                    t = self.peek()
                    raise POIError(f"타입의 {op_close}가 필요합니다.", "P011",
                                   t.line, t.col)
        nullable = bool(self.match("OP", "?"))
        base = self._KOREAN_TYPES.get(name) or self._TYPE_NORM.get(name) or name
        if base in ("Int", "Float", "Number", "Text", "Bool", "List", "Map",
                    "Fn", "Any", "Null") or base[:1].isupper():
            if generic_args:
                base += "<" + ",".join(generic_args) + ">"
            return base + ("?" if nullable else "")
        return "Any"

    def _skip_type(self):
        self.read_type()


def _join_tokens(toks) -> str:
    """토큰들을 사람이 읽기 좋은 소스 근사치로 (assert 메시지용)."""
    out = []
    no_space_before = {")", "]", ",", ".", "?.", "("}
    no_space_after = {"(", "[", ".", "?."}
    for i, t in enumerate(toks):
        val = '"' + str(t.value) + '"' if t.type == "STRING" else str(t.value)
        if out and val not in no_space_before and out[-1] not in no_space_after:
            out.append(" ")
        out.append(val)
    return "".join(out).strip()


def _tok_desc(t):
    if t.type == "NEWLINE":
        return "줄바꿈"
    if t.type == "EOF":
        return "파일 끝"
    return str(t.value)


def _stem(path: str) -> str:
    base = path.replace("\\", "/").rsplit("/", 1)[-1]
    if "." in base:
        base = base.rsplit(".", 1)[0]
    return "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in base) or "mod"
