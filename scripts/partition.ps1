Write-Host "Starting full stack..."
docker compose up --build -d
Start-Sleep -Seconds 8

Write-Host "Full stack is live. Open http://localhost:3000 to watch the dashboard."
Start-Sleep -Seconds 2

# Auto-detect container names rather than hardcoding them
$nodeA = docker ps --filter "name=node_a" --format "{{.Names}}"
$nodeB = docker ps --filter "name=node_b" --format "{{.Names}}"

if (-not $nodeA -or -not $nodeB) {
    Write-Host "ERROR: Could not find node_a or node_b containers. Is the cluster running?"
    Write-Host "Run 'docker ps' to check container names."
    exit 1
}

# Auto-detect the network name
$network = docker network ls --filter "name=rlnet" --format "{{.Name}}"

if (-not $network) {
    Write-Host "ERROR: Could not find the rlnet network."
    Write-Host "Run 'docker network ls' to check available networks."
    exit 1
}

Write-Host "Detected containers: $nodeA, $nodeB"
Write-Host "Detected network: $network"
Write-Host ""

Write-Host "Baseline — all nodes before partition:"
@(8001, 8002, 8003, 8004) | ForEach-Object {
    $s = Invoke-RestMethod "http://localhost:$_/status"
    Write-Host "  node=$($s.node_id)  global_total=$($s.global_total)"
}

Write-Host ""
Write-Host "Partitioning node_a and node_b off from node_c and node_d..."
docker network disconnect $network $nodeA
docker network disconnect $network $nodeB
Write-Host "Partition active. Gossip between {a,b} and {c,d} is now broken."
Write-Host "Waiting 20 seconds — watch the dashboard diverge..."
Start-Sleep -Seconds 20

Write-Host ""
Write-Host "Node statuses during partition:"
@(8001, 8002, 8003, 8004) | ForEach-Object {
    try {
        $s = Invoke-RestMethod "http://localhost:$_/status" -TimeoutSec 2
        Write-Host "  node=$($s.node_id)  global_total=$($s.global_total)  counts=$($s.counts | ConvertTo-Json -Compress)"
    } catch {
        Write-Host "  port $_ did not respond"
    }
}

Write-Host ""
Write-Host "Healing partition..."
docker network connect $network $nodeA
docker network connect $network $nodeB
Write-Host "Partition healed. Waiting 3 seconds for gossip to re-converge..."
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Node statuses after healing:"
@(8001, 8002, 8003, 8004) | ForEach-Object {
    $s = Invoke-RestMethod "http://localhost:$_/status"
    Write-Host "  node=$($s.node_id)  global_total=$($s.global_total)  counts=$($s.counts | ConvertTo-Json -Compress)"
}

Write-Host ""
Write-Host "All global_total values should now match."
Write-Host "Tearing down..."
docker compose down