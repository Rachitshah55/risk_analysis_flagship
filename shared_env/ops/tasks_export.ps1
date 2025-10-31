# Exports your existing tasks using YOUR names and YOUR filenames.
# No schtasks, GUI-friendly, zero renames required.

$ErrorActionPreference = "Stop"

# --- CONFIG (matches your XML files) ---
$ProjectRoot = "C:\DevProjects\risk_analysis_flagship"
$ExportDir   = Join-Path $ProjectRoot "docs_global\runbooks\scheduler_exports"

# Task Scheduler names (exactly as in your system)
$TaskNames = @(
  "Credit Daily",
  "Fraud Detect Daily",
  "Credit EOM Roll-up"
)

# Output filenames (exactly like the ones you attached)
$NameToFile = @{
  "Credit Daily"        = "Credit Daily.xml"
  "Fraud Detect Daily"  = "Fraud Detect Daily.xml"
  "Credit EOM Roll-up"  = "Credit EOM Roll-up.xml"
}
# ---------------------------------------

if (!(Test-Path $ExportDir)) { New-Item -ItemType Directory -Force -Path $ExportDir | Out-Null }

function Export-TaskXml($name, $outPath) {
  try {
    $xml = Export-ScheduledTask -TaskName $name
    $xml | Out-File -FilePath $outPath -Encoding utf8
    Write-Host "[OK] Exported '$name' -> $outPath"
  } catch {
    Write-Warning "Task '$name' not found or cannot be exported. $_"
  }
}

foreach ($name in $TaskNames) {
  Export-TaskXml -name $name -outPath (Join-Path $ExportDir $NameToFile[$name])
}

Write-Host "[DONE] Exports saved to $ExportDir"
