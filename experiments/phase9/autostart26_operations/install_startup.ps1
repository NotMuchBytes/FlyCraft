param(
    [Parameter(Mandatory=$true)][string]$Plan
)
$ErrorActionPreference = 'Stop'
$taskPlanPath = (Resolve-Path -LiteralPath $Plan).Path
$taskPlan = Get-Content -LiteralPath $taskPlanPath -Raw | ConvertFrom-Json
$taskRoot = $taskPlan.root
$taskState = $taskPlan.state_dir
$taskLauncher = Join-Path $PSScriptRoot 'bootstrap.py'
$taskPythonw = Join-Path (Split-Path -Parent $taskPlan.python) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $taskPythonw)) { throw 'The installed Python environment has no pythonw.exe; startup was not replaced.' }
$taskArguments = '"' + $taskLauncher + '" --plan "' + $taskPlanPath + '"'
$taskName = 'FlyCraft_AutoResume_20261126'
$taskRegistration = 'not_registered'
$taskRegistrationError = $null
New-Item -ItemType Directory -Path $taskState -Force | Out-Null
try {
    $taskAction = New-ScheduledTaskAction -Execute $taskPythonw -Argument $taskArguments -WorkingDirectory $taskRoot
    $taskTrigger = New-ScheduledTaskTrigger -AtLogOn -User ([Security.Principal.WindowsIdentity]::GetCurrent().Name)
    $taskPrincipal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
    $taskSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    $taskExisting = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($taskExisting -and -not ($taskExisting.Actions.Arguments -like ('*' + $PSScriptRoot + '*'))) { throw 'An unrelated task uses this name; it was not replaced.' }
    Register-ScheduledTask -TaskName $taskName -Action $taskAction -Trigger $taskTrigger -Principal $taskPrincipal -Settings $taskSettings -Description 'Resume the authorized FlyCraft campaign after sign-in; preserve checkpoints, STOP and quality gates.' -Force | Out-Null
    $taskRegistration = 'registered'
} catch {
    $taskRegistrationError = $_.Exception.Message
}
# Independent per-user startup fallback; both launch paths use the same OS lease.
$taskStartup = [Environment]::GetFolderPath('Startup')
$taskShortcutPath = Join-Path $taskStartup 'FlyCraft Auto Resume.lnk'
$taskShell = New-Object -ComObject WScript.Shell
$taskShortcut = $taskShell.CreateShortcut($taskShortcutPath)
$taskShortcut.TargetPath = $taskPythonw
$taskShortcut.Arguments = $taskArguments
$taskShortcut.WorkingDirectory = $taskRoot
$taskShortcut.WindowStyle = 7
$taskShortcut.Description = 'Resume FlyCraft in the background after signing in'
$taskShortcut.Save()
$taskProof = [ordered]@{ task_name=$taskName; task_registration=$taskRegistration; task_error=$taskRegistrationError; startup_shortcut=$taskShortcutPath; target=$taskPythonw; arguments=$taskArguments; trigger='user_sign_in'; pre_login_boot_installed=$false; installed_utc=[DateTime]::UtcNow.ToString('o') }
$taskProof | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskState 'installation.json') -Encoding utf8
$taskProof | ConvertTo-Json -Depth 5
