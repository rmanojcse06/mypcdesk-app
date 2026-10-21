; Inno Setup script for the MyDesk Windows installer.
; Build after PyInstaller:  set MYDESK_VERSION=1.0.0-beta.1  &&  iscc packaging\installer.iss
; Installs for the current user only (no admin prompt). Your settings and data in
; %APPDATA%\MyDesk are kept on update and uninstall.

#define AppVersion GetEnv("MYDESK_VERSION")
#if AppVersion == ""
  #define AppVersion "dev"
#endif

[Setup]
AppId={{6F0B2C1E-7D2B-4C55-9B7E-3A1D5E9C2B41}
AppName=MyDesk
AppVersion={#AppVersion}
AppPublisher=MyDesk
DefaultDirName={localappdata}\Programs\MyDesk
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=MyDesk-Setup-{#AppVersion}
SetupIconFile=..\mydesk\ui\mydesk.ico
UninstallDisplayIcon={app}\MyDesk.exe
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "startup"; Description: "Start MyDesk when I sign in to Windows"; GroupDescription: "Startup:"
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\MyDesk\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\MyDesk"; Filename: "{app}\MyDesk.exe"
Name: "{autodesktop}\MyDesk"; Filename: "{app}\MyDesk.exe"; Tasks: desktopicon
Name: "{userstartup}\MyDesk"; Filename: "{app}\MyDesk.exe"; Tasks: startup

[Run]
Filename: "{app}\MyDesk.exe"; Description: "Open MyDesk now"; Flags: nowait postinstall skipifsilent
