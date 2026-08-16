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

Write-Host "Taking baseline snapshot..."
Start-Sleep -Seconds 2
$before = @(8001, 8002, 8003, 8004) | ForEach-Object {
    Invoke-RestMethod "http://localhost:$_/status"
}

Write-Host "Spike running for 45 seconds..."
Start-Sleep -Seconds 45

$after = @(8001, 8002, 8003, 8004) | ForEach-Object {
    Invoke-RestMethod "http://localhost:$_/status"
}

Write-Host ""
Write-Host "Delta over 45 seconds (window-reset safe):"
$totalHitsDelta = 0
$totalRejectedDelta = 0
for ($i = 0; $i -lt 4; $i++) {
    $hitsDelta     = if ($after[$i].api_hits -ge $before[$i].api_hits) { $after[$i].api_hits - $before[$i].api_hits } else { $after[$i].api_hits }
    $rejectedDelta = if ($after[$i].rejected -ge $before[$i].rejected) { $after[$i].rejected - $before[$i].rejected } else { $after[$i].rejected }
    Write-Host "  node=$($after[$i].node_id)  hits_delta=$hitsDelta  rejected_delta=$rejectedDelta"
    $totalHitsDelta += $hitsDelta
    $totalRejectedDelta += $rejectedDelta
}
Write-Host ""
Write-Host "TOTAL hits in 45s window: $totalHitsDelta  (limit is 100/min, so ~75 expected over 45s)"
Write-Host "TOTAL rejected in 45s window: $totalRejectedDelta"

Write-Host ""
Write-Host "Returning to normal load..."
$env:REQUESTS_PER_MINUTE = "300"
docker compose up generator -d --no-deps --force-recreate

Write-Host "Tearing down..."
docker compose down