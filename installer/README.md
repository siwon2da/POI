# POI 설치

## 방법 A — 설치 마법사 (.exe, 파이썬 불필요)

hagora.kr/poi/ 에서 **poi-setup-1.18.3.exe** 를 받아 더블클릭.
창에서 다음 → (옵션 선택) → 설치 → 닫기.

## 방법 B — 명령 한 줄 (PowerShell)

```powershell
powershell -c "irm https://hagora.kr/poi/install.ps1 | iex"
```

poi.exe 를 받아 `%LOCALAPPDATA%\Programs\POI` 에 넣고 PATH·.poi 연결·시작 메뉴까지.

## 방법 C — 포터블 (poi.exe 하나)

```powershell
curl -o poi.exe https://hagora.kr/poi/poi.exe
.\poi.exe __install__            # 설치 (--no-path / --no-assoc / --no-startmenu 옵션)
.\poi.exe run 파일.poi           # 설치 없이 그냥 실행
```

## 방법 D — 저장소 (파이썬 3.10+)

```bash
git clone https://github.com/siwon2da/POI.git
cd POI
python -m poi run examples/basics.poi
pip install -e .        # poi 명령 등록
```

## 제거

```powershell
poi __uninstall__       # PATH·연결·시작메뉴·제어판 항목 제거 (폴더는 직접 삭제)
```

## 직접 빌드

- `.exe` (PyInstaller):  `python installer/build_exe.py`
- Inno Setup 설치 마법사:  `ISCC installer/poi.iss`  (Inno Setup 6+)
- 명령줄 스크립트 설치:  `powershell -ExecutionPolicy Bypass -File installer/install.ps1`
