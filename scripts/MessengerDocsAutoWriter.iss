#define MyAppName GetEnv("MDAW_APP_NAME")
#define MyAppVersion GetEnv("MDAW_APP_VERSION")
#define MySourceDir GetEnv("MDAW_SOURCE_DIR")
#define MyOutputDir GetEnv("MDAW_OUTPUT_DIR")
#define MyOutputBaseFilename GetEnv("MDAW_OUTPUT_BASE_FILENAME")

[Setup]
AppId={{80D7F3C5-75FD-48F6-B542-3F20BC8E6E6C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=122yjs
AppPublisherURL=https://github.com/122yjs/auto_write_txt_to_docs
AppSupportURL=https://github.com/122yjs/auto_write_txt_to_docs/issues
AppUpdatesURL=https://github.com/122yjs/auto_write_txt_to_docs/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#MyOutputDir}
OutputBaseFilename={#MyOutputBaseFilename}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppName}.exe

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppName}.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppName}.exe"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
