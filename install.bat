@echo off
rem Double-click to install MyDesk and add it to Windows startup.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
