<#
  POI 설치 스크립트 (Windows, 서명 불필요 · 관리자 권한 불필요)

    powershell -ExecutionPolicy Bypass -File install.ps1

  하는 일:
    · %LOCALAPPDATA%\Programs\POI 에 POI 를 복사
    · poi.cmd 런처 생성
    · 사용자 PATH 에 등록  (새 터미널부터 `poi` 명령 사용 가능)
    · .poi 파일을 더블클릭하면 `poi run` 으로 열리도록 연결 (선택)
#>
[CmdletBinding()]
param(
  [string]$Dest = (Join-Path $env:LOCALAPPDATA 'Programs\POI'),
  [switch]$NoPathUpdate,
  [switch]$NoAssoc,
  [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'
$src = Split-Path -Parent $PSScriptRoot   # repo 루트 (installer\ 의 부모)

function Find-Python {
  foreach ($c in @('py -3','python','python3')) {
    $exe, $rest = $c.Split(' ',2)
    $p = (Get-Command $exe -ErrorAction SilentlyContinue)
    if ($p) {
      try {
        $v = & $exe $rest --version 2>&1
        if ($v -match 'Python 3\.(\d+)') { if ([int]$Matches[1] -ge 10) { return $c } }
      } catch {}
    }
  }
  return $null
}

function Remove-FromUserPath([string]$dir) {
  $cur = [Environment]::GetEnvironmentVariable('Path','User')
  if (-not $cur) { return }
  $parts = $cur.Split(';') | Where-Object { $_ -and ($_.TrimEnd('\') -ne $dir.TrimEnd('\')) }
  [Environment]::SetEnvironmentVariable('Path', ($parts -join ';'), 'User')
}

if ($Uninstall) {
  Write-Host "POI 제거 중: $Dest"
  if (Test-Path $Dest) { Remove-Item -Recurse -Force $Dest }
  Remove-FromUserPath $Dest
  try {
    Remove-Item -Recurse -Force 'HKCU:\Software\Classes\.poi' -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force 'HKCU:\Software\Classes\POI.Script' -ErrorAction SilentlyContinue
  } catch {}
  $sm = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\POI'
  if (Test-Path $sm) { Remove-Item -Recurse -Force $sm }
  Write-Host "완료. 새 터미널에서는 poi 명령이 사라집니다."
  exit 0
}

$py = Find-Python
if (-not $py) {
  Write-Host "[중단] Python 3.10 이상이 필요합니다." -ForegroundColor Red
  Write-Host "       https://www.python.org/downloads/ 에서 설치 후 다시 실행하세요."
  Write-Host "       (설치 시 'Add python.exe to PATH' 체크)"
  exit 1
}
Write-Host "Python 발견: $py"

Write-Host "설치 위치: $Dest"
if (Test-Path $Dest) { Remove-Item -Recurse -Force $Dest }
New-Item -ItemType Directory -Force -Path $Dest | Out-Null

foreach ($item in @('poi','examples','docs','README.md','LICENSE','pyproject.toml')) {
  $p = Join-Path $src $item
  if (Test-Path $p) { Copy-Item -Recurse -Force $p (Join-Path $Dest $item) }
}
Get-ChildItem -Recurse -Directory -Filter '__pycache__' $Dest | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 런처
$launcher = @'
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from poi.cli import main
raise SystemExit(main())
'@
Set-Content -Path (Join-Path $Dest 'poi_launcher.py') -Value $launcher -Encoding UTF8

$cmd = "@echo off`r`n$py -X utf8 `"%~dp0poi_launcher.py`" %*`r`n"
Set-Content -Path (Join-Path $Dest 'poi.cmd') -Value $cmd -Encoding Ascii

# PATH
if (-not $NoPathUpdate) {
  $cur = [Environment]::GetEnvironmentVariable('Path','User')
  if (($cur -split ';' | ForEach-Object { $_.TrimEnd('\') }) -notcontains $Dest.TrimEnd('\')) {
    [Environment]::SetEnvironmentVariable('Path', ($cur.TrimEnd(';') + ';' + $Dest), 'User')
    Write-Host "사용자 PATH 에 추가했습니다."
  } else {
    Write-Host "이미 PATH 에 있습니다."
  }
}

# .poi 연결 (HKCU — 관리자 불필요)
if (-not $NoAssoc) {
  try {
    New-Item -Force 'HKCU:\Software\Classes\.poi' | Out-Null
    Set-ItemProperty 'HKCU:\Software\Classes\.poi' '(default)' 'POI.Script'
    New-Item -Force 'HKCU:\Software\Classes\POI.Script\shell\open\command' | Out-Null
    Set-ItemProperty 'HKCU:\Software\Classes\POI.Script' '(default)' 'POI 스크립트'
    Set-ItemProperty 'HKCU:\Software\Classes\POI.Script\shell\open\command' '(default)' "`"$Dest\poi.cmd`" run `"%1`""
    Write-Host ".poi 파일 연결 완료."
  } catch { Write-Host ".poi 연결은 건너뜀 ($_)" }
}

# 시작 메뉴
$sm = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\POI'
New-Item -ItemType Directory -Force $sm | Out-Null
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut((Join-Path $sm 'POI REPL.lnk'))
$lnk.TargetPath = "$env:WINDIR\System32\cmd.exe"
$lnk.Arguments  = "/k `"$Dest\poi.cmd`" repl"
$lnk.WorkingDirectory = $Dest
$lnk.Save()

Write-Host ""
Write-Host "설치 완료 -> $Dest" -ForegroundColor Green
Write-Host "새 터미널을 열고:  poi version"
Write-Host "               :  poi run `"$Dest\examples\basics.poi`""
Write-Host "제거:  powershell -ExecutionPolicy Bypass -File install.ps1 -Uninstall"
