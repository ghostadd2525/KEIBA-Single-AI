# Windows-only save + extract for the read-only live-source capture.
# Do not copy this file onto Production.
# Do not redirect remote bash to a Production path.
# Cursor does not SSH.
param(
    [Parameter(Mandatory = $true)][string]$RemoteHost,
    [string]$OutDir = (Join-Path $PWD "live_source_capture_windows")
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $here "OWNER_PASTE_COMMAND_BLOCK.sh"
if (-not (Test-Path $script)) {
    throw "OWNER_PASTE_COMMAND_BLOCK.sh not found next to this ps1"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$transcript = Join-Path $OutDir "transcript.txt"
Write-Host "WINDOWS_ONLY_SAVE=YES"
Write-Host "PRODUCTION_WRITE=NO"
Write-Host "SCP_UPLOAD=NO"
Write-Host "TRANSCRIPT=$transcript"

Get-Content -Raw -Path $script | ssh $RemoteHost bash 2>&1 | Tee-Object -FilePath $transcript | Out-Host

$extractPy = Join-Path $here "extract_capture.py"
$extracted = Join-Path $OutDir "extracted"
if (Get-Command python -ErrorAction SilentlyContinue) {
    & python $extractPy $transcript --out $extracted
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    & python3 $extractPy $transcript --out $extracted
} else {
    Write-Host "PYTHON_EXTRACT=SKIPPED"
    Write-Host "NEXT=install Python or run extract_capture.py on the review machine"
}

Write-Host "PRODUCTION_CODE_DEPLOY_ALLOWED=NO"
Write-Host "DEPLOY_EXECUTION_PACK=NO"
Write-Host "NEXT=return transcript + extracted files; do not deploy"
