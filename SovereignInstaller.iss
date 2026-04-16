; --- Sovereign Agent Professional Installer Script ---
; Generated for TDWAS Technology
; website: tdwas.com

#define MyAppName "Sovereign Agent"
#define MyAppVersion "26.9.0"
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
OutputBaseFilename=Sovereign_Agent_Setup_v26_9_0_8_0_7_0_0_0
PrivilegesRequired=admin

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

; The application files are handled by the standard uninstaller.
; Data cleanup is handled by the [Code] section below.
[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
var
  PurgeCheckBox: TNewCheckBox;

procedure InitializeUninstallProgressForm();
var
  PageText: TNewStaticText;
begin
  // Only add the checkbox if we are in full UI mode
  if not UninstallSilent then
  begin
    PageText := TNewStaticText.Create(UninstallProgressForm);
    PageText.Parent := UninstallProgressForm;
    PageText.Left := ScaleX(20);
    PageText.Top := UninstallProgressForm.ProgressBar.Top + UninstallProgressForm.ProgressBar.Height + ScaleY(15);
    PageText.Width := UninstallProgressForm.ClientWidth - ScaleX(40);
    PageText.Caption := 'Sovereign Intelligence Purge:';
    PageText.Font.Style := [fsBold];

    PurgeCheckBox := TNewCheckBox.Create(UninstallProgressForm);
    PurgeCheckBox.Parent := UninstallProgressForm;
    PurgeCheckBox.Left := ScaleX(20);
    PurgeCheckBox.Top := PageText.Top + ScaleY(20);
    PurgeCheckBox.Width := PageText.Width;
    PurgeCheckBox.Caption := 'Total Purge: Delete all Identity Profile, Resumes, and Application Data';
    PurgeCheckBox.Checked := False;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataPath: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if Assigned(PurgeCheckBox) and PurgeCheckBox.Checked then
    begin
      DataPath := ExpandConstant('{userappdata}\TDWAS\SovereignAgent');
      Log('Starting Total Purge of: ' + DataPath);
      if DirExists(DataPath) then
      begin
        if DelTree(DataPath, True, True, True) then
          Log('Total Purge Successful.')
        else
          Log('Total Purge Failed (Files may be in use).');
      end;
    end;
  end;
end;
