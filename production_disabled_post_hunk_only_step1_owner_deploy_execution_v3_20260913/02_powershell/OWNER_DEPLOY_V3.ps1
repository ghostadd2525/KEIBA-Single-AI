# PowerShell 5.1. Owner-only Production 工程1 hunk-only code deploy.
# Owner runs this file only. Cursor does not run this on Production.
# Sends pregenerated owner_deploy_stdin.py byte-for-byte on SSH stdin.
# Does not concatenate Python files at runtime. No SCP. No remote mkdir.
# Wrapper never invokes sudo. Payload restart argv is NOPASSWD systemctl restart only.
# Wrapper never sets OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED.
# Wrapper never sets or forwards OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED.
# Wrapper never sets or forwards OWNER_PRODUCTION_STEP1_V2_DEPLOY_APPROVED.
# Do not run v1 OWNER_DEPLOY.ps1 or v2 OWNER_DEPLOY_V2.ps1.
# Verifies SHA256SUMS + payload SHA before SSH.
$ErrorActionPreference = 'Continue'
$Key = 'C:\Users\Mr.me\Downloads\expect-beta-tokyo.pem'
$Target = 'ubuntu@13.231.5.5'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$PackRoot = Split-Path -Parent $Here
$StdinPy = Join-Path $Here 'owner_deploy_stdin.py'
$SumsFile = Join-Path $PackRoot 'SHA256SUMS.txt'
$FlagsFile = Join-Path $PackRoot 'FLAGS.txt'
$Downloads = Join-Path $env:USERPROFILE 'Downloads'
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$OutLog = Join-Path $Downloads ('production_disabled_post_hunk_only_step1_owner_deploy_execution_v3_20260913_output_' + $Stamp + '.txt')
$TimeoutMs = 400000
$script:KillDrainWaitMs = 8000
$script:DrainWaitMs = 20000
# Remote hard deadline is 300s. Wrapper must exceed remote + drain + kill-drain + 40s buffer.

if (Test-Path -LiteralPath $OutLog) {
    Write-Output 'OWNER_DEPLOY_STATUS=FAIL'
    Write-Output 'ERROR=refuse_overwrite_existing_output'
    Write-Output ('OUTPUT=' + $OutLog)
    exit 1
}

function Stop-ProcessTree {
    param([int]$ProcessId)
    if ($ProcessId -le 0) { return }
    $tk = $null
    try { $tk = Get-Command 'taskkill.exe' -ErrorAction SilentlyContinue } catch { $tk = $null }
    if ($null -ne $tk) {
        try { & taskkill.exe /PID $ProcessId /T /F | Out-Null } catch { }
        return
    }
    try {
        $p = [System.Diagnostics.Process]::GetProcessById($ProcessId)
        if ($null -ne $p) {
            if (-not $p.HasExited) { $p.Kill() }
        }
    } catch { }
}

function Get-TaskText {
    param($Task, [string]$Name)
    if ($null -eq $Task) { return ('(%s drain not started)' -f $Name) }
    $ran = [System.Threading.Tasks.TaskStatus]::RanToCompletion
    if ($Task.Status -eq $ran) {
        try { return [string]$Task.Result } catch { return ('(%s result error)' -f $Name) }
    }
    if ($Task.IsFaulted) {
        return ('(%s drain faulted status=%s)' -f $Name, [string]$Task.Status)
    }
    return ('(%s drain incomplete status=%s)' -f $Name, [string]$Task.Status)
}

function Get-RemoteDeployState {
    param([string]$StdOut)
    $executed = 'UNKNOWN'
    $phase = 'UNKNOWN'
    $restarted = 'UNKNOWN'
    if (-not [string]::IsNullOrEmpty($StdOut)) {
        $lines = $StdOut -split "(`r`n|`n)"
        foreach ($ln in $lines) {
            if ($ln.StartsWith('DEPLOY_EXECUTED=')) {
                $executed = $ln.Substring(16)
            }
            if ($ln.StartsWith('DEPLOY_PHASE=')) {
                $phase = $ln.Substring(13)
            }
            if ($ln.StartsWith('RESTART_EXECUTED=')) {
                $restarted = $ln.Substring(17)
            }
        }
    }
    return @{
        DeployExecuted = $executed
        DeployPhase = $phase
        RestartExecuted = $restarted
    }
}

function Get-WrapperAuditStatus {
    param(
        [bool]$TimedOut,
        [string]$ExitCodeText
    )
    if ($TimedOut) {
        return @{
            Status = 'FAILED'
            Reason = 'TIMEOUT'
            WrapperExit = 1
            SshExit = $ExitCodeText
        }
    }
    if ($ExitCodeText -ne '0') {
        return @{
            Status = 'FAILED'
            Reason = 'SSH_EXIT'
            WrapperExit = 1
            SshExit = $ExitCodeText
        }
    }
    return @{
        Status = 'SUCCESS'
        Reason = 'OK'
        WrapperExit = 0
        SshExit = '0'
    }
}

function Test-OwnerApprovalReady {
    param(
        [string]$Approved
    )
    if ($Approved -ne '1') {
        return @{
            Ready = $false
            Reason = 'OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED_UNSET'
        }
    }
    return @{
        Ready = $true
        Reason = 'OK'
    }
}

function Get-Sha256Hex {
    param([byte[]]$Bytes)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = $sha.ComputeHash($Bytes)
    } finally {
        $sha.Dispose()
    }
    return (([System.BitConverter]::ToString($hash) -replace '-', '').ToLowerInvariant())
}

function Get-FlagValue {
    param(
        [string]$FlagsText,
        [string]$Key
    )
    $prefix = $Key + '='
    $found = ''
    $lines = $FlagsText -split "(`r`n|`n)"
    foreach ($ln in $lines) {
        if ($ln.StartsWith($prefix)) {
            $found = $ln.Substring($prefix.Length)
        }
    }
    return $found
}

function Test-PackPayloadSha {
    param(
        [string]$PackRootPath,
        [string]$SumsPath,
        [string]$FlagsPath,
        [string]$PayloadPath
    )
    if (-not (Test-Path -LiteralPath $SumsPath)) {
        return @{ Ok = $false; Reason = 'SHA256SUMS_MISSING' }
    }
    if (-not (Test-Path -LiteralPath $FlagsPath)) {
        return @{ Ok = $false; Reason = 'FLAGS_MISSING' }
    }
    if (-not (Test-Path -LiteralPath $PayloadPath)) {
        return @{ Ok = $false; Reason = 'STDIN_PY_MISSING_ON_WINDOWS_PACK' }
    }
    $flagBytes = [System.IO.File]::ReadAllBytes($FlagsPath)
    $flagText = [System.Text.Encoding]::UTF8.GetString($flagBytes)
    $expectedPayload = Get-FlagValue -FlagsText $flagText -Key 'STDIN_PAYLOAD_SHA256'
    $payloadBytes = [System.IO.File]::ReadAllBytes($PayloadPath)
    $payloadSha = Get-Sha256Hex -Bytes $payloadBytes
    if ($expectedPayload -eq '' -or $expectedPayload -eq 'PENDING_GENERATE_EMBED') {
        return @{ Ok = $false; Reason = 'PAYLOAD_SHA_UNPINNED' }
    }
    if ($payloadSha -ne $expectedPayload) {
        return @{ Ok = $false; Reason = 'PAYLOAD_SHA_MISMATCH' }
    }
    $sumBytes = [System.IO.File]::ReadAllBytes($SumsPath)
    $sumText = [System.Text.Encoding]::UTF8.GetString($sumBytes)
    $sumLines = $sumText -split "(`r`n|`n)"
    $checked = 0
    foreach ($ln in $sumLines) {
        if ([string]::IsNullOrWhiteSpace($ln)) { continue }
        if ($ln.Length -lt 67) {
            return @{ Ok = $false; Reason = 'PACK_SHA_MISMATCH' }
        }
        $want = $ln.Substring(0, 64).ToLowerInvariant()
        $rel = $ln.Substring(66).Trim()
        if ($rel -eq 'SHA256SUMS.txt') { continue }
        $full = Join-Path $PackRootPath (($rel -replace '/', [IO.Path]::DirectorySeparatorChar))
        if (-not (Test-Path -LiteralPath $full)) {
            return @{ Ok = $false; Reason = 'PACK_SHA_MISMATCH' }
        }
        $got = Get-Sha256Hex -Bytes ([System.IO.File]::ReadAllBytes($full))
        if ($got -ne $want) {
            return @{ Ok = $false; Reason = 'PACK_SHA_MISMATCH' }
        }
        $checked++
    }
    if ($checked -lt 1) {
        return @{ Ok = $false; Reason = 'PACK_SHA_MISMATCH' }
    }
    return @{ Ok = $true; Reason = 'OK'; PayloadSha = $payloadSha; FilesChecked = $checked }
}

function Invoke-TimedProcess {
    param(
        [string]$FileName,
        [string]$Arguments,
        [int]$TimeoutMs,
        [string]$StdinText,
        [byte[]]$StdinBytes
    )
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FileName
    $psi.Arguments = $Arguments
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    $started = $false
    $stdoutTask = $null
    $stderrTask = $null
    try {
        [void]$proc.Start()
        $started = $true
        $stdoutTask = $proc.StandardOutput.ReadToEndAsync()
        $stderrTask = $proc.StandardError.ReadToEndAsync()
        if ($null -ne $StdinBytes) {
            $proc.StandardInput.BaseStream.Write($StdinBytes, 0, $StdinBytes.Length)
            $proc.StandardInput.BaseStream.Flush()
            $proc.StandardInput.Close()
        } elseif ($null -ne $StdinText) {
            $utf8NoBom = New-Object System.Text.UTF8Encoding $false
            $w = New-Object System.IO.StreamWriter($proc.StandardInput.BaseStream, $utf8NoBom)
            $w.NewLine = "`n"
            $w.Write($StdinText)
            $w.Flush()
            $w.Close()
        } else {
            $proc.StandardInput.Close()
        }
        $exited = $proc.WaitForExit($TimeoutMs)
        if (-not $exited) {
            Stop-ProcessTree -ProcessId $proc.Id
            try { [void]$stdoutTask.Wait($script:KillDrainWaitMs) } catch { }
            try { [void]$stderrTask.Wait($script:KillDrainWaitMs) } catch { }
            try { [void]$proc.WaitForExit($script:KillDrainWaitMs) } catch { }
            $exitText = 'STILL_RUNNING'
            try {
                if ($proc.HasExited) { $exitText = [string]$proc.ExitCode }
            } catch { }
            return @{
                TimedOut = $true
                ExitCode = -1
                ExitCodeText = $exitText
                StdOut = (Get-TaskText -Task $stdoutTask -Name 'stdout')
                StdErr = (Get-TaskText -Task $stderrTask -Name 'stderr')
                DrainStarted = $true
            }
        }
        try { [void]$stdoutTask.Wait($script:DrainWaitMs) } catch { }
        try { [void]$stderrTask.Wait($script:DrainWaitMs) } catch { }
        $code = -1
        try { $code = $proc.ExitCode } catch { }
        return @{
            TimedOut = $false
            ExitCode = $code
            ExitCodeText = [string]$code
            StdOut = (Get-TaskText -Task $stdoutTask -Name 'stdout')
            StdErr = (Get-TaskText -Task $stderrTask -Name 'stderr')
            DrainStarted = $true
        }
    } catch {
        if ($started) {
            try { Stop-ProcessTree -ProcessId $proc.Id } catch { }
            try { if ($null -ne $stdoutTask) { [void]$stdoutTask.Wait(2000) } } catch { }
            try { if ($null -ne $stderrTask) { [void]$stderrTask.Wait(2000) } } catch { }
        }
        return @{
            TimedOut = $false
            ExitCode = -1
            ExitCodeText = 'START_ERROR'
            StdOut = (Get-TaskText -Task $stdoutTask -Name 'stdout')
            StdErr = ((Get-TaskText -Task $stderrTask -Name 'stderr') + [Environment]::NewLine + [string]$_.Exception.Message)
            DrainStarted = ($null -ne $stdoutTask)
        }
    }
}

function Write-Log([string]$Line) {
    Add-Content -LiteralPath $OutLog -Value $Line -Encoding UTF8
}

function Write-AuditBlock([string]$Title, [string]$Body) {
    Write-Log ('----- ' + $Title + ' -----')
    if ([string]::IsNullOrEmpty($Body)) {
        Write-Log '(empty)'
        return
    }
    $lines = $Body -split "(`r`n|`n)"
    foreach ($ln in $lines) {
        if ($ln -match '^(AWS_|SECRET|TOKEN|PASSWORD|API_KEY|EXPECT_AI_API|X-AI-Key)') {
            Write-Log 'REDACTED_SECRET_LINE'
            continue
        }
        if ($ln -match '^[A-Za-z0-9+/]{80,}={0,2}$') {
            Write-Log 'REDACTED_BASE64_LINE'
            continue
        }
        Write-Log $ln
    }
}

function Get-SshOptString([string]$Pem) {
    return ('-i "' + $Pem + '" -o BatchMode=yes -o ConnectTimeout=15 -o ConnectionAttempts=3 -o ServerAliveInterval=5 -o ServerAliveCountMax=3')
}

Set-Content -LiteralPath $OutLog -Value 'PRODUCTION_DISABLED_POST_HUNK_ONLY_STEP1_OWNER_DEPLOY_EXECUTION_V3_20260913' -Encoding UTF8
Write-Log ('STARTED=' + (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'))
Write-Log 'WRAPPER_VERSION=owner_deploy_step1_v3_20260913'
Write-Log 'HUNK_ONLY_V1_NOT_OVERWRITTEN=YES'
Write-Log 'HUNK_ONLY_V2_NOT_OVERWRITTEN=YES'
Write-Log 'HUNK_ONLY_V3_NOT_OVERWRITTEN=YES'
Write-Log 'REMOTE_HARD_DEADLINE_S=300'
Write-Log 'WRAPPER_TIMEOUT_MS=400000'
Write-Log 'DRAIN_WAIT_MS=20000'
Write-Log 'KILL_DRAIN_WAIT_MS=8000'
Write-Log 'SAFETY_BUFFER_MS=40000'
Write-Log 'POST_ENABLE_IN_THIS_PACK=NO'
Write-Log 'MIGRATE=NO'
Write-Log '022_REAPPLY=NO'
Write-Log 'ENV_CHANGED=NO'
Write-Log 'SYSTEMD_CHANGED=NO'
Write-Log 'SUDO_INVOKED=NO'
Write-Log 'OLD_EXECUTION_PACK_RERUN_ALLOWED=NO'
Write-Log 'V2_RERUN_ALLOWED=NO'
Write-Log 'PACK_VERSION=v3'
Write-Log 'SCP_USED=NO'
Write-Log 'REMOTE_MKDIR_FROM_WRAPPER=NO'
Write-Log 'SSH_STARTED=NO'
Write-Log 'PRODUCTION_CODE_DEPLOY_ALLOWED=NO'
Write-Log 'OWNER_DEPLOY_APPROVED=NO'
Write-Log 'POST_CODE_PRODUCTION_DEPLOYED=NO'
Write-Log 'WRAPPER_SETS_OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED=NO'
Write-Log 'WRAPPER_SETS_OWNER_PRODUCTION_STEP1_V2_DEPLOY_APPROVED=NO'
Write-Log 'WRAPPER_SETS_OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED=NO'
Write-Log 'WRAPPER_FORWARDS_OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED=NO'
Write-Log 'WRAPPER_FORWARDS_OWNER_PRODUCTION_STEP1_V2_DEPLOY_APPROVED=NO'
Write-Log ('OUTPUT=' + $OutLog)

$shaGate = Test-PackPayloadSha -PackRootPath $PackRoot -SumsPath $SumsFile -FlagsPath $FlagsFile -PayloadPath $StdinPy
Write-Log ('PACK_SHA_GATE=' + $(if ($shaGate.Ok) { 'PASS' } else { 'FAIL' }))
Write-Log ('PACK_SHA_GATE_REASON=' + [string]$shaGate.Reason)
if ($shaGate.ContainsKey('PayloadSha')) {
    Write-Log ('STDIN_PAYLOAD_SHA256=' + [string]$shaGate.PayloadSha)
}
if ($shaGate.ContainsKey('FilesChecked')) {
    Write-Log ('PACK_SHA_FILES_CHECKED=' + [string]$shaGate.FilesChecked)
}
if (-not $shaGate.Ok) {
    Write-Log 'SSH_STARTED=NO'
    Write-Log ('HALT_REASON=' + [string]$shaGate.Reason)
    Write-Log 'OWNER_DEPLOY_STATUS=FAIL'
    Write-Log 'DEPLOY_EXECUTED=NO'
    Write-Log ('FINISHED=' + (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'))
    Write-Output 'OWNER_DEPLOY_STATUS=FAIL'
    Write-Output ('HALT_REASON=' + [string]$shaGate.Reason)
    Write-Output 'SSH_STARTED=NO'
    Write-Output ('OUTPUT=' + $OutLog)
    exit 2
}

$v1Approved = [string]$env:OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED
$v2Approved = [string]$env:OWNER_PRODUCTION_STEP1_V2_DEPLOY_APPROVED
$approvedText = [string]$env:OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED
if ((($v1Approved -eq '1') -or ($v2Approved -eq '1')) -and $approvedText -ne '1') {
    Write-Log 'SSH_STARTED=NO'
    Write-Log 'HALT_REASON=OLD_EXECUTION_PACK_RERUN_REFUSED'
    Write-Log 'OWNER_DEPLOY_STATUS=FAIL'
    Write-Output 'OWNER_DEPLOY_STATUS=FAIL'
    Write-Output 'HALT_REASON=OLD_EXECUTION_PACK_RERUN_REFUSED'
    Write-Output 'SSH_STARTED=NO'
    Write-Output ('OUTPUT=' + $OutLog)
    exit 2
}
$gate = Test-OwnerApprovalReady -Approved $approvedText
Write-Log 'WINDOWS_ENV_IS_NOT_PRODUCTION_EVIDENCE=YES'
Write-Log ('APPROVAL_READY=' + $(if ($gate.Ready) { 'YES' } else { 'NO' }))
Write-Log ('APPROVAL_GATE_REASON=' + [string]$gate.Reason)
if (-not $gate.Ready) {
    Write-Log 'SSH_STARTED=NO'
    Write-Log ('HALT_REASON=' + [string]$gate.Reason)
    Write-Log 'OWNER_DEPLOY_STATUS=FAIL'
    Write-Log 'DEPLOY_EXECUTED=NO'
    Write-Log 'PRODUCTION_CODE_DEPLOY_ALLOWED=NO'
    Write-Log ('FINISHED=' + (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'))
    Write-Output 'OWNER_DEPLOY_STATUS=FAIL'
    Write-Output ('HALT_REASON=' + [string]$gate.Reason)
    Write-Output 'SSH_STARTED=NO'
    Write-Output ('OUTPUT=' + $OutLog)
    exit 2
}

if (-not (Test-Path -LiteralPath $StdinPy)) {
    Write-Log 'HALT_REASON=STDIN_PY_MISSING_ON_WINDOWS_PACK'
    Write-Output 'OWNER_DEPLOY_STATUS=FAIL'
    Write-Output 'HALT_REASON=STDIN_PY_MISSING_ON_WINDOWS_PACK'
    Write-Output ('OUTPUT=' + $OutLog)
    exit 2
}

$StdinBytes = [System.IO.File]::ReadAllBytes($StdinPy)
$payloadSha = Get-Sha256Hex -Bytes $StdinBytes
Write-Log ('STDIN_PAYLOAD_SHA256=' + $payloadSha)
Write-Log 'STDIN_CONCATENATED_AT_RUNTIME=NO'
Write-Log 'STDIN_SOURCE=owner_deploy_stdin.py'
# Forward only the Owner-set value 1. Wrapper never assigns the Windows env.
# Do not forward EXPECT_AI_ALLOW_MIGRATION_022/019 or PREDICTION_RUNS_ENABLED.
$remoteCmd = 'OWNER_PRODUCTION_STEP1_V3_DEPLOY_APPROVED=1 PYTHONDONTWRITEBYTECODE=1 python3 -'
$sshOpt = Get-SshOptString $Key
$remoteArgs = $sshOpt + ' ' + $Target + ' ' + $remoteCmd
Write-Log 'SSH_STARTED=YES'
Write-Log 'STDIN_PYTHON=YES'
Write-Log 'REMOTE_COMMAND=python3 -'
$remote = Invoke-TimedProcess -FileName 'ssh' -Arguments $remoteArgs -TimeoutMs $TimeoutMs -StdinBytes $StdinBytes
Write-Log ('SSH_TIMEOUT=' + $(if ($remote.TimedOut) { 'YES' } else { 'NO' }))
Write-Log ('SSH_EXIT_RAW=' + $remote.ExitCodeText)
Write-AuditBlock 'REMOTE_STDOUT' $remote.StdOut
if ($remote.StdErr) { Write-AuditBlock 'REMOTE_STDERR' $remote.StdErr }

$remoteState = Get-RemoteDeployState -StdOut ([string]$remote.StdOut)
Write-Log ('REMOTE_DEPLOY_EXECUTED=' + [string]$remoteState.DeployExecuted)
Write-Log ('REMOTE_DEPLOY_PHASE=' + [string]$remoteState.DeployPhase)
Write-Log ('REMOTE_RESTART_EXECUTED=' + [string]$remoteState.RestartExecuted)
$st = Get-WrapperAuditStatus -TimedOut $remote.TimedOut -ExitCodeText $remote.ExitCodeText
if ($remote.TimedOut) {
    Write-Log 'PARTIAL_STDOUT_SAVED=YES'
    Write-Log 'PARTIAL_STDERR_SAVED=YES'
    $committedKnown = (($remoteState.DeployExecuted -eq 'YES') -and ($remoteState.DeployPhase -eq 'VERIFIED'))
    Write-Log ('COMMITTED_STATE_KNOWN_AFTER_TIMEOUT=' + $(if ($committedKnown) { 'YES' } else { 'NO' }))
}
Write-Log ('AUDIT_STATUS=' + $st.Status)
Write-Log ('SSH_EXIT=' + $st.SshExit)
Write-Log 'PRODUCTION_CODE_DEPLOY_ALLOWED=NO'
Write-Log 'POST_CODE_PRODUCTION_DEPLOYED=NO'
Write-Log ('FINISHED=' + (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'))
Write-Output ('AUDIT_STATUS=' + $st.Status)
Write-Output ('SSH_EXIT=' + $st.SshExit)
Write-Output ('OUTPUT=' + $OutLog)
Write-Output 'PRODUCTION_CODE_DEPLOY_ALLOWED=NO'
exit $st.WrapperExit
