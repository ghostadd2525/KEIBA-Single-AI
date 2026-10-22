# PROD-PREDICTION-ID-CUTOVER-OWNER-LOCAL
# Run from the owner's Windows machine that already has SSH to production.
# Does NOT run via Cloud Agent. Does NOT overwrite dirty prediction_adapter.py.
param(
  [string]$PemPath = "C:\Users\Mr.me\Downloads\expect-beta-tokyo.pem",
  [string]$HostName = "ubuntu@13.231.5.5",
  [string]$ScriptUrl = "https://raw.githubusercontent.com/ghostadd2525/KEIBA-Single-AI/cursor/race-id-contract-22d3/scripts/ops/prod-id-cutover-remote.sh"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $PemPath)) {
  throw "PEM not found: $PemPath"
}

$local = Join-Path $env:TEMP "prod-id-cutover-remote.sh"
Write-Host "[id-cutover] download $ScriptUrl"
Invoke-WebRequest -Uri $ScriptUrl -OutFile $local -UseBasicParsing

# Strip CR so bash on Ubuntu does not see Windows line endings.
$unix = [IO.File]::ReadAllText($local) -replace "`r`n", "`n" -replace "`r", "`n"
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[IO.File]::WriteAllText($local, $unix, $utf8NoBom)

Write-Host "[id-cutover] ssh $HostName (expect-ai restart only; adapter untouched)"
Get-Content -Raw $local | ssh -i $PemPath -o StrictHostKeyChecking=accept-new $HostName "sed 's/\r$//' | bash"
if ($LASTEXITCODE -ne 0) {
  throw "remote cutover failed with exit $LASTEXITCODE"
}
Write-Host "[id-cutover] remote script finished"
