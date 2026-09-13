# Windows-only save + extract for the read-only prediction_capacity live-source capture.
# PowerShell 5.1: send OWNER_PASTE_COMMAND_BLOCK.sh raw bytes to SSH stdin.
# Do not read the Owner script as text (that can change bytes).
# Do not copy this file onto Production.
# Do not redirect remote bash to a Production path.
# Cursor does not SSH.
param(
    [Parameter(Mandatory = $true)][string]$RemoteHost,
    [string]$OutDir = (Join-Path $PWD "prediction_capacity_capture_windows"),
    [string]$IdentityFile = "",
    [int]$TimeoutSec = 180
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $here "OWNER_PASTE_COMMAND_BLOCK.sh"
if (-not (Test-Path -LiteralPath $script)) {
    throw "OWNER_PASTE_COMMAND_BLOCK.sh not found next to this ps1"
}

if (Test-Path -LiteralPath $OutDir) {
    Write-Host "OUTDIR_EXISTS=YES"
    Write-Host "OUTDIR=$OutDir"
    Write-Host "SSH_SKIPPED=YES"
    Write-Host "EXTRACT_SKIPPED=YES"
    Write-Host "EXTRACT_RESULT=STOP"
    Write-Host "PRODUCTION_CODE_DEPLOY_ALLOWED=NO"
    Write-Host "DEPLOY_EXECUTION_PACK=NO"
    Write-Host "NEXT=choose a new OutDir; do not reuse or overwrite"
    exit 2
}
New-Item -ItemType Directory -Path $OutDir | Out-Null
$transcript = Join-Path $OutDir "transcript.txt"
Write-Host "WINDOWS_ONLY_SAVE=YES"
Write-Host "PRODUCTION_WRITE=NO"
Write-Host "SCP_UPLOAD=NO"
Write-Host "GET_CONTENT_RAW=NO"
Write-Host "TRANSCRIPT=$transcript"
if ($IdentityFile -ne "") {
    Write-Host "IDENTITY_FILE_SET=YES"
} else {
    Write-Host "IDENTITY_FILE_SET=NO"
}

$scriptBytes = [System.IO.File]::ReadAllBytes($script)
$sshArgs = New-Object System.Collections.Generic.List[string]
if ($IdentityFile -ne "") {
    if (-not (Test-Path -LiteralPath $IdentityFile)) {
        throw "IdentityFile not found: $IdentityFile"
    }
    $sshArgs.Add("-i") | Out-Null
    $sshArgs.Add($IdentityFile) | Out-Null
    $sshArgs.Add("-o") | Out-Null
    $sshArgs.Add("IdentitiesOnly=yes") | Out-Null
}
$sshArgs.Add("-o") | Out-Null
$sshArgs.Add("BatchMode=yes") | Out-Null
$sshArgs.Add($RemoteHost) | Out-Null
$sshArgs.Add("bash") | Out-Null

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "ssh"
$psi.UseShellExecute = $false
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true
$psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
$psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
# PowerShell 5.1 ProcessStartInfo has no ArgumentList. Use Arguments string.
$quoted = @()
foreach ($a in $sshArgs) {
    if ($a -match '[\s"]') {
        $quoted += '"' + ($a -replace '"', '\"') + '"'
    } else {
        $quoted += $a
    }
}
$psi.Arguments = [string]::Join(" ", $quoted)

$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $psi
$started = $false
try {
    $started = $proc.Start()
} catch {
    Write-Host "SSH_START=FAIL"
    Write-Host "EXTRACT_SKIPPED=YES"
    Write-Host "EXTRACT_RESULT=STOP"
    Write-Host "PRODUCTION_CODE_DEPLOY_ALLOWED=NO"
    Write-Host "DEPLOY_EXECUTION_PACK=NO"
    throw
}
if (-not $started) {
    Write-Host "SSH_START=FAIL"
    Write-Host "EXTRACT_SKIPPED=YES"
    Write-Host "EXTRACT_RESULT=STOP"
    Write-Host "PRODUCTION_CODE_DEPLOY_ALLOWED=NO"
    Write-Host "DEPLOY_EXECUTION_PACK=NO"
    exit 2
}

$stdin = $proc.StandardInput.BaseStream
$stdin.Write($scriptBytes, 0, $scriptBytes.Length)
$stdin.Flush()
$stdin.Close()

$timeoutMs = $TimeoutSec * 1000
$outTask = $proc.StandardOutput.ReadToEndAsync()
$errTask = $proc.StandardError.ReadToEndAsync()
$exited = $proc.WaitForExit($timeoutMs)
if (-not $exited) {
    try { $proc.Kill() } catch { }
    Start-Sleep -Milliseconds 200
    $stdoutText = ""
    $stderrText = ""
    try { $stdoutText = $outTask.Result } catch { }
    try { $stderrText = $errTask.Result } catch { }
    [System.IO.File]::WriteAllText($transcript, $stdoutText + $stderrText, [System.Text.UTF8Encoding]::new($false))
    Write-Host "SSH_TIMEOUT=YES"
    Write-Host "EXTRACT_SKIPPED=YES"
    Write-Host "EXTRACT_RESULT=STOP"
    Write-Host "PRODUCTION_CODE_DEPLOY_ALLOWED=NO"
    Write-Host "DEPLOY_EXECUTION_PACK=NO"
    exit 2
}

$stdoutText = $outTask.Result
$stderrText = $errTask.Result
$code = $proc.ExitCode
[System.IO.File]::WriteAllText($transcript, $stdoutText + $stderrText, [System.Text.UTF8Encoding]::new($false))
Write-Host $stdoutText
if ($stderrText -ne "") {
    Write-Host $stderrText
}
Write-Host "SSH_EXIT=$code"

if ($code -ne 0) {
    Write-Host "EXTRACT_SKIPPED=YES"
    Write-Host "EXTRACT_RESULT=STOP"
    Write-Host "PRODUCTION_CODE_DEPLOY_ALLOWED=NO"
    Write-Host "DEPLOY_EXECUTION_PACK=NO"
    exit $code
}

$extractPy = Join-Path $here "extract_capture.py"
$extracted = Join-Path $OutDir "extracted"
$py = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $py = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $py = "python3"
}
if ($null -eq $py) {
    Write-Host "PYTHON_EXTRACT=SKIPPED"
    Write-Host "NEXT=install Python or run extract_capture.py on the review machine"
} else {
    & $py $extractPy $transcript --out $extracted
    if ($LASTEXITCODE -ne 0) {
        Write-Host "EXTRACT_RESULT=STOP"
        Write-Host "PRODUCTION_CODE_DEPLOY_ALLOWED=NO"
        Write-Host "DEPLOY_EXECUTION_PACK=NO"
        exit $LASTEXITCODE
    }
}

Write-Host "PRODUCTION_CODE_DEPLOY_ALLOWED=NO"
Write-Host "DEPLOY_EXECUTION_PACK=NO"
Write-Host "NEXT=return transcript + extracted files; do not deploy"
