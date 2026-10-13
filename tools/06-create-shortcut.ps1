# Replace the old "Hermes Agent" shortcut with the Hermes workbench shortcut:
# launches the packaged desktop app, beautified custom icon.
# The Chinese name is built from codepoints so this file is encoding-proof.
$ErrorActionPreference = 'Stop'
$desktop = [Environment]::GetFolderPath('Desktop')
$old = Join-Path $desktop 'Hermes Agent.lnk'
$newName = 'Hermes ' + [char]0x5DE5 + [char]0x4F5C + [char]0x53F0 + '.lnk'
$new = Join-Path $desktop $newName

$backupDir = 'C:\Users\<用户名>\Desktop\hermes-agent-main\.build\workbench\replaced-shortcut'
if (Test-Path $old) {
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    Move-Item -Force $old (Join-Path $backupDir 'Hermes Agent.lnk')
    Write-Output "old shortcut moved to $backupDir"
}

$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut($new)
$lnk.TargetPath = 'C:\Users\<用户名>\Desktop\hermes-agent-main\apps\desktop\release\win-unpacked\Hermes.exe'
$lnk.WorkingDirectory = 'C:\Users\<用户名>\Desktop\hermes-agent-main'
$lnk.IconLocation = 'C:\Users\<用户名>\AppData\Local\hermes\icons\hermes-workbench.ico,0'
$lnk.Description = 'Hermes workbench - desktop app to chat with Hermes Agent'
$lnk.Save()

$check = $ws.CreateShortcut($new)
Write-Output ("created : " + $new)
Write-Output ("target  : " + $check.TargetPath)
Write-Output ("workdir : " + $check.WorkingDirectory)
Write-Output ("icon    : " + $check.IconLocation)
Write-Output ("exists  : " + (Test-Path $new))
