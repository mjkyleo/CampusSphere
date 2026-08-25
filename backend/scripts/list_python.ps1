Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' } | ForEach-Object {
    Write-Output ($_.ProcessId.ToString() + " | " + $_.CommandLine)
}
