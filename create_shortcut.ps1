# PowerShell script to create Desktop Shortcut for AI-DeFi Risk Intelligence v2
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$Target = Join-Path $PSScriptRoot "Run_Project.bat"
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "AI-DeFi Risk Intelligence v2.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Target
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.Description = "AI-DeFi Risk Intelligence v2 Platform"
$Shortcut.Save()

Write-Host "✅ Desktop shortcut created successfully at: $ShortcutPath"
