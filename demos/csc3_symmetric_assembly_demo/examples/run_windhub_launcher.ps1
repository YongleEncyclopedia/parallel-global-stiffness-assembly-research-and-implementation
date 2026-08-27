[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("full", "presentation")]
    [string]$Mode
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"
$scriptPath = Join-Path $PSScriptRoot "run_windhub.py"

function Stop-WithFailure([string]$Message) {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss-ffffff"
    $failureRoot = Join-Path ([System.IO.Path]::GetTempPath()) "csc3-windhub-example-failures\$timestamp"
    New-Item -ItemType Directory -Path $failureRoot -Force | Out-Null
    $failurePath = Join-Path $failureRoot "failure.json"
    [ordered]@{
        schema_version = "csc3-windhub-example-failure-v1"
        status = "FAIL"
        recorded_at_utc = [DateTime]::UtcNow.ToString("o")
        error_type = "PythonPreflight"
        message = $Message
    } | ConvertTo-Json | Set-Content -LiteralPath $failurePath -Encoding UTF8
    [Console]::Error.WriteLine("错误：$Message")
    [Console]::Error.WriteLine("失败记录：$failurePath")
    exit 1
}

$launcher = Get-Command py.exe -ErrorAction SilentlyContinue
if ($null -ne $launcher) {
    $launcherArguments = @("-3")
} else {
    $launcher = Get-Command python.exe -ErrorAction SilentlyContinue
    $launcherArguments = @()
}

if ($null -eq $launcher) {
    Stop-WithFailure "没有找到 Python。请安装 Python 3.10 或更高版本，并勾选 Add Python to PATH。"
}

& $launcher.Source @launcherArguments -c "import struct,sys; raise SystemExit(3 if sys.version_info < (3, 10) else 4 if struct.calcsize('P') != 8 else 0)"
if ($LASTEXITCODE -eq 3) {
    Stop-WithFailure "当前 Python 版本低于 3.10，请升级后重新运行。"
}
if ($LASTEXITCODE -eq 4) {
    Stop-WithFailure "当前是 32 位 Python。请安装 64 位 Python 3.10 或更高版本。"
}
if ($LASTEXITCODE -ne 0) {
    Stop-WithFailure "Python 无法正常启动，请修复或重新安装 64 位 Python 3.10 以上版本。"
}

& $launcher.Source @launcherArguments $scriptPath --mode $Mode
exit $LASTEXITCODE
