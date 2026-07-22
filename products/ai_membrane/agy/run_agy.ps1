<#
  run_agy.ps1 (packaged) — launch Antigravity CLI (agy) with the MetaSpace Warden guard active.

  Each run: rebuilds the patched Unleash feature set from the live backup, ensures the local mock
  Unleash server is up (DETACHED, so it survives this script and the agy session), sets UNLEASH_URL
  so agy's in-process Unleash client redirects to the mock (flipping json-hooks-enabled on), then
  launches agy. All paths are relative to this script's own folder ($PSScriptRoot).

  Usage:
    .\run_agy.ps1                 # launch agy, guard enforce (default)
    .\run_agy.ps1 -Mode dryrun    # observe-only
    .\run_agy.ps1 -Stop           # stop the background mock
    .\run_agy.ps1 -Status         # report mock state
#>
[CmdletBinding()]
param(
    [ValidateSet('enforce', 'dryrun')] [string]$Mode,
    [switch]$Stop, [switch]$Status,
    [Parameter(ValueFromRemainingArguments = $true)] $AgyArgs
)
$ErrorActionPreference = 'Stop'
$HERE = $PSScriptRoot
$PORT = 4242
$UNLEASH_URL = "http://127.0.0.1:$PORT/api"
$MOCK = Join-Path $HERE 'mock_unleash.py'
$BUILD = Join-Path $HERE 'build_features.py'
$PIDFILE = Join-Path $HERE '.mock.pid'

function Test-Port([int]$p) {
    $c = New-Object System.Net.Sockets.TcpClient
    try { $c.Connect('127.0.0.1', $p); return $true } catch { return $false } finally { $c.Close() }
}
function Stop-Mock {
    if (Test-Path $PIDFILE) {
        $procId = Get-Content $PIDFILE -ErrorAction SilentlyContinue
        if ($procId) { try { Stop-Process -Id ([int]$procId) -Force -ErrorAction Stop; Write-Host ">> mock stopped (pid $procId)" } catch { Write-Host ">> mock pid $procId not running" } }
        Remove-Item $PIDFILE -ErrorAction SilentlyContinue
    } else { Write-Host ">> no .mock.pid to stop" }
}
if ($Stop) { Stop-Mock; return }
if ($Status) {
    if (Test-Port $PORT) { $s = 'UP' } else { $s = 'DOWN' }
    Write-Host ">> mock on ${PORT}: $s"; Write-Host ">> UNLEASH_URL = $UNLEASH_URL"; return
}

Write-Host ">> rebuilding patched Unleash feature set ..."
& python $BUILD
if (Test-Port $PORT) {
    Write-Host ">> mock already listening on $PORT"
} else {
    Write-Host ">> starting mock Unleash (detached) ..."
    $p = Start-Process -FilePath 'python' -ArgumentList "`"$MOCK`"", "$PORT" -WindowStyle Hidden -PassThru
    $p.Id | Out-File -FilePath $PIDFILE -Encoding ascii
    $ok = $false
    for ($i = 0; $i -lt 25; $i++) { Start-Sleep -Milliseconds 200; if (Test-Port $PORT) { $ok = $true; break } }
    if ($ok) { Write-Host ">> mock up (pid $($p.Id))" } else { Write-Warning "mock did not come up on $PORT"; return }
}
$env:UNLEASH_URL = $UNLEASH_URL
if ($Mode) { $env:AGY_WARDEN_MODE = $Mode }
if ($env:AGY_WARDEN_MODE) { $effMode = $env:AGY_WARDEN_MODE } else { $effMode = 'enforce (default)' }
Write-Host ">> UNLEASH_URL = $UNLEASH_URL"
Write-Host ">> Warden mode = $effMode"
Write-Host ">> launching agy ...`n"
& agy @AgyArgs
