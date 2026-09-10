"""선택적 정적 타입 검사 (v1.5).

`poi check --types 파일.poi`  — 타입 표기를 실제로 검사한다.
`poi run --types 파일.poi`    — 경고만 찍고 그냥 실행한다.

절대 오탐하지 않는 게 원칙 — 양쪽 타입이 **확실할 때만** 지적한다.
타입은 순수 린트이고 실행에는 영향 없다.
"""
from __future__ import annotations

from .errors import POIError

_NUMERIC = {"Int", "Float", "Number"}
_KNOWN = {"Int", "Float", "Number", "Text", "Bool", "List", "Map", "Fn", "Null", "Any"}


class Finding:
    def __init__(self, code, msg, line, hint=None, level="error"):
        self.code, self.msg, self.line, self.hint, self.level = \
            code, msg, line, hint, level


def _base(t):
    return (t or "Any").rstrip("?")


def _nullable(t):
    return bool(t) and t.endswith("?")


def compat(actual: str, expected: str) -> bool:
    """actual 값을 expected 자리에 넣어도 되는가? 모르면 True (관대)."""
    a, e = _base(actual), _base(expected)
    if "Any" in (a, e) or a == "" or e == "":
        return True
    if a == e:
        return True
    if a == "Null":
        return _nullable(expected) or e in ("Any",)
    if e in _NUMERIC and a in _NUMERIC:
        return True  # Int -> Float 등 허용
    if e == "Number" and a in _NUMERIC:
        return True
    return False


class Checker:
    def __init__(self):
        self.findings: list[Finding] = []
        self.fns: dict[str, tuple] = {}   # name -> (param_types, ret_type)
        self.scopes: list[dict] = [{}]

    # env
    def _set(self, name, typ):
        self.scopes[-1][name] = typ

    def _get(self, name):
        for s in reversed(self.scopes):
            if name in s:
                return s[name]
        return "Any"

    def _err(self, code, msg, line, hint=None):
        self.findings.append(Finding(code, msg, line, hint))

    # ---- inference -------------------------------------------------
    def infer(self, n) -> str:
        k = n.kind
        if k == "Num":
            return "Float" if isinstance(n.value, float) else "Int"
        if k == "Str":
            return "Text"
        if k == "Bool":
            return "Bool"
        if k == "Null":
            return "Null"
        if k == "ArrayLit":
            return "List"
        if k == "ObjectLit":
            return "Map"
        if k == "Lambda":
            return "Fn"
        if k == "Name":
            return self._get(n.id)
        if k in ("Compare", "Is", "Between", "BoolOp"):
            return "Bool"
        if k == "UnaryOp":
            return "Bool" if n.op == "not" else self.infer(n.operand)
        if k == "BinOp":
            return self._infer_binop(n)
        if k == "Ternary":
            ct = self.infer(n.cond)
            if _base(ct) not in ("Bool", "Any"):
                self._err("P408",
                          f"삼항식 조건은 Bool 이어야 하는데 {_base(ct)} 입니다.",
                          n.cond.line or n.line,
                          "비교식이나 true/false 값을 사용하세요.")
            a, b = self.infer(n.body), self.infer(n.alt)
            return a if _base(a) == _base(b) else "Any"
        if k == "Coalesce":
            return "Any"
        if k == "Ask":
            return "Text"
        if k == "Call":
            return self._infer_call(n)
        if k in ("Member", "Index"):
            return "Any"
        return "Any"

    def _infer_binop(self, n):
        lt, rt = _base(self.infer(n.left)), _base(self.infer(n.right))
        if n.op == "+":
            if lt == "Text" and rt == "Text":
                return "Text"
            if lt in _NUMERIC and rt in _NUMERIC:
                return "Float" if "Float" in (lt, rt) else "Int"
            if {lt, rt} == {"Text", "Int"} or {lt, rt} == {"Text", "Float"}:
                self._err("P401",
                          "문자(Text)와 숫자를 + 로 더할 수 없습니다.", n.line,
                          "text(...) 로 숫자를 문자로 바꾸거나 number(...) 로 반대로 하세요.")
            return "Any"
        if n.op in ("-", "*", "/", "%"):
            if lt in _NUMERIC and rt in _NUMERIC:
                return "Float" if (n.op == "/" or "Float" in (lt, rt)) else "Int"
            if "Text" in (lt, rt) and "Any" not in (lt, rt):
                self._err("P402",
                          f"문자(Text)에는 {n.op} 연산을 쓸 수 없습니다.", n.line)
            return "Any"
        return "Any"

    def _infer_call(self, n):
        fn = n.func
        if fn.kind == "Name" and fn.id in self.fns:
            ptypes, ret = self.fns[fn.id]
            pos = [a for a in n.args]
            if len(pos) > len(ptypes):
                self._err("P404",
                          f"'{fn.id}' 함수는 인자 {len(ptypes)}개인데 {len(pos)}개를 줬습니다.",
                          n.line)
            for arg, pt in zip(pos, ptypes):
                if pt:
                    at = self.infer(arg)
                    if not compat(at, pt):
                        self._err("P403",
                                  f"'{fn.id}' 의 인자 자리에는 {_base(pt)} 가 와야 하는데 "
                                  f"{_base(at)} 를 줬습니다.", arg.line or n.line)
            return ret or "Any"
        return "Any"

    # ---- statements ---------------------------------------------
    def run(self, program):
        # 1차: 함수 시그니처 먼저 수집 (선언 순서 무관하게)
        for s in program.body:
            if s.kind == "FnDecl":
                self._collect_fn(s)
        for s in program.body:
            self.stmt(s)
        return self.findings

    def _collect_fn(self, n):
        ptypes = [p[2] if len(p) > 2 else None for p in n.params]
        self.fns[n.name] = (ptypes, getattr(n, "ret_type", None))

    def stmt(self, n):
        k = n.kind
        if k == "Assign":
            self._assign(n)
        elif k == "FnDecl":
            self._fn(n)
        elif k == "If":
            for condition, body in n.branches:
                actual = self.infer(condition)
                if _base(actual) not in ("Bool", "Any"):
                    self._err("P408",
                              f"if 조건은 Bool 이어야 하는데 {_base(actual)} 입니다.",
                              condition.line or n.line,
                              "비교식이나 true/false 값을 사용하세요.")
                self._block(body)
            if n.orelse:
                self._block(n.orelse)
        elif k == "While":
            actual = self.infer(n.cond)
            if _base(actual) not in ("Bool", "Any"):
                self._err("P408",
                          f"while 조건은 Bool 이어야 하는데 {_base(actual)} 입니다.",
                          n.cond.line or n.line,
                          "비교식이나 true/false 값을 사용하세요.")
            self._block(n.body)
        elif k in ("Repeat",):
            if n.var:
                self._set(n.var, "Int")
            self._block(n.body)
        elif k == "ForIn":
            self._set(n.var, "Any")
            self._block(n.body)
        elif k == "TryCatch":
            self._block(n.body)
            if n.name:
                self._set(n.name, "Text")
            self._block(n.handler)
        elif k == "Match":
            for _p, body in n.clauses:
                self._block(body)
            if n.default:
                self._block(n.default)
        elif k in ("TestBlock",):
            self._block(n.body)
        elif k == "Show":
            self.infer(n.value)
        elif k == "ExprStmt":
            self.infer(n.value)
        elif k == "Return":
            if n.value is not None:
                self.infer(n.value)
        elif k == "Assert":
            actual = self.infer(n.test)
            if _base(actual) not in ("Bool", "Any"):
                self._err("P406",
                          f"assert 조건은 Bool 이어야 하는데 {_base(actual)} 입니다.",
                          n.line,
                          "비교식(==, !=, <, > 등)이나 true/false 값을 사용하세요.")
            message = getattr(n, "message", None)
            if message is not None:
                message_type = self.infer(message)
                if _base(message_type) not in ("Text", "Any"):
                    self._err("P407",
                              "assert 실패 설명은 Text 이어야 하는데 "
                              f"{_base(message_type)} 입니다.",
                              n.line,
                              "text(...) 로 설명을 문자로 바꾸세요.")

    def _block(self, body):
        for s in body:
            self.stmt(s)

    def _assign(self, n):
        vt = self.infer(n.value)
        dt = getattr(n, "declared_type", None)
        if dt and not compat(vt, dt):
            self._err("P400",
                      f"'{n.target.id}' 는 {_base(dt)} 로 정했는데 "
                      f"{_base(vt)} 값을 넣었습니다.", n.line,
                      "타입 표기를 고치거나 값을 맞추세요.")
        if n.target.kind == "Name":
            self._set(n.target.id, dt or vt)

    def _fn(self, n):
        self.scopes.append({})
        for p in n.params:
            pname = p[0]
            ptype = p[2] if len(p) > 2 else None
            self._set(pname, ptype or "Any")
        rt = getattr(n, "ret_type", None)
        if n.is_expr_body:
            bt = self.infer(n.body)
            if rt and not compat(bt, rt):
                self._err("P405",
                          f"'{n.name}' 는 {_base(rt)} 를 돌려준다고 했는데 "
                          f"{_base(bt)} 를 돌려줍니다.", n.line)
        else:
            for s in n.body:
                self.stmt(s)
            if rt:
                for r in _returns_in(n.body):
                    if r.value is None:
                        continue
                    bt = self.infer(r.value)
                    if not compat(bt, rt):
                        self._err("P405",
                                  f"'{n.name}' 는 {_base(rt)} 를 돌려준다고 했는데 "
                                  f"{_base(bt)} 를 돌려줍니다.", r.line)
        self.scopes.pop()


def _returns_in(body):
    """중첩된 if/for/while/try 블록 안의 Return 까지 (안쪽 fn 은 제외)."""
    for s in body or []:
        k = getattr(s, "kind", None)
        if k == "Return":
            yield s
        elif k == "FnDecl":
            continue
        elif k == "If":
            for _c, b in getattr(s, "branches", []):
                yield from _returns_in(b)
            yield from _returns_in(getattr(s, "orelse", None))
        elif k in ("Repeat", "ForIn", "While"):
            yield from _returns_in(getattr(s, "body", None))
        elif k == "TryCatch":
            yield from _returns_in(getattr(s, "body", None))
            yield from _returns_in(getattr(s, "handler", None))
        elif k == "Match":
            for _p, b in getattr(s, "clauses", []):
                yield from _returns_in(b)
            yield from _returns_in(getattr(s, "default", None))


def check(program) -> list[Finding]:
    try:
        return Checker().run(program)
    except Exception as e:  # noqa: BLE001 — 검사기 버그가 실행을 막으면 안 된다
        return [Finding("P499", f"타입 검사 중단: {e}", None, level="warning")]


def render(findings, source: str) -> str:
    from .errors import _source_frame
    out = []
    errs = [f for f in findings if f.level == "error"]
    for f in findings:
        tag = "타입 오류" if f.level == "error" else "타입 경고"
        out.append(f"{tag} {f.code}" + (f"  (줄 {f.line})" if f.line else ""))
        out.append(f"  {f.msg}")
        if source and f.line:
            out.append(_source_frame(source, f.line, None))
        if f.hint:
            out.append(f"  해결: {f.hint}")
        out.append("")
    if not findings:
        out.append("타입 문제 없음.")
    else:
        out.append(f"타입 오류 {len(errs)}개, 경고 {len(findings) - len(errs)}개")
    return "\n".join(out)
