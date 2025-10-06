#define AppName "PixelPad"
#define AppVersion "0.1.0"
#define AppPublisher "PixelPad"
#define DistDir "..\\..\\dist\\PixelPad"
#define LicensePath "..\\..\\LICENSE"
#define OutputDir "installer"

[Setup]
AppId={{A67C695B-34D0-43D9-B3A7-2CF1D6145610}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile={#LicensePath}
OutputDir={#OutputDir}
OutputBaseFilename=PixelPad-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=no
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\PixelPad.exe"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\PixelPad.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PixelPad.exe"; Description: "Launch PixelPad"; Flags: nowait postinstall skipifsilent
