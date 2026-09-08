"""소스 보호 — 난독화 · 잠금 (1.9.9).

`poi build` 가 쓴다:
  --obfuscate            트랜스파일된 파이썬을 이름 치환·문자열 인코딩·marshal 로 감싼다
  --lock <비번>          코드 객체를 비번으로 암호화. exe 는 그 비번이 있어야 실행
  --ask-password         --lock 인데 비번을 exe 안에 안 넣음 → 실행할 때 물어봄

주의: PyInstaller exe 는 원리적으로 완전 방어가 안 된다. 난독화는 "쉽게 못 읽게",
잠금(--lock --ask-password)은 비번을 모르면 코드가 안 풀리게 하는 게 목적이다.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import marshal
import os
import re
import secrets
import zlib

_KEEP = {
    # 런타임 전역 — 절대 이름 바꾸면 안 됨
    "Box", "boxify", "poi_show", "poi_print", "poi_fmt", "poi_ask", "number",
    "text", "boolean", "poi_getattr", "poi_getattr_safe", "poi_setattr",
    "poi_coalesce", "poi_error_value", "poi_import_pyfile", "poi_import_module",
    "poi_import_pkg", "poi_std", "poi_make_error", "poi_assert",
    "poi_register_test", "poi_run_tests", "poi_range", "poi_error_is",
    "poi_range", "inspect", "pause", "watch", "_poi_trace", "render", "respond",
    "redirect", "html", "cookie", "session", "auth", "on_request", "on_response",
    "database", "task", "http", "net", "ai", "uikit", "scene3d", "game",
    "__name__", "__poi_dir__", "__poi_file__", "__poi_source__", "__poi_linemap__",
    "__poi_has_web__", "__poi_exports__", "poi_argv", "self", "cls",
}
_PY_BUILTINS = set(dir(__import__("builtins")))


class _Renamer(ast.NodeTransformer):
    def __init__(self):
        self.map: dict[str, str] = {}

    def _n(self, name: str) -> str:
        if (name in _KEEP or name in _PY_BUILTINS or name.startswith("__")
                or name.startswith("_route") or name.startswith("_page")
                or name.startswith("_act") or name.startswith("_poi")):
            return name
        if name not in self.map:
            self.map[name] = "l" + hashlib.blake2b(
                name.encode(), digest_size=6).hexdigest()
        return self.map[name]

    def visit_Name(self, node):
        node.id = self._n(node.id)
        return node

    def visit_FunctionDef(self, node):
        node.name = self._n(node.name)
        # docstring 제거
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            node.body = node.body[1:] or [ast.Pass()]
        self.generic_visit(node)   # 인자·본문은 visit_arg / visit_Name 이 처리
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_arg(self, node):
        node.arg = self._n(node.arg)
        return node


def obfuscate_py(src: str) -> str:
    """트랜스파일된 파이썬 소스를 난독화한다 (문법은 유지)."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return src
    tree = _Renamer().visit(tree)
    ast.fix_missing_locations(tree)
    try:
        import astor  # 선택
        flat = astor.to_source(tree)
    except Exception:
        flat = ast.unparse(tree)
    # marshal + zlib + base64 로 한 겹 더
    code = compile(flat, "<poi>", "exec")
    blob = base64.b85encode(zlib.compress(marshal.dumps(code), 9)).decode()
    chunks = "\n".join('_b += "%s"' % blob[i:i + 120]
                       for i in range(0, len(blob), 120))
    return (
        "import base64 as _a, zlib as _z, marshal as _m\n"
        "_b = ''\n" + chunks + "\n"
        "exec(_m.loads(_z.decompress(_a.b85decode(_b))))\n"
    )


# ── 잠금 (비밀번호) ──────────────────────────────────────────────────

def _keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(8, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def lock_code(code_obj, password: str) -> bytes:
    """코드 객체 → 암호화된 blob (salt|iters|ct).  cryptography 있으면 Fernet."""
    raw = zlib.compress(marshal.dumps(code_obj), 9)
    salt = secrets.token_bytes(16)
    iters = 200_000
    try:
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(
            hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iters))
        ct = Fernet(key).encrypt(raw)
        tag = b"F1"
    except Exception:
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iters, 32)
        ks = _keystream(key, len(raw))
        ct = bytes(a ^ b for a, b in zip(raw, ks))
        mac = hashlib.sha256(key + ct).digest()[:16]
        ct = mac + ct
        tag = b"X1"
    return tag + salt + iters.to_bytes(4, "big") + ct


def unlock_code(blob: bytes, password: str):
    tag, blob = blob[:2], blob[2:]
    salt, blob = blob[:16], blob[16:]
    iters = int.from_bytes(blob[:4], "big")
    ct = blob[4:]
    if tag == b"F1":
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(
            hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iters))
        raw = Fernet(key).decrypt(ct)
    else:
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iters, 32)
        mac, ct = ct[:16], ct[16:]
        if hashlib.sha256(key + ct).digest()[:16] != mac:
            raise ValueError("비밀번호가 틀립니다.")
        ks = _keystream(key, len(ct))
        raw = bytes(a ^ b for a, b in zip(ct, ks))
    return marshal.loads(zlib.decompress(raw))


_LOADER = '''\
# -*- coding: utf-8 -*-
import base64 as _b64, sys as _sys
from poi.protect import unlock_code as _unlock
_BLOB = _b64.b85decode("""__BLOB__""")
__EMBED_PW__
def _main():
    pw = _EMBED_PW
    if pw is None:
        try:
            import getpass
            pw = getpass.getpass("비밀번호: ")
        except Exception:
            pw = input("비밀번호: ")
    try:
        code = _unlock(_BLOB, pw)
    except Exception:
        print("비밀번호가 틀렸거나 파일이 손상됐습니다.", file=_sys.stderr)
        _sys.exit(1)
    g = {"__name__": "__main__"}
    exec(code, g)
if __name__ == "__main__":
    _main()
'''


def make_locked_entry(code_obj, password: str, embed: bool) -> str:
    """--lock 용 엔트리 소스. embed=False 면 실행 시 비번을 묻는다."""
    blob = base64.b85encode(lock_code(code_obj, password)).decode()
    if embed:
        stash = base64.b85encode(
            bytes(a ^ b for a, b in
                  zip(password.encode(), _keystream(b"poi-embed", len(password.encode()))))
        ).decode()
        pw_line = (
            'import base64 as __e\n'
            'from poi.protect import _keystream as __k\n'
            '__s = __e.b85decode("%s")\n'
            '_EMBED_PW = bytes(a ^ b for a, b in zip(__s, __k(b"poi-embed", len(__s)))).decode()\n'
            % stash)
    else:
        pw_line = "_EMBED_PW = None\n"
    src = _LOADER.replace("__BLOB__", "\\\n".join(
        blob[i:i + 200] for i in range(0, len(blob), 200)))
    src = src.replace("__EMBED_PW__", pw_line)
    return src
