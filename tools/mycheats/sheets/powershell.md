---
title: PowerShell
color: "#5b3fc4"
blurb: PowerShell equivalents and the object pipeline.
---
## Find your way
- `Get-Help Get-Process -Examples` : examples for any command
- `Get-Command *service*` : find commands by name
- `Get-Member` : see the properties of what's in the pipeline (`Get-Process | Get-Member`)
- `$PSVersionTable` : PowerShell version

## Files
- `Get-ChildItem -Recurse -Filter *.log` : find files by pattern
- `Get-ChildItem -Force` : include hidden files
- `Copy-Item src dst -Recurse` : copy a folder
- `Remove-Item folder -Recurse -Force` : delete a folder (careful)
- `Get-Content file.txt -Tail 20 -Wait` : follow the end of a log file
- `Select-String -Path *.txt -Pattern "error"` : search text in files (like grep)
- `Get-FileHash file.iso -Algorithm SHA256` : file checksum
- `Compress-Archive src out.zip` : make a zip
- `Expand-Archive in.zip dst` : unzip

## Processes and services
- `Get-Process | Sort-Object CPU -Descending | Select-Object -First 10` : top CPU users
- `Stop-Process -Name notepad` : close a program
- `Get-Service | Where-Object Status -eq Running` : running services
- `Restart-Service -Name Spooler` : restart a service (admin)

## Network
- `Test-NetConnection google.com -Port 443` : check a port is reachable
- `Get-NetIPAddress -AddressFamily IPv4` : IP addresses
- `Resolve-DnsName example.com` : DNS lookup
- `Invoke-WebRequest https://example.com -OutFile page.html` : download a file
- `Invoke-RestMethod https://api.github.com/users/octocat` : call a JSON API

## System
- `Get-ComputerInfo` : full system summary
- `Get-PnpDevice -PresentOnly -Class USB` : connected USB devices
- `Get-Volume` : drives and free space
- `Get-HotFix` : installed Windows updates

## Pipeline tricks
- `... | Out-GridView` : show results in a sortable window
- `... | Export-Csv out.csv -NoTypeInformation` : save results as CSV
- `... | ConvertTo-Json` : results as JSON
- `... | Measure-Object` : count items
- `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` : allow your own scripts to run
