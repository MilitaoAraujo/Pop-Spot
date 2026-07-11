; Script do Inno Setup para gerar o instalador PopSpot-Setup.exe
; Compilar com: iscc setup.iss  (ou via CI no GitHub Actions)

#define AppName    "Pop-Spot"
#define AppVersion "1.0.0"
#define AppExe     "PopSpot.exe"
#define AppPublisher "MilitaoAraujo"
#define AppURL     "https://github.com/MilitaoAraujo/Pop-Spot"

[Setup]
AppId={{A3F1C2D4-7B8E-4F2A-9C3D-1E5F6A7B8C9D}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}/releases

; Instala em AppData do usuario — nao precisa de administrador
DefaultDirName={localappdata}\PopSpot
DefaultGroupName={#AppName}
OutputDir=dist
OutputBaseFilename=PopSpot-Setup
SetupIconFile=

; Visual
WizardStyle=modern
WizardResizable=no
DisableDirPage=yes
DisableProgramGroupPage=yes
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ShowLanguageDialog=no

; Desinstalacao
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}
CreateUninstallRegKey=yes

[Languages]
Name: "ptbr";    MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; \
  Description: "Criar atalho na Área de Trabalho"; \
  GroupDescription: "Atalhos adicionais:"

Name: "autostart"; \
  Description: "Iniciar o Pop-Spot automaticamente com o Windows"; \
  GroupDescription: "Atalhos adicionais:"; \
  Flags: unchecked

[Files]
; Copia o bundle gerado pelo PyInstaller
Source: "dist\PopSpot\*"; \
  DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Menu Iniciar do usuario atual (nao requer admin)
Name: "{userprograms}\{#AppName}";          Filename: "{app}\{#AppExe}"
Name: "{userprograms}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"

; Area de Trabalho do usuario atual (nao requer admin)
Name: "{userdesktop}\{#AppName}";  Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; Iniciar com o Windows (opcional, via chave Run do usuário)
Root: HKCU; \
  Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; \
  ValueName: "PopSpot"; \
  ValueData: """{app}\{#AppExe}"""; \
  Flags: uninsdeletevalue; \
  Tasks: autostart

[Run]
; Oferece abrir o widget ao final da instalacao
Filename: "{app}\{#AppExe}"; \
  Description: "Abrir o Pop-Spot agora"; \
  Flags: nowait postinstall skipifsilent
