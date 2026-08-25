# Stop celery worker python processes only (keep uvicorn and fake redis)
$procs = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'python.exe' -and $_.CommandLine -match 'celery'
}
foreach ($p in $procs) {
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Output ("killed " + $p.ProcessId)
}
