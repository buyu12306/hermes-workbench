# Read targets of the agent-related desktop shortcuts.
$sh = New-Object -ComObject WScript.Shell
Get-ChildItem ([Environment]::GetFolderPath('Desktop')) -Filter '*.lnk' |
    Where-Object { $_.Name -match 'Claude|DeepSeek|Qoder|Trae|WorkBuddy' } |
    ForEach-Object {
        $l = $sh.CreateShortcut($_.FullName)
        Write-Output ('== ' + $_.Name)
        Write-Output ('   target : ' + $l.TargetPath)
        Write-Output ('   args   : ' + $l.Arguments)
        Write-Output ('   workdir: ' + $l.WorkingDirectory)
    }
