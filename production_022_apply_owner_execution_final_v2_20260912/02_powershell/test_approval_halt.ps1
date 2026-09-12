# Run OWNER_APPLY.ps1 without approval. Must not start SSH. Must write output.
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$OwnerPs1 = Join-Path $Here 'OWNER_APPLY.ps1'
$td = Join-Path ([System.IO.Path]::GetTempPath()) ('applyhalt-' + [guid]::NewGuid().ToString('N'))
[void][System.IO.Directory]::CreateDirectory($td)
$env:USERPROFILE = $td
Remove-Item Env:OWNER_PRODUCTION_022_APPLY_APPROVED -ErrorAction SilentlyContinue
Remove-Item Env:EXPECT_AI_ALLOW_MIGRATION_022 -ErrorAction SilentlyContinue
$env:PREDICTION_RUNS_ENABLED = '0'
$p = Start-Process -FilePath (Get-Command pwsh).Source -ArgumentList @('-NoProfile','-File', $OwnerPs1) -Wait -PassThru -NoNewWindow -RedirectStandardOutput (Join-Path $td 'out.txt') -RedirectStandardError (Join-Path $td 'err.txt')
$code = $p.ExitCode
$out = Get-Content -LiteralPath (Join-Path $td 'out.txt') -Raw -ErrorAction SilentlyContinue
$logs = @(Get-ChildItem -LiteralPath (Join-Path $td 'Downloads') -Filter 'production_022_apply_owner_execution_final_v2_20260912_output_*.txt' -ErrorAction SilentlyContinue)
$fail = 0
function Expect([bool]$Cond, [string]$Name) {
    if ($Cond) { Write-Output ('PASS ' + $Name) } else { Write-Output ('FAIL ' + $Name); $script:fail++ }
}
Expect ($code -eq 2) 'halt_exit_2'
Expect ([string]$out -match 'SSH_STARTED=NO') 'halt_stdout_ssh_no'
Expect ([string]$out -match 'OWNER_PRODUCTION_022_APPLY_APPROVED_UNSET') 'halt_reason_unset'
Expect ($logs.Count -eq 1) 'halt_output_file_created'
if ($logs.Count -eq 1) {
    $body = Get-Content -LiteralPath $logs[0].FullName -Raw
    Expect ([string]$body -match 'SSH_STARTED=NO') 'halt_log_ssh_no'
    Expect ([string]$body -notmatch 'REMOTE_STDOUT') 'halt_no_remote_stdout'
}
Write-Output ('HALT_TEST_FAIL_COUNT=' + [string]$fail)
if ($fail -ne 0) { exit 1 }
exit 0
