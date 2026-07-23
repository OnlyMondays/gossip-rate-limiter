Write-Host "Starting full stack..."
docker compose up --build -d
Start-Sleep -Seconds 8

Write-Host "Cluster is live. Open http://localhost:3000 to watch the dashboard."
Write-Host "Press Enter when ready to kill node_b..."
Read-Host

Write-Host "Killing node_b..."
docker compose stop node_b
Write-Host "node_b is down. Cluster should keep enforcing for 15 seconds..."
Start-Sleep -Seconds 15

Write-Host "Checking remaining nodes still respond:"
@(8001, 8003, 8004) | ForEach-Object {
    $s = Invoke-RestMethod "http://localhost:$_/status"
    Write-Host "  node=$($s.node_id)  global_total=$($s.global_total)"
}

Write-Host ""
Write-Host "Restarting node_b..."
docker compose start node_b
Start-Sleep -Seconds 3

Write-Host "Checking node_b re-converged:"
$s = Invoke-RestMethod http://localhost:8002/status
Write-Host "  node=$($s.node_id)  global_total=$($s.global_total)"

Write-Host ""
Write-Host "All node statuses after recovery:"
@(8001, 8002, 8003, 8004) | ForEach-Object {
    $s = Invoke-RestMethod "http://localhost:$_/status"
    Write-Host "  node=$($s.node_id)  global_total=$($s.global_total)"
}

Write-Host "Tearing down..."
docker compose down