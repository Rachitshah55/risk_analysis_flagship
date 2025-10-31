# Safe import: creates tasks only if missing. Never overwrites. Never requires admin.
# Use GUI import (as Admin) if you ever need to overwrite existing tasks.

$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\DevProjects\risk_analysis_flagship"
$ImportDir   = Join-Path $ProjectRoot "docs_global\runbooks\scheduler_exports"

# xml -> exact task name (matches your exports)
$Map = @{
  "Credit Daily.xml"        = "Credit Daily";
  "Fraud Detect Daily.xml"  = "Fraud Detect Daily";
  "Credit EOM Roll-up.xml"  = "Credit EOM Roll-up";
}

function Fix-WorkingDir($xmlPath, $dir) {
  try {
    [xml]$x = Get-Content -Path $xmlPath -Encoding UTF8
    $changed = $false
    foreach ($exec in $x.Task.Actions.Exec) {
      if ($null -eq $exec.WorkingDirectory -or $exec.WorkingDirectory -ne $dir) {
        $exec.WorkingDirectory = $dir; $changed = $true
      }
    }
    if ($changed) { $tmp=[IO.Path]::GetTempFileName() -replace '.tmp$','.xml'; $x.Save($tmp); return $tmp }
    return $xmlPath
  } catch { return $xmlPath }
}

foreach ($kv in $Map.GetEnumerator()) {
  $xmlFile  = Join-Path $ImportDir $kv.Key
  $taskName = $kv.Value
  if (!(Test-Path $xmlFile)) { Write-Warning "Missing XML: $xmlFile"; continue }

  # If the task already exists, just skip (no errors, no admin needed)
  $exists = $false
  try { $null = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop; $exists = $true } catch { }

  if ($exists) {
    Write-Host "[SKIP] '$taskName' already exists. Use GUI (Task Scheduler as Admin) to overwrite if desired."
    continue
  }

  $xmlForImport = Fix-WorkingDir $xmlFile $ProjectRoot
  $xmlString = Get-Content -Path $xmlForImport -Raw -Encoding UTF8
  Register-ScheduledTask -TaskName $taskName -Xml $xmlString -Force | Out-Null
  Write-Host "[OK] Created '$taskName'"
}

Write-Host "[DONE] Safe import complete."
