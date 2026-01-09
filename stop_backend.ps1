# Stop backend on port 8000
Write-Host "Stopping backend on port 8000..."

$connections = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($connections) {
    foreach ($conn in $connections) {
        $pid = $conn.OwningProcess
        Write-Host "Found process PID: $pid"
        try {
            Stop-Process -Id $pid -Force -ErrorAction Stop
            Write-Host "Killed process $pid"
        } catch {
            Write-Host "Could not kill process $pid : $_"
        }
    }
    Start-Sleep -Seconds 2
    $check = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    if ($check) {
        Write-Host "Warning: Port 8000 still in use"
    } else {
        Write-Host "✅ Backend stopped successfully"
    }
} else {
    Write-Host "No process found on port 8000"
}

# Also try to kill any Python processes that might be the backend
Write-Host "`nChecking for Python processes..."
$pythonProcs = Get-Process python* -ErrorAction SilentlyContinue
if ($pythonProcs) {
    Write-Host "Found $($pythonProcs.Count) Python process(es)"
    $pythonProcs | ForEach-Object {
        Write-Host "  - PID: $($_.Id), Name: $($_.ProcessName)"
    }
    $response = Read-Host "Kill all Python processes? (y/n)"
    if ($response -eq 'y') {
        $pythonProcs | Stop-Process -Force
        Write-Host "✅ All Python processes killed"
    }
} else {
    Write-Host "No Python processes found"
}
