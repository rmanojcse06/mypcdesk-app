# MyDesk installer for Windows.
# Creates a private Python environment, installs packages, and adds MyDesk to
# Windows startup, the Start menu and the desktop.
# Run by double-clicking install.bat (or: powershell -ExecutionPolicy Bypass -File install.ps1)

param([switch]$NoStartup)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
Write-Host ""
Write-Host "  MyDesk installer" -ForegroundColor Magenta
Write-Host "  Folder: $Root"
Write-Host ""

# 1. Find Python 3.10-3.13 (py launcher, PATH, or Anaconda)
function Get-PyVersion($exe, $extra) {
    try { return (& $exe @extra -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null).Trim() } catch { return $null }
}
$candidates = @(
    @{exe = "py"; extra = @("-3.12")}, @{exe = "py"; extra = @("-3.11")}, @{exe = "py"; extra = @("-3.13")},
    @{exe = "py"; extra = @("-3")}, @{exe = "python"; extra = @()},
    @{exe = "$env:USERPROFILE\anaconda3\python.exe"; extra = @()},
    @{exe = "$env:USERPROFILE\miniconda3\python.exe"; extra = @()},
    @{exe = "$env:ProgramData\anaconda3\python.exe"; extra = @()}
)
$py = $null
foreach ($c in $candidates) {
    $v = Get-PyVersion $c.exe $c.extra
    if ($v -and [version]$v -ge [version]"3.10" -and [version]$v -le [version]"3.13") { $py = $c; break }
}
if (-not $py) {
    Write-Host "Python 3.10 - 3.13 not found. Install Python 3.12 from https://www.python.org/downloads/ and run this again." -ForegroundColor Red
    Read-Host "Press Enter to close"; exit 1
}
Write-Host "[1/4] Using Python $(Get-PyVersion $py.exe $py.extra) ($($py.exe) $($py.extra -join ' '))" -ForegroundColor Cyan

# 2. Private environment
$venv = Join-Path $Root ".venv"
if (-not (Test-Path "$venv\Scripts\python.exe")) {
    & $py.exe @($py.extra) -m venv $venv
}
$vpy = "$venv\Scripts\python.exe"
$vpyw = "$venv\Scripts\pythonw.exe"

Write-Host "[2/4] Installing packages (first time takes a few minutes)" -ForegroundColor Cyan
& $vpy -m pip install --upgrade pip --quiet
& $vpy -m pip install -r (Join-Path $Root "requirements.txt") --quiet
if ($LASTEXITCODE -ne 0) { Write-Host "Package install failed - see messages above." -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }

# 3. Shortcuts
Write-Host "[3/4] Creating shortcuts" -ForegroundColor Cyan
$shell = New-Object -ComObject WScript.Shell
$icon = Join-Path $Root "mydesk\ui\mydesk.ico"
function New-Shortcut($path, $arguments) {
    $s = $shell.CreateShortcut($path)
    $s.TargetPath = $vpyw
    $s.Arguments = "`"$Root\mydesk.py`" $arguments".Trim()
    $s.WorkingDirectory = $Root
    $s.Description = "MyDesk"
    if (Test-Path $icon) { $s.IconLocation = $icon }
    $s.Save()
}
New-Shortcut (Join-Path ([Environment]::GetFolderPath("Desktop")) "MyDesk.lnk") ""
New-Shortcut (Join-Path ([Environment]::GetFolderPath("Programs")) "MyDesk.lnk") ""
if (-not $NoStartup) {
    New-Shortcut (Join-Path ([Environment]::GetFolderPath("Startup")) "MyDesk.lnk") ""
    Write-Host "      MyDesk will open automatically when you sign in to Windows."
}

# 4. Check WebView2 (built into Windows 11; Edge installs it on Windows 10)
Write-Host "[4/4] Checking the window engine (WebView2)" -ForegroundColor Cyan
$wv = Get-ItemProperty "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" -ErrorAction SilentlyContinue
if (-not $wv) { $wv = Get-ItemProperty "HKCU:\Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" -ErrorAction SilentlyContinue }
if (-not $wv) { Write-Host "      WebView2 not detected - MyDesk will open in an Edge app window instead." -ForegroundColor Yellow }

Write-Host ""
Write-Host "Done! Starting MyDesk..." -ForegroundColor Green
Start-Process $vpyw -ArgumentList "`"$Root\mydesk.py`"" -WorkingDirectory $Root
Start-Sleep -Seconds 2
