# 自动编译和测试脚本 (PowerShell)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GPU 并行刚度矩阵组装 - 自动构建测试" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 设置环境变量
$env:PATH = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\bin;$env:PATH"
$env:PATH = "C:\Program Files\CMake\bin;$env:PATH"

# 设置 VS 环境
Write-Host "[1/5] 配置 Visual Studio 环境..." -ForegroundColor Yellow
Push-Location "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build"
cmd /c "vcvars64.bat&set" | ForEach-Object {
    if ($_ -match "=") {
        $v = $_.split("=", 2)
        [System.Environment]::SetEnvironmentVariable($v[0], $v[1])
    }
}
Pop-Location
Write-Host "✓ VS 环境配置完成" -ForegroundColor Green
Write-Host ""

# 验证工具
Write-Host "[2/5] 验证工具..." -ForegroundColor Yellow
$tools = @(
    @{Name="CMake"; Command="cmake --version"},
    @{Name="NVCC"; Command="nvcc --version"},
    @{Name="MSVC"; Command="cl"}
)

foreach ($tool in $tools) {
    try {
        $null = Invoke-Expression $tool.Command 2>&1
        Write-Host "  ✓ $($tool.Name): OK" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ $($tool.Name): 未找到" -ForegroundColor Red
        exit 1
    }
}
Write-Host ""

# 清理旧构建
Write-Host "[3/5] 清理并配置 CMake..." -ForegroundColor Yellow
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}
New-Item -ItemType Directory -Path "build" | Out-Null
Set-Location "build"

cmake .. -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ CMake 配置失败" -ForegroundColor Red
    Set-Location ..
    exit 1
}
Write-Host "✓ CMake 配置成功" -ForegroundColor Green
Write-Host ""

# 编译
Write-Host "[4/5] 编译项目..." -ForegroundColor Yellow
nmake
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ 编译失败" -ForegroundColor Red
    Set-Location ..
    exit 1
}
Write-Host "✓ 编译成功" -ForegroundColor Green
Write-Host ""

# 运行测试
Write-Host "[5/5] 运行基准测试..." -ForegroundColor Yellow
Write-Host "测试网格: 30x30x30 (约 48000 单元)" -ForegroundColor Gray
Set-Location ..

$exe = if (Test-Path "build\benchmark.exe") { "build\benchmark.exe" } else { "build\bin\Release\benchmark.exe" }
if (Test-Path $exe) {
    & $exe 30 30 30
} else {
    Write-Host "✗ 可执行文件未找到: $exe" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 显示结果
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "测试结果汇总" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$resultFiles = @("benchmark_results.csv", "build\benchmark_results.csv")
$found = $false
foreach ($file in $resultFiles) {
    if (Test-Path $file) {
        Get-Content $file
        $found = $true
        break
    }
}

if (-not $found) {
    Write-Host "警告: 未找到结果文件" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "构建和测试完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
