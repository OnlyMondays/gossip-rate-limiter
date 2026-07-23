Write-Host "Starting full stack..."
docker compose up --build -d
Start-Sleep -Seconds 8

Write-Host "Full stack is live. Open http://localhost:3000 to watch the dashboard."
Write-Host "Generator is already firing at 300 req/min."
Write-Host "Press Enter when ready to spike to 1000 req/min..."
Read-Host

Write-Host "Spiking traffic to 1000 req/min..."
$env:REQUESTS_PER_MINUTE = "1000"
docker compose up generator -d --no-deps

Write-Host "Spike running for 30 seconds — watch dashboard hold at 100..."
Start-Sleep -Seconds 30

Write-Host "Checking riftcodex_hits stayed near 100:"
@(8001, 8002, 8003, 8004) | ForEach-Object {
    $s = Invoke-RestMethod "http://localhost:$_/status"
    Write-Host "  node=$($s.node_id)  riftcodex_hits=$($s.riftcodex_hits)  rejected=$($s.rejected)"
}

Write-Host ""
Write-Host "Returning to normal load..."
$env:REQUESTS_PER_MINUTE = "300"
docker compose up generator -d --no-deps

Write-Host "Tearing down..."
docker compose down