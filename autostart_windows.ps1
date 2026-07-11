# Configura ou remove o início automático do Pop-Spot no Windows.
# Usa o Agendador de Tarefas (Task Scheduler) — não precisa de administrador.
#
# Uso:
#   Ativar  → clique com botão direito > "Executar com PowerShell"
#             ou no terminal: .\autostart_windows.ps1
#
#   Desativar → .\autostart_windows.ps1 -Remover

param([switch]$Remover)

$taskName = "PopSpot"
$launcher = Join-Path $PSScriptRoot "iniciar.vbs"

if ($Remover) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "Pop-Spot removido do inicio automatico." -ForegroundColor Yellow
} else {
    if (-not (Test-Path $launcher)) {
        Write-Host "Erro: iniciar.vbs nao encontrado em $PSScriptRoot" -ForegroundColor Red
        exit 1
    }

    # Acao: rodar o VBS com wscript (sem janela de console)
    $action = New-ScheduledTaskAction `
        -Execute  "wscript.exe" `
        -Argument "`"$launcher`""

    # Gatilho: ao fazer login, com 10 s de espera para o desktop carregar
    $trigger = New-ScheduledTaskTrigger -AtLogon
    $trigger.Delay = "PT10S"

    # Configuracoes: sem limite de tempo, roda com bateria, nao reinicia automaticamente
    $settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit    0 `
        -AllowStartIfOnBatteries $true `
        -DisallowStartIfOnBatteries $false

    Register-ScheduledTask `
        -TaskName  $taskName `
        -Action    $action `
        -Trigger   $trigger `
        -Settings  $settings `
        -RunLevel  Limited `
        -Force | Out-Null

    Write-Host ""
    Write-Host "Pop-Spot configurado para iniciar automaticamente!" -ForegroundColor Green
    Write-Host "O widget vai abrir 10 segundos apos o login."
    Write-Host ""
    Write-Host "Para desativar: .\autostart_windows.ps1 -Remover" -ForegroundColor Gray
}

Write-Host ""
Read-Host "Pressione Enter para fechar"
