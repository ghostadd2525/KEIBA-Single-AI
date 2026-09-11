# PowerShell 5.1. Owner-only Production backup v2.
# Owner runs this file only. Cursor does not run this on Production.
# Python bytes are sent on SSH stdin. No SCP. No remote mkdir. No sudo.
# No persistent env change. No 022 APPLY. Wrapper never sets
# OWNER_PRODUCTION_BACKUP_APPROVED.
# v1 ZIP SHA256=35ef43ad03c0da93f76d85b3513ae8dcb32506468c22012e4bcd098ee6b33e19
# is CHANGES_REQUIRED audit trail and is not overwritten.
$ErrorActionPreference = 'Continue'
$Key = 'C:\Users\Mr.me\Downloads\expect-beta-tokyo.pem'
$Target = 'ubuntu@13.231.5.5'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$ContractPy = Join-Path $Here 'backup_contract.py'
$RemotePy = Join-Path $Here 'owner_backup_remote.py'
$Downloads = Join-Path $env:USERPROFILE 'Downloads'
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$OutLog = Join-Path $Downloads ('production_backup_owner_execution_v2_20260911_output_' + $Stamp + '.txt')
$TimeoutMs = 180000
$script:KillDrainWaitMs = 5000
$script:DrainWaitMs = 15000

if (Test-Path -LiteralPath $OutLog) {
    Write-Output 'OWNER_BACKUP_STATUS=FAIL'
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
        [string]$Approved,
        [string]$Migration022,
        [string]$PredictionRuns
    )
    if ($Approved -ne '1') {
        return @{
            Ready = $false
            Reason = 'OWNER_PRODUCTION_BACKUP_APPROVED_UNSET'
        }
    }
    $m = $Migration022.ToLower()
    if (($m -eq '1') -or ($m -eq 'true') -or ($m -eq 'yes')) {
        return @{
            Ready = $false
            Reason = 'EXPECT_AI_ALLOW_MIGRATION_022_SET'
        }
    }
    $p = $PredictionRuns.ToLower()
    if (($p -eq '1') -or ($p -eq 'true') -or ($p -eq 'yes')) {
        return @{
            Ready = $false
            Reason = 'PREDICTION_RUNS_ENABLED'
        }
    }
    return @{
        Ready = $true
        Reason = 'OK'
    }
}

function Invoke-TimedProcess {
    param(
        [string]$FileName,
        [string]$Arguments,
        [int]$TimeoutMs,
        [string]$StdinText
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
        if ($null -ne $StdinText) {
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

Set-Content -LiteralPath $OutLog -Value 'PRODUCTION_BACKUP_OWNER_EXECUTION_V2_20260911' -Encoding UTF8
Write-Log ('STARTED=' + (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'))
Write-Log 'WRAPPER_VERSION=owner_backup_v2_20260911'
Write-Log 'V1_PACK_CHANGES_REQUIRED=YES'
Write-Log 'V1_ZIP_OVERWRITE=NO'
Write-Log 'APPLY_PLAN_ZIP_OVERWRITE=NO'
Write-Log 'SSH_STARTED=NO'
Write-Log 'SCP_USED=NO'
Write-Log 'REMOTE_MKDIR_FROM_WRAPPER=NO'
Write-Log 'SUDO_INVOKED=NO'
Write-Log 'PERSISTENT_ENV_CHANGED=NO'
Write-Log 'MIGRATION_022_IN_THIS_PACK=NO'
Write-Log 'PRODUCTION_APPLY_READY=NO'
Write-Log 'OWNER_APPLY_APPROVED=NO'
Write-Log 'WRAPPER_SETS_OWNER_PRODUCTION_BACKUP_APPROVED=NO'
Write-Log ('OUTPUT=' + $OutLog)

$approvedText = [string]$env:OWNER_PRODUCTION_BACKUP_APPROVED
$mig022Text = [string]$env:EXPECT_AI_ALLOW_MIGRATION_022
$predText = [string]$env:PREDICTION_RUNS_ENABLED
$gate = Test-OwnerApprovalReady -Approved $approvedText -Migration022 $mig022Text -PredictionRuns $predText
Write-Log ('APPROVAL_READY=' + $(if ($gate.Ready) { 'YES' } else { 'NO' }))
Write-Log ('APPROVAL_GATE_REASON=' + [string]$gate.Reason)
if (-not $gate.Ready) {
    Write-Log 'SSH_STARTED=NO'
    Write-Log ('HALT_REASON=' + [string]$gate.Reason)
    Write-Log 'OWNER_BACKUP_STATUS=FAIL'
    Write-Log 'APPLY_PRECONDITION_BACKUP_PASS=NO'
    Write-Log 'PRODUCTION_APPLY_READY=NO'
    Write-Log 'MIGRATION_MAY_PROCEED=NO'
    Write-Log ('FINISHED=' + (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'))
    Write-Output 'OWNER_BACKUP_STATUS=FAIL'
    Write-Output ('HALT_REASON=' + [string]$gate.Reason)
    Write-Output 'SSH_STARTED=NO'
    Write-Output ('OUTPUT=' + $OutLog)
    exit 2
}

if (-not (Test-Path -LiteralPath $ContractPy)) {
    Write-Log 'HALT_REASON=CONTRACT_PY_MISSING_ON_WINDOWS_PACK'
    Write-Output 'OWNER_BACKUP_STATUS=FAIL'
    Write-Output 'HALT_REASON=CONTRACT_PY_MISSING_ON_WINDOWS_PACK'
    Write-Output ('OUTPUT=' + $OutLog)
    exit 2
}
if (-not (Test-Path -LiteralPath $RemotePy)) {
    Write-Log 'HALT_REASON=REMOTE_PY_MISSING_ON_WINDOWS_PACK'
    Write-Output 'OWNER_BACKUP_STATUS=FAIL'
    Write-Output 'HALT_REASON=REMOTE_PY_MISSING_ON_WINDOWS_PACK'
    Write-Output ('OUTPUT=' + $OutLog)
    exit 2
}

$ContractText = Get-Content -LiteralPath $ContractPy -Raw -Encoding UTF8
$RemoteText = Get-Content -LiteralPath $RemotePy -Raw -Encoding UTF8
$PyText = '__name__ = "backup_contract"' + "`n" + $ContractText + "`n" + '__name__ = "__main__"' + "`n" + $RemoteText
$fwdApproved = [string]$env:OWNER_PRODUCTION_BACKUP_APPROVED
$remoteCmd = 'OWNER_PRODUCTION_BACKUP_APPROVED=' + $fwdApproved + ' PYTHONDONTWRITEBYTECODE=1 python3 -'
$sshOpt = Get-SshOptString $Key
$remoteArgs = $sshOpt + ' ' + $Target + ' ' + $remoteCmd
Write-Log 'SSH_STARTED=YES'
Write-Log 'STDIN_PYTHON=YES'
Write-Log 'REMOTE_COMMAND=python3 -'
$remote = Invoke-TimedProcess -FileName 'ssh' -Arguments $remoteArgs -TimeoutMs $TimeoutMs -StdinText $PyText
Write-Log ('SSH_TIMEOUT=' + $(if ($remote.TimedOut) { 'YES' } else { 'NO' }))
Write-Log ('SSH_EXIT_RAW=' + $remote.ExitCodeText)
Write-AuditBlock 'REMOTE_STDOUT' $remote.StdOut
if ($remote.StdErr) { Write-AuditBlock 'REMOTE_STDERR' $remote.StdErr }

$st = Get-WrapperAuditStatus -TimedOut $remote.TimedOut -ExitCodeText $remote.ExitCodeText
if ($remote.TimedOut) {
    Write-Log 'PARTIAL_STDOUT_SAVED=YES'
    Write-Log 'PARTIAL_STDERR_SAVED=YES'
}
Write-Log ('AUDIT_STATUS=' + $st.Status)
Write-Log ('SSH_EXIT=' + $st.SshExit)
Write-Log 'PRODUCTION_APPLY_READY=NO'
Write-Log 'MIGRATION_MAY_PROCEED=NO'
Write-Log ('FINISHED=' + (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'))
Write-Output ('AUDIT_STATUS=' + $st.Status)
Write-Output ('SSH_EXIT=' + $st.SshExit)
Write-Output ('OUTPUT=' + $OutLog)
Write-Output 'PRODUCTION_APPLY_READY=NO'
exit $st.WrapperExit
