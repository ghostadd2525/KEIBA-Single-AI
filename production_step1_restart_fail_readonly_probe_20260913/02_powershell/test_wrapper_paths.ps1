# Local Parser.ParseFile + wrapper path fixtures. No SSH. No Production.
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$OwnerPs1 = Join-Path $Here 'OWNER_PROBE.ps1'
$fail = 0

function Expect([bool]$Cond, [string]$Name) {
    if ($Cond) {
        Write-Output ('PASS ' + $Name)
    } else {
        Write-Output ('FAIL ' + $Name)
        $script:fail++
    }
}

Write-Output ('PS_EDITION=' + [string]$PSVersionTable.PSEdition)
Write-Output ('PS_VERSION=' + [string]$PSVersionTable.PSVersion)
Write-Output ('PS_MAJOR=' + [string]$PSVersionTable.PSVersion.Major)

$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($OwnerPs1, [ref]$tokens, [ref]$parseErrors)
Expect ($parseErrors.Count -eq 0) 'parsefile_error_count_0'
if ($parseErrors.Count -ne 0) {
    foreach ($e in $parseErrors) {
        Write-Output ('PARSE_ERROR=' + [string]$e.ToString())
    }
}
Write-Output ('PARSE_ERROR_COUNT=' + [string]$parseErrors.Count)

$pred = {
    param($a)
    return ($a -is [System.Management.Automation.Language.FunctionDefinitionAst])
}
$fns = $ast.FindAll($pred, $true)
$needed = @('Stop-ProcessTree', 'Get-TaskText', 'Get-WrapperAuditStatus', 'Get-RemoteProbeState', 'Invoke-TimedProcess', 'Test-OwnerApprovalReady', 'Get-Sha256Hex', 'Test-PackPayloadSha')
foreach ($name in $needed) {
    $hit = $false
    foreach ($fn in $fns) {
        if ($fn.Name -eq $name) { $hit = $true }
    }
    Expect $hit ('ast_has_' + $name)
    if ($hit) {
        foreach ($fn in $fns) {
            if ($fn.Name -eq $name) {
                Invoke-Expression $fn.Extent.Text
            }
        }
    }
}

$invokeFn = $null
foreach ($fn in $fns) {
    if ($fn.Name -eq 'Invoke-TimedProcess') { $invokeFn = $fn }
}
if ($null -ne $invokeFn) {
    $body = [string]$invokeFn.Extent.Text
    $startI = $body.IndexOf('[void]$proc.Start()')
    $outI = $body.IndexOf('$stdoutTask = $proc.StandardOutput.ReadToEndAsync()')
    $errI = $body.IndexOf('$stderrTask = $proc.StandardError.ReadToEndAsync()')
    $waitI = $body.IndexOf('$proc.WaitForExit($TimeoutMs)')
    Expect (($startI -ge 0) -and ($outI -gt $startI) -and ($outI -lt $waitI)) 'ast_stdout_drain_before_wait'
    Expect (($startI -ge 0) -and ($errI -gt $startI) -and ($errI -lt $waitI)) 'ast_stderr_drain_before_wait'
    $tryCatch = $invokeFn.FindAll({
            param($a)
            return ($a -is [System.Management.Automation.Language.TryStatementAst])
        }, $true)
    Expect ($tryCatch.Count -ge 1) 'ast_outer_try_present'
}

$allText = [System.IO.File]::ReadAllText($OwnerPs1)
$shaI = $allText.IndexOf('$shaGate = Test-PackPayloadSha')
$gateI = $allText.IndexOf('$gate = Test-OwnerApprovalReady')
$sshI = $allText.IndexOf("Invoke-TimedProcess -FileName 'ssh'")
Expect (($shaI -ge 0) -and ($gateI -gt $shaI) -and ($sshI -gt $gateI)) 'sha_then_approval_before_ssh'
Expect ($allText.Contains('.Contains(') -eq $false) 'no_pscustomobject_contains'
Expect ($allText.Contains('scp ') -eq $false) 'no_scp'
Expect ($allText.Contains('sudo ') -eq $false) 'no_sudo'
Expect ($allText.Contains('SetEnvironmentVariable') -eq $false) 'no_setenv'
Expect ($allText.Contains('$env:OWNER_READONLY_STEP1_PROBE_APPROVED =') -eq $false) 'wrapper_does_not_set_approval'
Expect ($allText.Contains('$env:OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED =') -eq $false) 'wrapper_does_not_set_deploy_approval'
Expect ($allText.Contains('OWNER_PRODUCTION_STEP1_DEPLOY_APPROVED=1') -eq $false) 'wrapper_does_not_forward_deploy_approval'
Expect ($allText.Contains('python3 -') -eq $true) 'stdin_python3_dash'
Expect ($allText.Contains('ReadAllBytes') -eq $true) 'stdin_readallbytes'
Expect ($allText.Contains('owner_probe_stdin.py') -eq $true) 'reads_pregenerated_stdin'
Expect ($allText.Contains('WINDOWS_ENV_IS_NOT_PRODUCTION_EVIDENCE=YES') -eq $true) 'windows_env_not_prod_evidence'
Expect ($allText.Contains('__name__ = "backup_contract"') -eq $false) 'no_runtime_name_concat'

$script:KillDrainWaitMs = 2000
$script:DrainWaitMs = 5000
$td = Join-Path ([System.IO.Path]::GetTempPath()) ('probe1paths-' + [guid]::NewGuid().ToString('N'))
[void][System.IO.Directory]::CreateDirectory($td)
$okPy = Join-Path $td 'ok.py'
$nzPy = Join-Path $td 'nz.py'
$toPy = Join-Path $td 'to.py'
$committedToPy = Join-Path $td 'committed_to.py'
Set-Content -LiteralPath $okPy -Value "import sys`nsys.stdout.write('OKOUT')`nsys.stderr.write('OKERR')`nsys.exit(0)`n" -Encoding ASCII
Set-Content -LiteralPath $nzPy -Value "import sys`nsys.stdout.write('NZOUT')`nsys.stderr.write('NZERR')`nsys.exit(7)`n" -Encoding ASCII
Set-Content -LiteralPath $toPy -Value "import sys,time`nsys.stdout.write('PARTIAL')`nsys.stdout.flush()`ntime.sleep(20)`n" -Encoding ASCII
Set-Content -LiteralPath $committedToPy -Value "import sys,time`nsys.stdout.write('PROBE_EXECUTED=YES\nPROBE_PHASE=COMPLETE\nSYSTEMCTL_MUTATE_ISSUED=NO\n')`nsys.stdout.flush()`ntime.sleep(20)`n" -Encoding ASCII

$ok = Invoke-TimedProcess -FileName 'python3' -Arguments $okPy -TimeoutMs 15000 -StdinText $null
Expect (-not $ok.TimedOut) 'path_success_not_timeout'
Expect ($ok.ExitCodeText -eq '0') 'path_success_exit0'
Expect ($ok.DrainStarted -eq $true) 'path_success_drain_started'
Expect ([string]$ok.StdOut -match 'OKOUT') 'path_success_stdout'
Expect ([string]$ok.StdErr -match 'OKERR') 'path_success_stderr'
$stOk = Get-WrapperAuditStatus -TimedOut $false -ExitCodeText '0'
Expect ($stOk.Status -eq 'SUCCESS') 'path_success_wrapper'
Expect ($stOk.WrapperExit -eq 0) 'path_success_wrapper_exit'

$nz = Invoke-TimedProcess -FileName 'python3' -Arguments $nzPy -TimeoutMs 15000 -StdinText $null
Expect (-not $nz.TimedOut) 'path_nonzero_not_timeout'
Expect ($nz.ExitCodeText -eq '7') 'path_nonzero_exit7'
Expect ($nz.DrainStarted -eq $true) 'path_nonzero_drain_started'
Expect ([string]$nz.StdOut -match 'NZOUT') 'path_nonzero_stdout'
Expect ([string]$nz.StdErr -match 'NZERR') 'path_nonzero_stderr'
$stNz = Get-WrapperAuditStatus -TimedOut $false -ExitCodeText $nz.ExitCodeText
Expect ($stNz.Status -eq 'FAILED') 'path_nonzero_wrapper_failed'
Expect ($stNz.Reason -eq 'SSH_EXIT') 'path_nonzero_reason_ssh_exit'
Expect ($stNz.WrapperExit -eq 1) 'path_nonzero_wrapper_exit1'

$to = Invoke-TimedProcess -FileName 'python3' -Arguments $toPy -TimeoutMs 1500 -StdinText $null
Expect ($to.TimedOut -eq $true) 'path_timeout_flag'
Expect ($to.DrainStarted -eq $true) 'path_timeout_drain_started'
Expect ([string]$to.StdOut -match 'PARTIAL') 'path_timeout_partial_stdout'
$stTo = Get-WrapperAuditStatus -TimedOut $true -ExitCodeText $to.ExitCodeText
Expect ($stTo.Status -eq 'FAILED') 'path_timeout_wrapper_failed'
Expect ($stTo.Reason -eq 'TIMEOUT') 'path_timeout_reason'
Expect ($stTo.WrapperExit -eq 1) 'path_timeout_wrapper_exit1'
$unknownTo = Get-RemoteProbeState -StdOut ([string]$to.StdOut)
Expect ($unknownTo.ProbeExecuted -eq 'UNKNOWN') 'path_timeout_before_commit_executed_unknown'
Expect ($unknownTo.ProbePhase -eq 'UNKNOWN') 'path_timeout_before_commit_phase_unknown'

$cto = Invoke-TimedProcess -FileName 'python3' -Arguments $committedToPy -TimeoutMs 1500 -StdinText $null
Expect ($cto.TimedOut -eq $true) 'path_timeout_after_commit_flag'
Expect ($cto.DrainStarted -eq $true) 'path_timeout_after_commit_drain'
Expect ([string]$cto.StdOut -match 'PROBE_EXECUTED=YES') 'path_timeout_after_commit_executed_yes'
Expect ([string]$cto.StdOut -match 'PROBE_PHASE=COMPLETE') 'path_timeout_after_commit_phase_committed'
$knownTo = Get-RemoteProbeState -StdOut ([string]$cto.StdOut)
Expect ($knownTo.ProbeExecuted -eq 'YES') 'path_timeout_after_commit_state_executed'
Expect ($knownTo.ProbePhase -eq 'COMPLETE') 'path_timeout_after_commit_state_phase'
$stCto = Get-WrapperAuditStatus -TimedOut $true -ExitCodeText $cto.ExitCodeText
Expect ($stCto.Status -eq 'FAILED') 'path_timeout_after_commit_wrapper_failed'
Expect ($stCto.Reason -eq 'TIMEOUT') 'path_timeout_after_commit_reason'
Expect (-not (($knownTo.ProbeExecuted -eq 'UNKNOWN') -or ($knownTo.ProbePhase -eq 'UNKNOWN'))) 'path_timeout_after_commit_not_unknown'

$sf = Invoke-TimedProcess -FileName '/no/such/step1_ssh_binary' -Arguments '' -TimeoutMs 5000 -StdinText $null
Expect (-not $sf.TimedOut) 'path_startfail_not_timeout'
Expect ($sf.ExitCodeText -eq 'START_ERROR') 'path_startfail_code'
$stSf = Get-WrapperAuditStatus -TimedOut $false -ExitCodeText $sf.ExitCodeText
Expect ($stSf.Status -eq 'FAILED') 'path_startfail_wrapper_failed'
Expect ($stSf.Reason -eq 'SSH_EXIT') 'path_startfail_reason'

$g1 = Test-OwnerApprovalReady -Approved ''
Expect ($g1.Ready -eq $false) 'approval_unset_not_ready'
Expect ($g1.Reason -eq 'OWNER_READONLY_STEP1_PROBE_APPROVED_UNSET') 'approval_unset_reason'
$g4 = Test-OwnerApprovalReady -Approved '1'
Expect ($g4.Ready -eq $true) 'approval_ready_when_explicit'

Write-Output ('PATH_TEST_FAIL_COUNT=' + [string]$fail)
if ($fail -ne 0) { exit 1 }
exit 0
