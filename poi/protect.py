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


# ── 디컴파일 (반대 방향) — exe 에서 되찾을 수 있는 만큼 복원 ──────────

_CA_MAGIC = b"MEI\014\013\012\013\016"


def _extract_carchive(path: str) -> dict:
    """PyInstaller onefile exe → { 이름: 원본 바이트 }."""
    import struct
    import zlib
    data = open(path, "rb").read()
    pos = data.rfind(_CA_MAGIC)
    if pos < 0:
        raise ValueError("PyInstaller CArchive 를 못 찾았어요 (PyInstaller exe 가 아닐 수 있음).")
    # cookie: magic(8) + pkglen(I) + toc(I) + toclen(I) + pyvers(I) + [pylibname(64)]
    cookie = data[pos:pos + 88]
    pkg_len, toc_off, toc_len, _pyv = struct.unpack("!IIII", cookie[8:24])
    end = pos + len(_CA_MAGIC) + 4 * 4
    # pylibname 필드(64B) 유무는 버전마다 다름 — TOC 위치를 절대오프셋으로 계산
    pkg_start = (pos + 24 + (64 if data[end:end + 3].isalpha() else 0)) - pkg_len \
        if False else (len(data) - pkg_len if pos >= len(data) - pkg_len else pos + 24 - pkg_len)
    # 더 튼튼하게: 파일 끝에서 pkg_len 만큼 앞이 패키지 시작
    pkg_start = len(data) - pkg_len
    toc_start = pkg_start + toc_off
    toc = data[toc_start:toc_start + toc_len]
    out = {}
    i = 0
    while i + 18 <= len(toc):
        (elen, dpos, dlen, ulen, flag) = struct.unpack("!IIIIB", toc[i:i + 17])
        typecode = toc[i + 17:i + 18].decode("latin-1")
        name = toc[i + 18:i + elen].rstrip(b"\x00").decode("utf-8", "replace")
        raw = data[pkg_start + dpos: pkg_start + dpos + dlen]
        if flag & 1:
            try:
                raw = zlib.decompress(raw)
            except Exception:
                pass
        out[name or f"_e{i}"] = (typecode, raw)
        i += elen
        if elen == 0:
            break
    return out


def _pyc_to_code(raw: bytes):
    """PYSOURCE 엔트리(마셜된 코드) 또는 .pyc → code object."""
    import marshal
    for skip in (0, 16, 12, 8):
        try:
            return marshal.loads(raw[skip:])
        except Exception:
            continue
    raise ValueError("코드 객체를 못 읽었어요.")


def _harvest_source(code, found):
    """co_consts 에서 파이썬 소스처럼 보이는 문자열을 모은다 (재귀)."""
    import types
    for c in getattr(code, "co_consts", ()):
        if isinstance(c, str) and len(c) > 40 and (
                "def " in c or "poi_show" in c or "make_globals" in c
                or "exec(" in c or "\n" in c and "=" in c):
            found.append(c)
        elif isinstance(c, types.CodeType):
            _harvest_source(c, found)


def decompile_exe(exe_path: str, out_dir: str = "decompiled") -> dict:
    """POI/PyInstaller exe 에서 되찾을 수 있는 만큼 복원한다."""
    from .packager import read_package
    import os
    os.makedirs(out_dir, exist_ok=True)
    native = read_package(exe_path)
    if native is not None:
        code, manifest = native
        import dis
        import io
        import json
        clean_manifest = {k: v for k, v in manifest.items() if not k.startswith("_")}
        meta_path = os.path.join(out_dir, "poi-package.json")
        with open(meta_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(clean_manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        saved = [meta_path]
        notes = []
        mode = str(manifest.get("mode", "compiled"))
        if mode == "compiled":
            buf = io.StringIO()
            dis.dis(code, file=buf)
            bytecode_path = os.path.join(out_dir, "_poi_app.bytecode.txt")
            with open(bytecode_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(buf.getvalue())
            saved.append(bytecode_path)
            notes.append("원본 POI 소스는 포함되지 않아 바이트코드 분석본을 저장했습니다.")
        else:
            notes.append(f"보호 방식이 {mode}라 앱 코드는 복원하지 않았습니다.")
        return {"out": out_dir, "files": saved, "notes": notes,
                "entries": 1, "native": True, "mode": mode}
    entries = _extract_carchive(exe_path)
    saved, notes = [], []
    for name, (tc, raw) in entries.items():
        safe = name.replace("/", "_").replace("\\", "_").replace("..", "_") or "entry"
        if tc in ("s", "m", "M"):
            try:
                code = _pyc_to_code(raw)
                src = []
                _harvest_source(code, src)
                if src:
                    body = max(src, key=len)
                    p = os.path.join(out_dir, safe + ".recovered.py")
                    with open(p, "w", encoding="utf-8", newline="\n") as f:
                        f.write(body)
                    saved.append(p)
                    if "_unlock" in body or "make_locked_entry" in body \
                            or "_BLOB" in body:
                        notes.append(f"{name}: 비밀번호 잠금 — 원본 코드는 비번 없이 복원 불가")
                else:
                    p = os.path.join(out_dir, safe + ".marshal")
                    with open(p, "wb") as f:
                        f.write(raw)
                    saved.append(p)
            except Exception as e:  # noqa: BLE001
                notes.append(f"{name}: {e}")
        elif tc in ("x", "b") and not name.endswith((".dll", ".pyd", ".so")):
            p = os.path.join(out_dir, safe)
            with open(p, "wb") as f:
                f.write(raw)
            saved.append(p)
    return {"out": out_dir, "files": saved, "notes": notes,
            "entries": len(entries), "native": False}
