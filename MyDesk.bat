@echo off
rem Open MyDesk (same as the desktop shortcut).
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0mydesk.py" %*
