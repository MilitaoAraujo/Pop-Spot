Option Explicit
Dim shell, fso, dir, python, cmd

Set shell = WScript.CreateObject("WScript.Shell")
Set fso   = CreateObject("Scripting.FileSystemObject")

' Diretório onde este arquivo .vbs está (= pasta do projeto)
dir = fso.GetParentFolderName(WScript.ScriptFullName)

' Procura o Python do MSYS2. Testa os caminhos mais comuns.
' Se nenhum existir, usa "pythonw" do PATH do sistema (conda, etc.)
Dim cand(2)
cand(0) = "C:\msys64\mingw64\bin\python.exe"
cand(1) = "C:\msys2\mingw64\bin\python.exe"
cand(2) = "pythonw"

Dim i
python = cand(2)
For i = 0 To 1
    If fso.FileExists(cand(i)) Then
        python = cand(i)
        Exit For
    End If
Next

' windowStyle=0 → sem janela de console; bWaitOnReturn=False → não bloqueia
cmd = """" & python & """ """ & dir & "\main.py"""
shell.Run cmd, 0, False
