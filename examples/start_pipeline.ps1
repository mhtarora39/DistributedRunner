$project_dir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent | Split-Path -Parent

Write-Host "Orchestrating a True Closed-Loop Architecture within Windows Terminal tabs..."

# Uses wt.exe to spawn four isolated instances of runner.py forming a completely solid circle
# Node 1 -> Node 2 -> Node 3 -> Node 4 -> back to Node 1

wt new-tab -d "$project_dir" --title "Node 4 (Ring Closer)" powershell -NoExit -Command "python runner.py --listen-port 9004 --target-port 9001 --mode proxy" `; `
   new-tab -d "$project_dir" --title "Node 3 (Proxy Node)" powershell -NoExit -Command "python runner.py --listen-port 9003 --target-port 9004 --mode proxy" `; `
   new-tab -d "$project_dir" --title "Node 2 (Proxy Node)" powershell -NoExit -Command "python runner.py --listen-port 9002 --target-port 9003 --mode proxy" `; `
   new-tab -d "$project_dir" --title "Node 1 (Isolate Manager)" powershell -NoExit -Command "python runner.py --listen-port 9001 --target-port 9002 --mode isolate"
