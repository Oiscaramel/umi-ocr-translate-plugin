# Build the portable plugin folder: build\umi_local_translate
#
#   powershell -ExecutionPolicy Bypass -File build.ps1
#   powershell -ExecutionPolicy Bypass -File build.ps1 -RefreshRuntime -RefreshModel
#
param(
    [switch]$RefreshRuntime,
    [switch]$RefreshModel,
    [string]$Index = "https://pypi.tuna.tsinghua.edu.cn/simple"
)

$ErrorActionPreference = "Stop"
$root  = $PSScriptRoot
$src   = Join-Path $root "src\umi_local_translate"
$vendorPy = Join-Path $root "vendor\python"
$vendorSp = Join-Path $root "vendor\site-packages"
$models   = Join-Path $root "models"
$modelDir = Join-Path $models "nllb-200-distilled-600M-int8"
$out   = Join-Path $root "build\umi_local_translate"

Write-Host "== project: $root"

# ---------------------------------------------------------------- 1. python
if ($RefreshRuntime -or -not (Test-Path (Join-Path $vendorPy "python.exe"))) {
    Write-Host "== fetching CPython 3.12 standalone via uv"
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uv) { throw "uv not found. Install: pip install uv" }
    & $uv.Source python install 3.12
    $found = & $uv.Source python find 3.12
    $pyRoot = Split-Path -Parent $found
    if (Test-Path $vendorPy) { Remove-Item -Recurse -Force $vendorPy }
    Copy-Item -Recurse $pyRoot $vendorPy
    foreach ($d in @("Lib\site-packages","Lib\ensurepip","Lib\idlelib","Lib\turtledemo","Lib\tkinter","tcl","include","libs","Lib\__pycache__")) {
        $p = Join-Path $vendorPy $d
        if (Test-Path $p) { Remove-Item -Recurse -Force $p }
    }
    foreach ($f in @("DLLs\_tkinter.pyd","DLLs\tcl86t.dll","DLLs\tk86t.dll")) {
        $p = Join-Path $vendorPy $f
        if (Test-Path $p) { Remove-Item -Force $p }
    }
}

# ------------------------------------------------------------ 2. deps
if ($RefreshRuntime -or -not (Test-Path (Join-Path $vendorSp "ctranslate2"))) {
    Write-Host "== installing runtime dependencies"
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uv) { throw "uv not found. Install: pip install uv" }
    if (Test-Path $vendorSp) { Remove-Item -Recurse -Force $vendorSp }
    & $uv.Source pip install --target $vendorSp --python (Join-Path $vendorPy "python.exe") --link-mode copy --no-deps --index-url $Index ctranslate2==4.9.1 numpy==2.5.5 tokenizers==0.23.3 pyyaml==6.0.4
    if ($LASTEXITCODE -ne 0) { throw "dependency install failed" }
}

# ------------------------------------------------------------ 3. model
$modelFiles = @("model.bin","config.json","tokenizer.json","tokenizer_config.json","special_tokens_map.json","shared_vocabulary.txt")
$modelOk = $true
foreach ($f in $modelFiles) { if (-not (Test-Path (Join-Path $modelDir $f))) { $modelOk = $false } }
if ($RefreshModel -or -not $modelOk) {
    Write-Host "== downloading NLLB-200 CT2 int8 model (hf-mirror)"
    New-Item -ItemType Directory -Force -Path $modelDir | Out-Null
    $base = "https://hf-mirror.com/JustFrederik/nllb-200-distilled-600M-ct2-int8/resolve/main"
    foreach ($f in $modelFiles) {
        if ($RefreshModel -or -not (Test-Path (Join-Path $modelDir $f))) {
            Write-Host "   -> $f"
            & curl.exe -L --retry 5 --retry-delay 3 -C - --silent --show-error -o (Join-Path $modelDir $f) "$base/$f"
            if ($LASTEXITCODE -ne 0) { throw "download failed: $f" }
        }
    }
}

# ------------------------------------------------------------ 4. assemble
Write-Host "== assembling $out"
if (Test-Path $out) { Remove-Item -Recurse -Force $out }
New-Item -ItemType Directory -Force -Path $out | Out-Null
Copy-Item -Recurse (Join-Path $src "*") $out
New-Item -ItemType Directory -Force -Path (Join-Path $out "runtime") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $out "models") | Out-Null
Copy-Item -Recurse $vendorPy (Join-Path $out "runtime\python")
Copy-Item -Recurse $vendorSp (Join-Path $out "runtime\site-packages")
Copy-Item -Recurse $modelDir (Join-Path $out "models\nllb-200-distilled-600M-int8")

# ------------------------------------------------------------ 5. selftest
Write-Host "== running selftest"
& (Join-Path $out "runtime\python\python.exe") (Join-Path $out "service\selftest.py")
if ($LASTEXITCODE -ne 0) { throw "selftest failed" }

$size = (Get-ChildItem $out -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
Write-Host ""
Write-Host ("Done. {0:N0} MB" -f $size)
Write-Host "Install with: powershell -ExecutionPolicy Bypass -File install.ps1"
