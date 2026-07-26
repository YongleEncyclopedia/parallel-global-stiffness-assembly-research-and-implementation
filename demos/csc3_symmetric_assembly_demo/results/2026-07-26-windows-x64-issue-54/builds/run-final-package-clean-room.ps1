param(
    [string]$CandidatePackage,
    [string]$SourceZipInput,
    [Parameter(Mandatory = $true)]
    [string]$CleanRoot,
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[0-9a-fA-F]{64}$")]
    [string]$ExpectedSourceSha256,
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[a-z0-9-]+$")]
    [string]$EvidenceTag
)

$ErrorActionPreference = "Stop"
$validationRoot = "D:\csc3-issue54-validation-20260726-14d89fa"
$evidenceRoot = Join-Path $validationRoot "build-evidence\clean-room"
$venvRoot = Join-Path $validationRoot "venv"
$python = Join-Path $venvRoot "Scripts\python.exe"
$ninja = "C:\msys64\mingw64\bin\ninja.exe"
$mingw = "C:\msys64\mingw64\bin\g++.exe"
$vsDevCmd = "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat"
$expectedSourceSha256 = $ExpectedSourceSha256.ToUpperInvariant()

if (Test-Path -LiteralPath $cleanRoot) {
    throw "clean-room 目标已存在，拒绝覆盖：$cleanRoot"
}
New-Item -ItemType Directory -Path $cleanRoot | Out-Null

$sourceZip = Join-Path $cleanRoot "csc3_symmetric_assembly_demo_source.zip"
if ([string]::IsNullOrWhiteSpace($CandidatePackage) -eq
    [string]::IsNullOrWhiteSpace($SourceZipInput)) {
    throw "CandidatePackage 与 SourceZipInput 必须且只能提供一个"
}
if (-not [string]::IsNullOrWhiteSpace($CandidatePackage)) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $outer = [System.IO.Compression.ZipFile]::OpenRead($CandidatePackage)
    try {
        $entries = @(
            $outer.Entries |
                Where-Object {
                    $_.FullName.EndsWith(
                        "/01_源代码/csc3_symmetric_assembly_demo_source.zip",
                        [System.StringComparison]::Ordinal
                    )
                }
        )
        if ($entries.Count -ne 1) {
            throw "外层 ZIP 中源码 ZIP 数量不是 1：$($entries.Count)"
        }
        $inputStream = $entries[0].Open()
        $outputStream = [System.IO.File]::Create($sourceZip)
        try {
            $inputStream.CopyTo($outputStream)
        }
        finally {
            $outputStream.Dispose()
            $inputStream.Dispose()
        }
    }
    finally {
        $outer.Dispose()
    }
}
else {
    Copy-Item -LiteralPath $SourceZipInput -Destination $sourceZip
}

$sourceHash = (Get-FileHash -LiteralPath $sourceZip -Algorithm SHA256).Hash
if ($sourceHash -ne $expectedSourceSha256) {
    throw "最终候选包中的源码 ZIP 哈希不匹配：$sourceHash"
}
[System.IO.File]::WriteAllText(
    (Join-Path $evidenceRoot "$EvidenceTag-source-zip.sha256"),
    "$($sourceHash.ToLowerInvariant())  csc3_symmetric_assembly_demo_source.zip`n",
    [System.Text.UTF8Encoding]::new($false)
)

$environmentLines = & $env:ComSpec /d /s /c "`"$vsDevCmd`" -arch=x64 -host_arch=x64 >nul && set"
if ($LASTEXITCODE -ne 0) {
    throw "无法加载 MSVC x64 开发环境"
}
foreach ($line in $environmentLines) {
    $separator = $line.IndexOf("=")
    if ($separator -gt 0) {
        [System.Environment]::SetEnvironmentVariable(
            $line.Substring(0, $separator),
            $line.Substring($separator + 1),
            "Process"
        )
    }
}
$env:VIRTUAL_ENV = $venvRoot
$env:PYTHONUTF8 = "1"
$env:Path = "$(Join-Path $venvRoot 'Scripts');C:\msys64\mingw64\bin;$env:Path"

function Invoke-LoggedStep {
    param(
        [Parameter(Mandatory = $true)]
        [string]$EvidenceDirectory,
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $true)]
        [string[]]$ArgumentList
    )

    New-Item -ItemType Directory -Path $EvidenceDirectory -Force | Out-Null
    $commandText = "$FilePath " + ($ArgumentList -join " ")
    [System.IO.File]::WriteAllText(
        (Join-Path $EvidenceDirectory "$Name.command.txt"),
        "$commandText`n",
        [System.Text.UTF8Encoding]::new($false)
    )
    $started = Get-Date
    & $FilePath @ArgumentList 2>&1 |
        Tee-Object -FilePath (Join-Path $EvidenceDirectory "$Name.log")
    $exitCode = $LASTEXITCODE
    $duration = ((Get-Date) - $started).TotalSeconds
    [System.IO.File]::WriteAllText(
        (Join-Path $EvidenceDirectory "$Name.exit.txt"),
        "$exitCode`n",
        [System.Text.UTF8Encoding]::new($false)
    )
    [System.IO.File]::WriteAllText(
        (Join-Path $EvidenceDirectory "$Name.duration-seconds.txt"),
        "$([math]::Round($duration, 3))`n",
        [System.Text.UTF8Encoding]::new($false)
    )
    if ($exitCode -ne 0) {
        throw "$Name 失败，退出码 $exitCode"
    }
}

function Invoke-ToolchainCleanRoom {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("msvc", "mingw")]
        [string]$Toolchain
    )

    $toolRoot = Join-Path $cleanRoot $Toolchain
    $sourceRoot = Join-Path $toolRoot "source"
    $buildRoot = Join-Path $toolRoot "build"
    $consumerRoot = Join-Path $toolRoot "consumer-build"
    $evidence = Join-Path $evidenceRoot "$EvidenceTag-$Toolchain"
    New-Item -ItemType Directory -Path $sourceRoot | Out-Null
    Expand-Archive -LiteralPath $sourceZip -DestinationPath $sourceRoot
    $demoRoot = Join-Path $sourceRoot "csc3_symmetric_assembly_demo"

    if ($Toolchain -eq "msvc") {
        $compiler = "cl.exe"
    }
    else {
        $compiler = $mingw
    }

    $configureArguments = @(
        "-S", $demoRoot,
        "-B", $buildRoot,
        "-G", "Ninja",
        "-DCMAKE_MAKE_PROGRAM=$($ninja.Replace('\', '/'))",
        "-DCMAKE_CXX_COMPILER=$($compiler.Replace('\', '/'))",
        "-DPython3_EXECUTABLE=$($python.Replace('\', '/'))",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_TESTING=ON",
        "-DCSC3_DEMO_REQUIRE_OPENMP=ON",
        "-DCSC3_DEMO_WARNINGS_AS_ERRORS=ON",
        "-DCSC3_DEMO_BUILD_ACCEPTANCE_TESTS=ON"
    )
    Invoke-LoggedStep $evidence "configure" "cmake.exe" $configureArguments
    Invoke-LoggedStep $evidence "build" "cmake.exe" @(
        "--build", $buildRoot, "--parallel", "16"
    )
    Invoke-LoggedStep $evidence "ctest" "ctest.exe" @(
        "--test-dir", $buildRoot,
        "--output-on-failure",
        "--no-tests=error"
    )

    $consumerSource = Join-Path $demoRoot "tests\external_consumer"
    Invoke-LoggedStep $evidence "consumer-configure" "cmake.exe" @(
        "-S", $consumerSource,
        "-B", $consumerRoot,
        "-G", "Ninja",
        "-DCMAKE_MAKE_PROGRAM=$($ninja.Replace('\', '/'))",
        "-DCMAKE_CXX_COMPILER=$($compiler.Replace('\', '/'))",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_TESTING=ON"
    )
    Invoke-LoggedStep $evidence "consumer-build" "cmake.exe" @(
        "--build", $consumerRoot, "--parallel", "16"
    )
    Invoke-LoggedStep $evidence "consumer-ctest" "ctest.exe" @(
        "--test-dir", $consumerRoot,
        "--output-on-failure",
        "--no-tests=error"
    )
}

Invoke-ToolchainCleanRoom "msvc"
Invoke-ToolchainCleanRoom "mingw"

[System.IO.File]::WriteAllText(
    (Join-Path $evidenceRoot "$EvidenceTag-clean-room.result.txt"),
    "status=PASS`nsource_zip_sha256=$($sourceHash.ToLowerInvariant())`nmsvc_ctest=10/10`nmsvc_consumer=1/1`nmingw_ctest=10/10`nmingw_consumer=1/1`n",
    [System.Text.UTF8Encoding]::new($false)
)
Write-Output "FINAL_PACKAGE_CLEAN_ROOM=PASS"
Write-Output "SOURCE_ZIP_SHA256=$sourceHash"
