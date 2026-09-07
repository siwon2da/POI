<#
  POI — 한 줄 설치 (Windows, 관리자 권한 불필요, 파이썬 불필요)

    powershell -c "irm https://hagora.kr/poi/install.ps1 | iex"

  하는 일:  poi.exe 를 받아 %LOCALAPPDATA%\Programs\POI 에 넣고
            PATH 등록 + .poi 연결 + 시작 메뉴 항목.
  제거:     poi __uninstall__
#>
$ErrorActionPreference = 'Stop'
$base = 'https://hagora.kr/poi'
$dest = Join-Path $env:LOCALAPPDATA 'Programs\POI'
$exe  = Join-Path $dest 'poi.exe'

Write-Host "POI 설치를 시작합니다 -> $dest" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $dest | Out-Null

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
} catch {}

Write-Host "poi.exe 내려받는 중..."
Invoke-WebRequest -Uri "$base/poi.exe" -OutFile $exe -UseBasicParsing

Unblock-File $exe -ErrorAction SilentlyContinue

Write-Host "설치 구성 중..."
& $exe __install__ --dir $dest @args

Write-Host ""
Write-Host "끝났습니다. 새 터미널을 열고:  poi version" -ForegroundColor Green
Write-Host "입문서: https://hagora.kr/poi/book/"
