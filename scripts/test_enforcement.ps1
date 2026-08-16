Write-Host "Starting cluster..."
docker compose up node_a node_b node_c node_d --build -d

Write-Host "Waiting for nodes to be ready..."
Start-Sleep -Seconds 5

Write-Host "Running enforcement test (limit=100, firing 150 requests)..."
$ports = @(8001, 8002, 8003, 8004)
$allowed = 0
$denied = 0

1..150 | ForEach-Object {
    $port = $ports | Get-Random
    $result = Invoke-RestMethod -Method Post -Uri "http://localhost:$port/request" `
        -ContentType "application/json" -Body '{"query":"test"}'
    $label = if ($result.allowed) { "ALLOW"; $script:allowed++ } else { "DENY "; $script:denied++ }
    Write-Host "$label  total=$($result.global_total)"
}

Write-Host ""
Write-Host "Result: $allowed allowed, $denied denied (expected ~100 allowed, ~50 denied)"

Write-Host "Tearing down cluster..."
docker compose down