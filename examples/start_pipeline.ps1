$project_dir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent | Split-Path -Parent

Write-Host "Orchestrating a 4-Node Pipeline within Windows Terminal tabs..."

# Uses wt.exe to spawn a single new terminal instance, opening new-tabs for each piece of the pipeline
# When passing a semicolon ';' to PowerShell through wt.exe, we must escape it as '\;' 
# so Windows Terminal doesn't interpret it as a "create new tab" command!

wt new-tab -d "$project_dir" --title "Node 4 (Server)" powershell -NoExit -Command "python nodes/server.py --port 9004" `; `
   new-tab -d "$project_dir" --title "Node 3 (Proxy)" powershell -NoExit -Command "Start-Sleep -Seconds 1 \`\; python runner.py --listen-port 9003 --target-port 9004 --mode proxy" `; `
   new-tab -d "$project_dir" --title "Node 2 (Proxy)" powershell -NoExit -Command "Start-Sleep -Seconds 2 \`\; python runner.py --listen-port 9002 --target-port 9003 --mode proxy" `; `
   new-tab -d "$project_dir" --title "Node 1 (Isolate)" powershell -NoExit -Command "Start-Sleep -Seconds 3 \`\; python runner.py --listen-port 9001 --target-port 9002 --mode isolate" `; `
   new-tab -d "$project_dir" --title "Node 0 (Client)" powershell -NoExit -Command "Start-Sleep -Seconds 4 \`\; python nodes/client.py --port 9001"
