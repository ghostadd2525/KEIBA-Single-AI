# PowerShell 5.1. Owner-only. READ-ONLY Production Step 2-4 baseline / disabled-POST DRY_RUN v2.
# Syntax-only fix of v1. v1 ZIP is not overwritten. Do not run v1 (MissingCatchOrFinally).
# Cursor does not run this. Do not overwrite v1-v4 review ZIP. No Production writes.
# No SCP. No GitHub. No 019 apply. No POST.
# Remote Python may GET http://127.0.0.1:8000 only.
# Never POST /v1/prediction-runs. Never GET prediction detail by race_id.
$ErrorActionPreference = 'Continue'
$Key = 'C:\Users\Mr.me\Downloads\expect-beta-tokyo.pem'
$Target = 'ubuntu@13.231.5.5'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$AuditPy = Join-Path $Here 'baseline_disabled_post_dry_run.py'
$Downloads = Join-Path $env:USERPROFILE 'Downloads'
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$OutLog = Join-Path $Downloads ('production_prediction_run_baseline_disabled_post_dry_run_readonly_v2_20260911_output_' + $Stamp + '.txt')
$TimeoutMs = 180000
$script:KillDrainWaitMs = 5000
$script:DrainWaitMs = 15000

if (Test-Path -LiteralPath $OutLog) {
    Write-Output 'AUDIT_STATUS=FAILED'
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

Set-Content -LiteralPath $OutLog -Value 'PRODUCTION_PREDICTION_RUN_BASELINE_DISABLED_POST_DRY_RUN_READONLY_V2_20260911' -Encoding UTF8
Write-Log ('STARTED=' + (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'))
Write-Log 'WRAPPER_VERSION=owner_readonly_baseline_disabled_post_dry_run_v2_20260911'
Write-Log 'V1_PACK_DO_NOT_RUN=YES'
Write-Log 'V1_PACK_PARSE_ERROR=YES'
Write-Log 'V1_V4_REVIEW_ZIP_OVERWRITE=NO'
Write-Log 'V1_DRY_RUN_ZIP_OVERWRITE=NO'
Write-Log 'HISTORICAL_DB_RACE_LIVE_INFERENCE_ALLOWED=NO'
Write-Log 'DETAIL_GET_ALLOWED=NO'
Write-Log 'POST_ENDPOINT_CALLED=NO'
Write-Log 'MIGRATION_019_APPLY=NO'
Write-Log 'EXPECT_AI_ALLOW_MIGRATION_019_ENABLED=NO'
Write-Log 'CURSOR_EC2_CONNECT=NO'
Write-Log 'PRODUCTION_CHANGED=NO'
Write-Log 'GITHUB_CHANGED=NO'
Write-Log 'PR23_MERGED=NO'
Write-Log 'PR24_UPDATED=NO'
Write-Log 'FIND_USED=NO'
Write-Log 'REMOTE_MKDIR=NO'
Write-Log 'SCP_DOWNLOAD=NO'
Write-Log 'SCP_UPLOAD=NO'
Write-Log 'WRAPPER_PUBLIC_HTTP=NO'
Write-Log 'REMOTE_LOCALHOST_GET_ONLY=YES'
Write-Log 'SYSTEMD_MUTATING=NO'
Write-Log 'SUDO_INVOKED=NO'
Write-Log 'DB_CHANGED=0'
Write-Log 'BACKUP_COPY_EXECUTED=NO'
Write-Log 'OWNER_APPLY_APPROVED=NO'
Write-Log 'APPLY_EXECUTED=NO'
Write-Log 'PRODUCTION_DRY_RUN_READY=NO'
Write-Log 'PRODUCTION_APPLY_READY=NO'
Write-Log ('OUTPUT=' + $OutLog)

function Get-SshOptString([string]$Pem) {
    return ('-i "' + $Pem + '" -o BatchMode=yes -o ConnectTimeout=15 -o ConnectionAttempts=3 -o ServerAliveInterval=5 -o ServerAliveCountMax=3')
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
        Write-Log $ln
    }
}

$PyText = Get-Content -LiteralPath $AuditPy -Raw -Encoding UTF8
$sshOpt = Get-SshOptString $Key
$remoteCmd = 'PYTHONDONTWRITEBYTECODE=1 python3 -'
$remoteArgs = $sshOpt + ' ' + $Target + ' ' + $remoteCmd
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
Write-Log ('FINISHED=' + (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'))
Write-Output ('AUDIT_STATUS=' + $st.Status)
Write-Output ('SSH_EXIT=' + $st.SshExit)
Write-Output ('OUTPUT=' + $OutLog)
Write-Output 'V1_PACK_DO_NOT_RUN=YES'
Write-Output 'POST_ENDPOINT_CALLED=NO'
Write-Output 'PRODUCTION_DRY_RUN_READY=NO'
exit $st.WrapperExit
