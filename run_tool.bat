@echo off
rem Run any MyDesk tool from a terminal, e.g.
rem   run_tool list
rem   run_tool clip_saver "https://www.youtube.com/shorts/XXXX"
"%~dp0.venv\Scripts\python.exe" "%~dp0mytool.py" %*
