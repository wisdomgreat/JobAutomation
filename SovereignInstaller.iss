; --- Sovereign Agent Professional Installer Script ---
; Generated for TDWAS Technology
; website: tdwas.com

#define MyAppName "Sovereign Agent"
#define MyAppVersion "25.0"
#define MyAppPublisher "TDWAS Technology"
#define MyAppURL "https://tdwas.com"
#define MyAppExeName "SovereignAgent.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
AppId={{D37F2A28-4E8E-4A42-B9E4-D16A42CEB3F1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Standard Professional Location
DefaultDirName={autopf}\{#MyAppName}
ChangesAssociations=yes
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
SetupIconFile=image\favicon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
OutputDir=dist
OutputBaseFilename=Sovereign_Agent_Setup_v25

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Packages the entire directory structure from build.py --onedir
Source: "dist\SovereignAgent\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; NOTE: We preserve the user's permanent identity in AppData/Roaming manually.
; Only deleting the software files from Program Files.
Type: filesandordirs; Name: "{app}"
