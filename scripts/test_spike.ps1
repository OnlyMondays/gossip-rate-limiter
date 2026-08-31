Write-Host "Starting full stack..."
docker compose up --build -d
Start-Sleep -Seconds 8

Write-Host "Full stack is live. Open http://localhost:3000 to watch the dashboard."
Write-Host "Generator is already firing at 300 req/min."
Write-Host "Press Enter when ready to spike to 1000 req/min..."
Read-Host

Write-Host "Spiking traffic to 1000 req/min..."
$env:REQUESTS_PER_MINUTE = "1000"
docker compose up generator -d --no-deps --force-recreate

Write-Host "Waiting for next minute boundary to start a clean window..."
$secondsUntilNextMinute = 60 - ((Get-Date).Second)
Write-Host "Waiting $secondsUntilNextMinute seconds for window alignment..."
Start-Sleep -Seconds $secondsUntilNextMinute

Write-Host "Window just reset — taking baseline snapshot now..."
$before = @(8001, 8002, 8003, 8004) | ForEach-Object {
    Invoke-RestMethod "http://localhost:$_/status"
}

Write-Host "Measuring for the full 60-second window..."
Start-Sleep -Seconds 58

$after = @(8001, 8002, 8003, 8004) | ForEach-Object {
    Invoke-RestMethod "http://localhost:$_/status"
}

Write-Host ""
Write-Host "Delta over one full window (~60s):"
$totalHitsDelta = 0
$totalRejectedDelta = 0
for ($i = 0; $i -lt 4; $i++) {
    $hitsDelta     = $after[$i].api_hits - $before[$i].api_hits
    $rejectedDelta = $after[$i].rejected - $before[$i].rejected
    Write-Host "  node=$($after[$i].node_id)  hits_delta=$hitsDelta  rejected_delta=$rejectedDelta"
    $totalHitsDelta += $hitsDelta
    $totalRejectedDelta += $rejectedDelta
}
Write-Host ""
Write-Host "TOTAL hits: $totalHitsDelta  (limit is 100/min, expect ~100)"
Write-Host "TOTAL rejected: $totalRejectedDelta  (expect ~900 at 1000 req/min load)"

Write-Host ""
Write-Host "Returning to normal load..."
$env:REQUESTS_PER_MINUTE = "300"
docker compose up generator -d --no-deps --force-recreate

Write-Host "Tearing down..."
docker compose down