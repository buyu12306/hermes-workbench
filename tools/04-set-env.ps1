# Set the user-scope env var so every launch of the packaged Hermes Desktop
# resolves its backend to this source checkout (rung 1: HERMES_DESKTOP_HERMES_ROOT).
$root = 'C:\Users\<用户名>\Desktop\hermes-agent-main'
[Environment]::SetEnvironmentVariable('HERMES_DESKTOP_HERMES_ROOT', $root, 'User')
$check = [Environment]::GetEnvironmentVariable('HERMES_DESKTOP_HERMES_ROOT', 'User')
Write-Output "HERMES_DESKTOP_HERMES_ROOT(User) = $check"
