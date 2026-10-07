$t = Get-ScheduledTask -TaskName "Joyce OS - Delayed Start"
"State: " + $t.State
"Delay: " + $t.Triggers[0].Delay
"Run:   " + $t.Actions[0].Execute + " " + $t.Actions[0].Arguments
$startup = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
"Startup folder:"
Get-ChildItem $startup | ForEach-Object { "  " + $_.Name }
