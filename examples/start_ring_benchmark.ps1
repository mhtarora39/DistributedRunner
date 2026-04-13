$project_dir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent | Split-Path -Parent

Write-Host "Orchestrating a 3-Node Distributed Benchmarking Ring within Windows Terminal tabs..."

wt new-tab -d "$project_dir" --title "Rank 4" powershell -NoExit -Command "python node.py --rank 4 --world-size 5" `; `
   new-tab -d "$project_dir" --title "Rank 3" powershell -NoExit -Command "python node.py --rank 3 --world-size 5" `; `
   new-tab -d "$project_dir" --title "Rank 2" powershell -NoExit -Command "python node.py --rank 2 --world-size 5" `; `
   new-tab -d "$project_dir" --title "Rank 1" powershell -NoExit -Command "python node.py --rank 1 --world-size 5" `; `
   new-tab -d "$project_dir" --title "Rank 0 (Master)" powershell -NoExit -Command "python node.py --rank 0 --world-size 5 --validate"
