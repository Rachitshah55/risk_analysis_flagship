# Re-imports FROM your three XMLs TO your three existing names.
# Uses Register-ScheduledTask only. No schtasks. No renames.
# If tasks already exist, add -Force to overwrite in-place.

param([switch]$Force)
$ErrorActionPreference = "Stop"

# --- CONFIG (matches your XML files) ---
$ProjectRoot = "C:\DevProjects\risk_analysis_flagship"
$ImportDir   = Join-Path $ProjectRoot "docs_global\runbooks\scheduler_exports"

# xml filename -> Task Scheduler name (EXACT)
$Map = @{
  "Credit Daily.xml"        = "Credit Daily";
  "Fraud Detect Daily.xml"  = "Fraud Detect Daily";
  "Credit EOM Roll-up.xml"  = "Credit EOM Roll-up";
}
# ---------------------------------------

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

  $xmlForImport = Fix-WorkingDir $xmlFile $ProjectRoot

  $exists = $false
  try { $null = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop; $exists = $true } catch { }

  if ($exists -and $Force) {
    try {
      Unregister-ScheduledTask -TaskName $taskName -Confirm:$false | Out-Null
      Write-Host "[INFO] Removed existing '$taskName' (force)."
    } catch { Write-Warning "Could not remove existing '$taskName'. $_" }
  } elseif ($exists -and -not $Force) {
    Write-Host "[SKIP] Task '$taskName' already exists. Use -Force to overwrite."
    continue
  }

  try {
    $xmlString = Get-Content -Path $xmlForImport -Raw -Encoding UTF8
    Register-ScheduledTask -TaskName $taskName -Xml $xmlString -Force | Out-Null
    Write-Host "[OK] Imported '$taskName'"
  } catch {
    Write-Error "Failed to import '$taskName'. $_"
  }
}

Write-Host "[DONE] Import complete. Verify in Task Scheduler."
