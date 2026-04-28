#define MyAppName "Sovereign Agent"
#define MyAppVersion "30.11.5"
#define MyAppPublisher "TDWAS Technology"
#define MyAppURL "https://tdwas.com"
#define MyAppExeName "SovereignAgent.exe"

[Setup]
AppId={{D86F5C6A-6D84-4B2E-8E3B-A893D3E9E524}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=Sovereign_Agent_Setup_{#MyAppVersion}
OutputDir=dist
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=image\favicon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\SovereignAgent_Portable.exe"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: ignoreversion
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "image\*"; DestDir: "{app}\image"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "VERSION"; DestDir: "{app}"; Flags: ignoreversion
Source: "customtkinter\*"; DestDir: "{app}\customtkinter"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: ".env.example"; DestDir: "{app}"; DestName: ".env"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall
