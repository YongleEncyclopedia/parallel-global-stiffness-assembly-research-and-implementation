$ErrorActionPreference = "Stop"
$repository = "D:\parallel-global-stiffness-assembly-research-and-implementation"
$validation = "D:\csc3-issue54-validation-20260726-14d89fa"
$venv = Join-Path $validation "venv"
$python = Join-Path $venv "Scripts\python.exe"
$stdout = Join-Path $validation "build-evidence\post-linkfix-python-suite.stdout.log"
$stderr = Join-Path $validation "build-evidence\post-linkfix-python-suite.stderr.log"
$exitFile = Join-Path $validation "build-evidence\post-linkfix-python-suite.exit.txt"
$resultFile = Join-Path $validation "build-evidence\post-linkfix-python-suite.result.txt"

$env:VIRTUAL_ENV = $venv
$env:PYTHONUTF8 = "1"
$env:Path = "$(Join-Path $venv 'Scripts');$env:Path"

$arguments = @(
    "-m", "unittest", "discover",
    "-s", "demos/csc3_symmetric_assembly_demo/tests/python",
    "-p", "test_*.py",
    "-v"
)
$started = Get-Date
$process = Start-Process `
    -FilePath $python `
    -ArgumentList $arguments `
    -WorkingDirectory $repository `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -Wait `
    -PassThru
$duration = ((Get-Date) - $started).TotalSeconds

[System.IO.File]::WriteAllText(
    $exitFile,
    "$($process.ExitCode)`n",
    [System.Text.UTF8Encoding]::new($false)
)
$status = if ($process.ExitCode -eq 0) { "PASS" } else { "FAIL" }
[System.IO.File]::WriteAllText(
    $resultFile,
    "status=$status`nexit_code=$($process.ExitCode)`nduration_seconds=$([math]::Round($duration, 3))`n",
    [System.Text.UTF8Encoding]::new($false)
)
exit $process.ExitCode
