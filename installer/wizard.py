# -*- coding: utf-8 -*-
"""POI 설치 마법사 (Windows GUI).

PyInstaller 로 poi-setup-<버전>.exe 로 묶는다. poi.exe 를 payload 로 동봉한다.
관리자 권한 불필요 — 현재 사용자(%LOCALAPPDATA%)에 설치.
"""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk

APP = "POI"
VERSION = "1.2.0"
BLUE = "#3182F6"
INK = "#191F28"
BG = "#FFFFFF"
SOFT = "#F2F4F6"


def _res(name: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def broadcast_env_change():
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x1A
    SMTO_ABORTIFHUNG = 0x0002
    res = ctypes.c_ulong()
    ctypes.windll.user32.SendMessageTimeoutW(
        HWND_BROADCAST, WM_SETTINGCHANGE, 0, ctypes.c_wchar_p("Environment"),
        SMTO_ABORTIFHUNG, 3000, ctypes.byref(res))


def add_to_path(target: str):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                        winreg.KEY_READ | winreg.KEY_WRITE) as k:
        try:
            cur, _ = winreg.QueryValueEx(k, "Path")
        except FileNotFoundError:
            cur = ""
        parts = [p for p in cur.split(";") if p]
        if target.rstrip("\\").lower() not in (p.rstrip("\\").lower() for p in parts):
            parts.append(target)
            winreg.SetValueEx(k, "Path", 0, winreg.REG_EXPAND_SZ, ";".join(parts))
    broadcast_env_change()


def remove_from_path(target: str):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                            winreg.KEY_READ | winreg.KEY_WRITE) as k:
            cur, _ = winreg.QueryValueEx(k, "Path")
            parts = [p for p in cur.split(";")
                     if p and p.rstrip("\\").lower() != target.rstrip("\\").lower()]
            winreg.SetValueEx(k, "Path", 0, winreg.REG_EXPAND_SZ, ";".join(parts))
        broadcast_env_change()
    except FileNotFoundError:
        pass


def assoc_poi(exe: str):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.poi") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "POI.Script")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\POI.Script") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "POI 스크립트")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                          r"Software\Classes\POI.Script\shell\open\command") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f'"{exe}" run "%1"')


def start_menu_shortcut(exe: str, folder: str):
    sm = os.path.join(os.environ["APPDATA"],
                      r"Microsoft\Windows\Start Menu\Programs\POI")
    os.makedirs(sm, exist_ok=True)
    lnk = os.path.join(sm, "POI REPL.lnk").replace("\\", "\\\\")
    ps = (
        f'$w = New-Object -ComObject WScript.Shell; '
        f'$s = $w.CreateShortcut("{lnk}"); '
        f'$s.TargetPath = "$env:WINDIR\\system32\\cmd.exe"; '
        f'$s.Arguments = \'/k \"\"{exe}\" repl\"\'; '
        f'$s.WorkingDirectory = "{folder}"; '
        f'$s.IconLocation = "{exe},0"; $s.Save()'
    )
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                   capture_output=True, creationflags=0x08000000)


def do_install(dest: str, opts: dict, log):
    exe_src = _res("poi.exe")
    os.makedirs(dest, exist_ok=True)
    log(f"설치 위치: {dest}")

    exe_dst = os.path.join(dest, "poi.exe")
    shutil.copy2(exe_src, exe_dst)
    log("poi.exe 복사 완료")

    for extra in ("examples", "README.md", "LICENSE"):
        src = _res(extra)
        if os.path.exists(src):
            dst = os.path.join(dest, extra)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            log(f"{extra} 복사")

    if opts["path"]:
        add_to_path(dest)
        log("사용자 PATH 에 추가 (새 터미널부터 'poi' 사용 가능)")
    if opts["assoc"]:
        assoc_poi(exe_dst)
        log(".poi 파일을 POI 로 열도록 연결")
    if opts["startmenu"]:
        start_menu_shortcut(exe_dst, dest)
        log("시작 메뉴에 'POI REPL' 추가")

    # 제거 정보
    try:
        import winreg
        key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\POI"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
            winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, f"POI {VERSION}")
            winreg.SetValueEx(k, "DisplayVersion", 0, winreg.REG_SZ, VERSION)
            winreg.SetValueEx(k, "Publisher", 0, winreg.REG_SZ, "siwon2da")
            winreg.SetValueEx(k, "InstallLocation", 0, winreg.REG_SZ, dest)
            winreg.SetValueEx(k, "DisplayIcon", 0, winreg.REG_SZ, exe_dst)
            winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ,
                              f'"{exe_dst}" __uninstall__')
    except Exception as e:  # noqa: BLE001
        log(f"(제거 정보 등록 건너뜀: {e})")

    log("")
    log("설치 완료. 새 터미널을 열고  poi version  을 쳐보세요.")


class Wizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"POI {VERSION} 설치")
        self.configure(bg=BG)
        self.geometry("560x420")
        self.resizable(False, False)
        try:
            self.iconbitmap(_res("poi.ico"))
        except Exception:
            pass
        self.dest = tk.StringVar(
            value=os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "POI"))
        self.opt_path = tk.BooleanVar(value=True)
        self.opt_assoc = tk.BooleanVar(value=True)
        self.opt_sm = tk.BooleanVar(value=True)
        self.frames = {}
        self._build()
        self.show("welcome")

    def _hdr(self, parent, text):
        tk.Label(parent, text=text, bg=BG, fg=INK,
                 font=("Malgun Gothic", 16, "bold")).pack(anchor="w", pady=(28, 4),
                                                          padx=32)

    def _build(self):
        # welcome
        f = tk.Frame(self, bg=BG)
        tk.Label(f, text="P O I", bg=BG, fg=BLUE,
                 font=("Consolas", 40, "bold")).pack(pady=(56, 6))
        tk.Label(f, text="Power Of Imagination", bg=BG, fg="#8B95A1",
                 font=("Malgun Gothic", 11)).pack()
        tk.Label(f, text=f"버전 {VERSION}", bg=BG, fg="#8B95A1",
                 font=("Malgun Gothic", 9)).pack(pady=(2, 24))
        tk.Label(f, text="POI 를 이 컴퓨터에 설치합니다.\n관리자 권한은 필요하지 않습니다.",
                 bg=BG, fg=INK, font=("Malgun Gothic", 10), justify="center").pack()
        self.frames["welcome"] = f

        # options
        f = tk.Frame(self, bg=BG)
        self._hdr(f, "설치 옵션")
        box = tk.Frame(f, bg=BG)
        box.pack(fill="x", padx=32, pady=8)
        tk.Label(box, text="설치 위치", bg=BG, fg="#4E5968",
                 font=("Malgun Gothic", 9)).pack(anchor="w")
        row = tk.Frame(box, bg=BG)
        row.pack(fill="x", pady=(2, 16))
        tk.Entry(row, textvariable=self.dest, font=("Consolas", 9)).pack(
            side="left", fill="x", expand=True, ipady=4)
        for var, label in ((self.opt_path, "PATH 에 추가 (터미널에서 'poi' 명령 사용)"),
                           (self.opt_assoc, ".poi 파일을 POI 로 열기"),
                           (self.opt_sm, "시작 메뉴에 'POI REPL' 만들기")):
            tk.Checkbutton(box, text=label, variable=var, bg=BG, fg=INK,
                           activebackground=BG, font=("Malgun Gothic", 10),
                           anchor="w").pack(anchor="w", pady=3)
        self.frames["options"] = f

        # progress
        f = tk.Frame(self, bg=BG)
        self._hdr(f, "설치 중")
        self.pb = ttk.Progressbar(f, mode="indeterminate")
        self.pb.pack(fill="x", padx=32, pady=(4, 10))
        self.logbox = tk.Text(f, height=12, bg=SOFT, fg=INK, relief="flat",
                              font=("Consolas", 9), wrap="word")
        self.logbox.pack(fill="both", expand=True, padx=32, pady=(0, 8))
        self.frames["progress"] = f

        # finish
        f = tk.Frame(self, bg=BG)
        tk.Label(f, text="✓", bg=BG, fg=BLUE,
                 font=("Segoe UI", 44, "bold")).pack(pady=(56, 6))
        tk.Label(f, text="POI 가 설치되었습니다", bg=BG, fg=INK,
                 font=("Malgun Gothic", 15, "bold")).pack()
        tk.Label(f, text="새 터미널을 열고  poi version  을 실행해 보세요.\n"
                         "입문서: https://hagora.kr/poi/book/",
                 bg=BG, fg="#4E5968", font=("Malgun Gothic", 10),
                 justify="center").pack(pady=(8, 0))
        self.frames["finish"] = f

        # nav bar
        self.nav = tk.Frame(self, bg=SOFT, height=56)
        self.nav.pack(side="bottom", fill="x")
        self.btn_next = tk.Button(self.nav, text="다음", width=12, bg=BLUE, fg="white",
                                  relief="flat", font=("Malgun Gothic", 10, "bold"),
                                  command=self._next, cursor="hand2")
        self.btn_next.pack(side="right", padx=(6, 20), pady=12)
        self.btn_cancel = tk.Button(self.nav, text="취소", width=10, bg=SOFT,
                                    fg="#4E5968", relief="flat",
                                    font=("Malgun Gothic", 10), command=self.destroy,
                                    cursor="hand2")
        self.btn_cancel.pack(side="right", pady=12)

    def show(self, name):
        for fr in self.frames.values():
            fr.pack_forget()
        self.frames[name].pack(side="top", fill="both", expand=True)
        self.state = name
        if name == "welcome":
            self.btn_next.config(text="다음", state="normal")
        elif name == "options":
            self.btn_next.config(text="설치", state="normal")
        elif name == "progress":
            self.btn_next.config(state="disabled")
            self.btn_cancel.config(state="disabled")
        elif name == "finish":
            self.btn_next.config(text="닫기", state="normal", command=self.destroy)
            self.btn_cancel.pack_forget()

    def _next(self):
        if self.state == "welcome":
            self.show("options")
        elif self.state == "options":
            self.show("progress")
            self.pb.start(12)
            threading.Thread(target=self._run_install, daemon=True).start()

    def _log(self, msg):
        self.logbox.insert("end", msg + "\n")
        self.logbox.see("end")
        self.update_idletasks()

    def _run_install(self):
        try:
            do_install(self.dest.get().strip(), {
                "path": self.opt_path.get(),
                "assoc": self.opt_assoc.get(),
                "startmenu": self.opt_sm.get(),
            }, self._log)
        except Exception as e:  # noqa: BLE001
            self._log("")
            self._log(f"[오류] {e}")
            self.btn_cancel.config(state="normal", text="닫기")
            self.pb.stop()
            return
        self.pb.stop()
        self.after(400, lambda: self.show("finish"))


def uninstall():
    dest = os.path.dirname(os.path.abspath(sys.executable))
    remove_from_path(dest)
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
    print("POI 제거됨. 이 폴더는 직접 지우세요:", dest)


if __name__ == "__main__":
    if "__uninstall__" in sys.argv:
        uninstall()
    else:
        Wizard().mainloop()
