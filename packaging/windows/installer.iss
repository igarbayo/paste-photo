; Instalador de paste-photo (Inno Setup 6). Por usuario: no pide permisos de administrador.
; Lo compila packaging/build.py --installer, que pasa:
;   /DAppVersion=0.2.0  /DSourceDir=<dist\paste-photo>  /DRepoRoot=<raíz del repo>
;
; Qué hace:
;   - Copia la app en %LOCALAPPDATA%\Programs\paste-photo
;   - Acceso directo en el menú Inicio (y en el escritorio, opcional)
;   - Tarea "Iniciar con Windows": el mismo valor de registro que el menú de la bandeja
;   - Tarea "Añadir al PATH": para usar `paste-photo-cli` desde una terminal
;   - Cierra la app si está abierta antes de actualizar o desinstalar
;   - El desinstalador quita el inicio automático y la entrada del PATH (la configuración
;     del usuario en %APPDATA%\paste-photo se conserva)

#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif
#ifndef RepoRoot
  #define RepoRoot "..\.."
#endif
#ifndef SourceDir
  #define SourceDir RepoRoot + "\dist\paste-photo"
#endif

#define AppName "paste-photo"
#define AppExe "paste-photo.exe"
#define RunKey "Software\Microsoft\Windows\CurrentVersion\Run"

[Setup]
AppId={{40E6E043-6668-4B34-93FE-C0C101B9CECE}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=igarbayo
AppPublisherURL=https://github.com/igarbayo/paste-photo
AppSupportURL=https://github.com/igarbayo/paste-photo/issues
AppUpdatesURL=https://github.com/igarbayo/paste-photo/releases
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=paste-photo-setup-{#AppVersion}
SetupIconFile={#RepoRoot}\paste_photo\resources\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ChangesEnvironment=yes
CloseApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
spanish.AutoStart=Iniciar paste-photo al iniciar sesión en Windows
english.AutoStart=Start paste-photo when I sign in to Windows
spanish.AddToPath=Añadir paste-photo-cli al PATH (para usarlo desde una terminal)
english.AddToPath=Add paste-photo-cli to PATH (to use it from a terminal)
spanish.Launch=Abrir paste-photo ahora
english.Launch=Open paste-photo now

[Tasks]
Name: "autostart"; Description: "{cm:AutoStart}"
Name: "addtopath"; Description: "{cm:AddToPath}"
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "{#RunKey}"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExe}"""; Tasks: autostart
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Tasks: addtopath; Check: NotInPath(ExpandConstant('{app}'))

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:Launch}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#AppExe}"; Flags: runhidden; RunOnceId: "KillApp"

[Code]
function NotInPath(Dir: string): Boolean;
var
  Path: string;
begin
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', Path) then
    Path := '';
  Result := Pos(';' + Uppercase(Dir) + ';', ';' + Uppercase(Path) + ';') = 0;
end;

procedure RemoveFromPath(Dir: string);
var
  Path: string;
  P: Integer;
begin
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', Path) then
    exit;
  Path := ';' + Path + ';';
  P := Pos(';' + Uppercase(Dir) + ';', Uppercase(Path));
  if P = 0 then
    exit;
  Delete(Path, P, Length(Dir) + 1);
  Path := Copy(Path, 2, Length(Path) - 2);
  RegWriteExpandStringValue(HKCU, 'Environment', 'Path', Path);
end;

// Cierra la app (si está abierta) antes de copiar archivos: si no, el .exe está bloqueado.
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM {#AppExe}', '', SW_HIDE,
       ewWaitUntilTerminated, ResultCode);
  Result := '';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    // El inicio automático puede haberse activado desde la bandeja: se quita siempre.
    RegDeleteValue(HKCU, '{#RunKey}', '{#AppName}');
    RemoveFromPath(ExpandConstant('{app}'));
  end;
end;
