<#
.SYNOPSIS
    Makes a Windows PC start Emkay full screen in Microsoft Edge, ready to listen.

.DESCRIPTION
    Emkay Kiosk helper for Windows (https://github.com/emkay-voice/emkay-kiosk).

    It does three things, and nothing else:
      1. Lets Emkay's address use the microphone and play sound without asking
         (Microsoft Edge policies AudioCaptureAllowedUrls and AutoplayAllowlist).
      2. Starts Emkay as a full-screen Edge app when anyone signs in to this PC
         (a shortcut in the all-users Startup folder).
      3. Keeps the screen and the PC awake while plugged in (power plan settings).

    Run it from an elevated PowerShell (Run as administrator).
    Use -WhatIf to see what it would change, and -Remove to undo steps 1 and 2.

.PARAMETER Url
    Emkay's address. Default: https://app.emkay.ai. Use your Emkay Home's address if you have one.

.PARAMETER Remove
    Removes the policies and the Startup shortcut this script added. Power settings are left as they are.

.EXAMPLE
    .\emkay-kiosk.ps1 -WhatIf
.EXAMPLE
    .\emkay-kiosk.ps1 -Url https://emkay-home.local
.EXAMPLE
    .\emkay-kiosk.ps1 -Remove
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$Url = "https://app.emkay.ai",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

# --- small helpers, Emkay style: one quiet line per step -------------------
$dot = [char]0x25CF; $tick = [char]0x2713
function Step([string]$text) { Write-Host "  " -NoNewline; Write-Host $dot -ForegroundColor Cyan -NoNewline; Write-Host " $text" }
function Done([string]$text) { Write-Host "  " -NoNewline; Write-Host $tick -ForegroundColor Green -NoNewline; Write-Host " $text" }
function Note([string]$text) { Write-Host "    $text" -ForegroundColor DarkGray }

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin -and -not $WhatIfPreference) {
    Write-Host "Please run this from PowerShell opened with 'Run as administrator'." -ForegroundColor Yellow
    exit 1
}

# The policies want an origin (scheme://host[:port]), not a full address.
$uri = [Uri]$Url
$origin = $uri.GetLeftPart([UriPartial]::Authority)

$policyRoot = "HKLM:\SOFTWARE\Policies\Microsoft\Edge"
$lists = @("AudioCaptureAllowedUrls", "AutoplayAllowlist")
$startup = Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs\StartUp\Emkay.lnk"
$edge = @(
    (Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"),
    (Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe")
) | Where-Object { Test-Path $_ } | Select-Object -First 1

# Adds $origin to a list policy (values named 1, 2, 3, ...) without touching other entries.
function Add-OriginToPolicy {
    [CmdletBinding(SupportsShouldProcess)]
    param([string]$name)
    $key = Join-Path $policyRoot $name
    if (-not (Test-Path $key)) {
        if ($PSCmdlet.ShouldProcess($key, "Create policy key")) { New-Item -Path $key -Force | Out-Null }
    }
    $values = if (Test-Path $key) { Get-ItemProperty -Path $key } else { $null }
    $existing = @()
    if ($values) { $existing = $values.PSObject.Properties | Where-Object { $_.Name -match '^\d+$' } }
    if ($existing.Value -contains $origin) { return }
    $next = 1
    if ($existing) { $next = ([int[]]$existing.Name | Measure-Object -Maximum).Maximum + 1 }
    if ($PSCmdlet.ShouldProcess("$key\$next", "Set to $origin")) {
        New-ItemProperty -Path $key -Name "$next" -Value $origin -PropertyType String -Force | Out-Null
    }
}

# Removes $origin from a list policy, leaving other entries alone.
function Clear-OriginFromPolicy {
    [CmdletBinding(SupportsShouldProcess)]
    param([string]$name)
    $key = Join-Path $policyRoot $name
    if (-not (Test-Path $key)) { return }
    $values = Get-ItemProperty -Path $key
    foreach ($p in $values.PSObject.Properties | Where-Object { $_.Name -match '^\d+$' -and $_.Value -eq $origin }) {
        if ($PSCmdlet.ShouldProcess("$key\$($p.Name)", "Remove")) { Remove-ItemProperty -Path $key -Name $p.Name }
    }
}

Write-Host ""
Write-Host "  E M K A Y   K I O S K" -ForegroundColor White
Write-Host "  $origin" -ForegroundColor Cyan
Write-Host ""

if ($Remove) {
    Step "Removing Emkay's microphone and sound permissions in Edge"
    foreach ($l in $lists) { Clear-OriginFromPolicy $l }
    Done "Permissions removed"
    if (Test-Path $startup) {
        if ($PSCmdlet.ShouldProcess($startup, "Remove Startup shortcut")) { Remove-Item $startup }
    }
    Done "Emkay no longer starts when someone signs in"
    Note "Power settings were left as they are (Settings > System > Power)."
    exit 0
}

if (-not $edge) {
    Write-Host "Microsoft Edge was not found. Install it from https://www.microsoft.com/edge and run this again." -ForegroundColor Yellow
    exit 1
}

Step "Letting Emkay use the microphone and play sound without asking"
foreach ($l in $lists) { Add-OriginToPolicy $l }
Done "Edge allows the microphone and sound for $origin"

Step "Starting Emkay full screen when someone signs in"
if ($PSCmdlet.ShouldProcess($startup, "Create Startup shortcut to $Url")) {
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut($startup)
    $lnk.TargetPath = $edge
    $lnk.Arguments = "--app=$Url --start-fullscreen --no-first-run"
    $lnk.Description = "Emkay"
    $lnk.Save()
}
Done "Emkay starts as a full-screen app at sign-in"

Step "Keeping the screen and the PC awake while plugged in"
if ($PSCmdlet.ShouldProcess("power plan", "Never turn off the screen or sleep on AC power")) {
    powercfg /change monitor-timeout-ac 0
    powercfg /change standby-timeout-ac 0
}
Done "Screen and PC stay awake on mains power"

Write-Host ""
Note "Next: let the PC sign in by itself (see docs/windows.md, step 2), then restart."
Note "Press F11 to leave full screen, Alt+F4 to close Emkay."
Write-Host ""
