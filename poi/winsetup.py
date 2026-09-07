"""Windows 명령줄 설치 (관리자 권한 불필요).

standalone `poi.exe` 가 자기 자신을 설치한다:

    poi.exe __install__ [--dir <경로>] [--no-path] [--no-assoc] [--no-startmenu]
    poi.exe __uninstall__

한 줄 설치 부트스트랩은 hagora.kr/poi/install.ps1 참고.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

_APP = "POI"


def _default_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Programs", "POI")


def _broadcast_env():
    try:
        import ctypes
        res = ctypes.c_ulong()
        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF, 0x1A, 0, ctypes.c_wchar_p("Environment"), 0x0002, 3000,
            ctypes.byref(res))
    except Exception:
        pass


def _path_add(target: str):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                        winreg.KEY_READ | winreg.KEY_WRITE) as k:
        try:
            cur, _ = winreg.QueryValueEx(k, "Path")
        except FileNotFoundError:
            cur = ""
        parts = [p for p in cur.split(";") if p]
        low = [p.rstrip("\\").lower() for p in parts]
        if target.rstrip("\\").lower() not in low:
            parts.append(target)
            winreg.SetValueEx(k, "Path", 0, winreg.REG_EXPAND_SZ, ";".join(parts))
    _broadcast_env()


def _path_remove(target: str):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                            winreg.KEY_READ | winreg.KEY_WRITE) as k:
            cur, _ = winreg.QueryValueEx(k, "Path")
            parts = [p for p in cur.split(";")
                     if p and p.rstrip("\\").lower() != target.rstrip("\\").lower()]
            winreg.SetValueEx(k, "Path", 0, winreg.REG_EXPAND_SZ, ";".join(parts))
        _broadcast_env()
    except FileNotFoundError:
        pass


def _assoc(exe: str):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.poi") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "POI.Script")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                          r"Software\Classes\POI.Script") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "POI 스크립트")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                          r"Software\Classes\POI.Script\shell\open\command") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f'"{exe}" run "%1"')


def _startmenu(exe: str, folder: str):
    sm = os.path.join(os.environ.get("APPDATA", ""),
                      r"Microsoft\Windows\Start Menu\Programs\POI")
    os.makedirs(sm, exist_ok=True)
    lnk = os.path.join(sm, "POI REPL.lnk").replace("\\", "\\\\")
    ps = (f'$w=New-Object -ComObject WScript.Shell;$s=$w.CreateShortcut("{lnk}");'
          f'$s.TargetPath="$env:WINDIR\\system32\\cmd.exe";'
          f"$s.Arguments='/k \"\"{exe}\" repl\"';"
          f'$s.WorkingDirectory="{folder}";$s.IconLocation="{exe},0";$s.Save()')
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                   capture_output=True, creationflags=0x08000000)


def _uninstall_reg(exe: str, dest: str, version: str):
    import winreg
    key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\POI"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
        winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, f"POI {version}")
        winreg.SetValueEx(k, "DisplayVersion", 0, winreg.REG_SZ, version)
        winreg.SetValueEx(k, "Publisher", 0, winreg.REG_SZ, "siwon2da")
        winreg.SetValueEx(k, "InstallLocation", 0, winreg.REG_SZ, dest)
        winreg.SetValueEx(k, "DisplayIcon", 0, winreg.REG_SZ, exe)
        winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ,
                          f'"{exe}" __uninstall__')


def install(argv: list[str]) -> int:
    if os.name != "nt":
        print("이 명령은 Windows 전용입니다. 다른 OS 는 저장소를 받아 쓰세요.")
        return 1
    from . import __version__

    dest = _default_dir()
    do_path = do_assoc = do_sm = True
    it = iter(argv)
    for a in it:
        if a == "--dir":
            dest = os.path.abspath(next(it, dest))
        elif a.startswith("--dir="):
            dest = os.path.abspath(a.split("=", 1)[1])
        elif a == "--no-path":
            do_path = False
        elif a == "--no-assoc":
            do_assoc = False
        elif a == "--no-startmenu":
            do_sm = False

    src = os.path.abspath(sys.executable)
    if not getattr(sys, "frozen", False):
        print("이 방식은 standalone poi.exe 에서만 동작합니다.")
        print("소스로 받았다면:  pip install -e .   (또는 python -m poi ...)")
        return 1

    os.makedirs(dest, exist_ok=True)
    exe_dst = os.path.join(dest, "poi.exe")
    if os.path.abspath(src) != os.path.abspath(exe_dst):
        shutil.copy2(src, exe_dst)
    print(f"설치: {exe_dst}")

    if do_path:
        _path_add(dest)
        print("PATH 등록 (새 터미널부터 'poi' 사용 가능)")
    if do_assoc:
        try:
            _assoc(exe_dst)
            print(".poi 파일 연결")
        except Exception as e:  # noqa: BLE001
            print(f"(.poi 연결 건너뜀: {e})")
    if do_sm:
        try:
            _startmenu(exe_dst, dest)
            print("시작 메뉴에 'POI REPL'")
        except Exception:
            pass
    try:
        _uninstall_reg(exe_dst, dest, __version__)
    except Exception:
        pass

    print()
    print(f"완료. POI {__version__}. 새 터미널에서:  poi version")
    return 0


def uninstall(_argv: list[str]) -> int:
    if os.name != "nt":
        return 1
    dest = os.path.dirname(os.path.abspath(sys.executable))
    _path_remove(dest)
    try:
        import winreg
        for path in (r"Software\Classes\.poi", r"Software\Classes\POI.Script",
                     r"Software\Microsoft\Windows\CurrentVersion\Uninstall\POI"):
            try:
                winreg.DeleteKeyEx(winreg.HKEY_CURRENT_USER, path)
            except OSError:
                pass
    except Exception:
        pass
    sm = os.path.join(os.environ.get("APPDATA", ""),
                      r"Microsoft\Windows\Start Menu\Programs\POI")
    if os.path.isdir(sm):
        shutil.rmtree(sm, ignore_errors=True)
    print("POI 제거됨. 남은 폴더는 직접 지우세요:", dest)
    return 0
