; POI — Inno Setup 설치 마법사 스크립트
; 빌드:  ISCC.exe poi.iss   (Inno Setup 6+ 필요)
; 결과:  Output\poi-setup-<버전>.exe  (진짜 GUI 설치 마법사)
;
; 이 스크립트는 관리자 권한 없이(현재 사용자) 설치한다.
; Python 3.10+ 이 있어야 하며, 없으면 안내 후 python.org 를 연다.

#define AppName "POI"
#define AppVer  "1.18.6"  ; 루트 VERSION과 동일하게 유지
#define AppPub  "siwon2da"
#define AppURL  "https://github.com/siwon2da/POI"
#define AppSite "https://hagora.kr/poi/"

[Setup]
AppId={{A1B2C3D4-POI0-4E5F-9A1B-000000000001}
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher={#AppPub}
AppPublisherURL={#AppURL}
DefaultDirName={localappdata}\Programs\POI
DefaultGroupName=POI
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=poi-setup-{#AppVer}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ChangesEnvironment=yes
UninstallDisplayIcon={app}\poi.ico
SetupIconFile=poi.ico

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "addtopath"; Description: "PATH 에 추가 (터미널에서 'poi' 명령 사용)"; GroupDescription: "연동:"
Name: "assocpoi";  Description: ".poi 파일을 POI 로 열기";                    GroupDescription: "연동:"
Name: "startmenu"; Description: "시작 메뉴에 'POI REPL' 만들기";              GroupDescription: "연동:"

[Files]
Source: "..\poi\*";      DestDir: "{app}\poi";      Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: "__pycache__\*,*.pyc"
Source: "..\examples\*"; DestDir: "{app}\examples"; Flags: recursesubdirs ignoreversion
Source: "..\docs\*";     DestDir: "{app}\docs";     Flags: recursesubdirs ignoreversion
Source: "..\README.md";  DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE";    DestDir: "{app}"; Flags: ignoreversion
Source: "poi.ico";       DestDir: "{app}"; Flags: ignoreversion
Source: "poi_launcher.py"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\POI REPL"; Filename: "{cmd}"; Parameters: "/k ""{app}\poi.cmd"" repl"; WorkingDir: "{app}"; IconFilename: "{app}\poi.ico"; Tasks: startmenu
Name: "{group}\POI 소개 페이지"; Filename: "{#AppSite}"; Tasks: startmenu

[Registry]
; .poi 연결 (현재 사용자)
Root: HKCU; Subkey: "Software\Classes\.poi"; ValueType: string; ValueName: ""; ValueData: "POI.Script"; Tasks: assocpoi; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\POI.Script"; ValueType: string; ValueName: ""; ValueData: "POI 스크립트"; Tasks: assocpoi; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\POI.Script\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\poi.ico"; Tasks: assocpoi
Root: HKCU; Subkey: "Software\Classes\POI.Script\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\poi.cmd"" run ""%1"""; Tasks: assocpoi
; PATH 추가 (현재 사용자) — {app} 를 세미콜론 앞에 붙인다
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{code:AddToPath}"; Tasks: addtopath; Check: NeedsPath

[Run]
Filename: "{app}\poi.cmd"; Parameters: "version"; Flags: runhidden; StatusMsg: "설치 확인 중..."

[Code]
var PyCmd: string;

function DetectPython(): Boolean;
var rc: Integer;
begin
  Result := False;
  if Exec('cmd.exe', '/c py -3 --version', '', SW_HIDE, ewWaitUntilTerminated, rc) and (rc = 0) then
  begin PyCmd := 'py -3'; Result := True; exit; end;
  if Exec('cmd.exe', '/c python --version', '', SW_HIDE, ewWaitUntilTerminated, rc) and (rc = 0) then
  begin PyCmd := 'python'; Result := True; exit; end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not DetectPython() then
  begin
    if MsgBox('POI 는 Python 3.10 이상이 필요합니다. 지금은 찾지 못했습니다.'#13#10 +
             'python.org 다운로드 페이지를 열까요? (설치 시 "Add python.exe to PATH" 체크)',
             mbConfirmation, MB_YESNO) = IDYES then
      ShellExec('open', 'https://www.python.org/downloads/', '', '', SW_SHOW, ewNoWait, ErrorCode);
    Result := False;
  end;
end;

// poi.cmd 를 감지된 파이썬으로 생성
procedure CurStepChanged(CurStep: TSetupStep);
var body: string;
begin
  if CurStep = ssPostInstall then
  begin
    body := '@echo off' + #13#10 + PyCmd + ' -X utf8 "%~dp0poi_launcher.py" %*' + #13#10;
    SaveStringToFile(ExpandConstant('{app}\poi.cmd'), body, False);
  end;
end;

function NeedsPath(): Boolean;
var p: string;
begin
  RegQueryStringValue(HKCU, 'Environment', 'Path', p);
  Result := Pos(LowerCase(ExpandConstant('{app}')), LowerCase(p)) = 0;
end;

function AddToPath(Param: string): string;
var p: string;
begin
  RegQueryStringValue(HKCU, 'Environment', 'Path', p);
  if (p <> '') and (p[Length(p)] <> ';') then p := p + ';';
  Result := p + ExpandConstant('{app}');
end;
