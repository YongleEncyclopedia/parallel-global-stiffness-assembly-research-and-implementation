[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$launcherPath = Join-Path $PSScriptRoot "run_windhub_launcher.ps1"
& $launcherPath -Mode presentation
exit $LASTEXITCODE
