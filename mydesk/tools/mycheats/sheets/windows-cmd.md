---
title: Windows CMD
color: "#2f6fed"
blurb: Command Prompt basics for files, network and system.
---
## Files and folders
- `dir /a` : list files, including hidden ones
- `cd /d D:\work` : change drive and folder in one step
- `mkdir name` : make a folder
- `copy a.txt b.txt` : copy a file
- `xcopy src dst /e /i /h` : copy a folder tree
- `robocopy src dst /mir` : mirror a folder (deletes extras in dst)
- `move a.txt folder\` : move a file
- `del file.txt` : delete a file
- `rmdir /s /q folder` : delete a folder and everything in it (careful)
- `tree /f` : show a folder tree with files
- `where python` : find which program runs for a command

## Network
- `ipconfig /all` : IP, gateway, DNS and MAC addresses
- `ipconfig /flushdns` : clear the DNS cache
- `ping -n 4 google.com` : test reachability
- `tracert google.com` : show the route to a host
- `nslookup example.com` : look up DNS records
- `netstat -ano` : open ports with their process IDs
- `netsh wlan show profiles` : saved Wi-Fi networks
- `curl -I https://example.com` : fetch only the response headers

## System
- `systeminfo` : Windows version, RAM, boot time
- `tasklist` : running processes
- `taskkill /im name.exe /f` : force-close a program
- `taskkill /pid 1234 /f` : force-close by process ID
- `sfc /scannow` : repair Windows system files (admin)
- `chkdsk C: /f` : check a drive for errors (admin)
- `shutdown /r /t 0` : restart now
- `powercfg /batteryreport` : battery health report (HTML)

## Environment
- `set` : list environment variables
- `echo %PATH%` : show the PATH
- `setx NAME "value"` : save a variable for future windows

## Handy
- `cls` : clear the screen
- `command > out.txt 2>&1` : save output and errors to a file
- `command | clip` : copy output to the clipboard
- `start .` : open the current folder in File Explorer
