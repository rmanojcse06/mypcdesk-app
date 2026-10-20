@echo off
rem Stop MyDesk from opening when you sign in (the app itself stays installed).
powershell -NoProfile -Command "Remove-Item -ErrorAction SilentlyContinue (Join-Path ([Environment]::GetFolderPath('Startup')) 'MyDesk.lnk'); Write-Host 'MyDesk removed from startup.'"
pause
