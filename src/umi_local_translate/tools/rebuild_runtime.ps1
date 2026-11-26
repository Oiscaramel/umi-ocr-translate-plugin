# Rebuild runtime\site-packages for the portable Umi-OCR translation plugin.
# Requires: uv (https://docs.astral.sh/uv/)
#
#   powershell -ExecutionPolicy Bypass -File tools\rebuild_runtime.ps1
#
param(
    [string]$Index = "https://pypi.tuna.tsinghua.edu.cn/simple",
    [switch]$Model
)

$ErrorActionPreference = "Stop"

$plugin  = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $plugin "runtime"
$pyDir   = Join-Path $runtime "python"
$site    = Join-Path $runtime "site-packages"
$pyExe   = Join-Path $pyDir "python.exe"

Write-Host "plugin : $plugin"

if (-not (Test-Path $pyExe)) {
    throw "runtime\python\python.exe not found. The folder is incomplete; copy the whole plugin folder again."
}

$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    throw "uv not found. Install it first: pip install uv   (or: winget install astral-sh.uv)"
}

Write-Host "uv     : $($uv.Source)"
Write-Host "python : $pyExe"
Write-Host "index  : $Index"

if (Test-Path $site) { Remove-Item -Recurse -Force $site }
New-Item -ItemType Directory -Force -Path $site | Out-Null

& $uv.Source pip install --target $site --python $pyExe --link-mode copy --no-deps `
    --index-url $Index `
    ctranslate2==4.9.1 numpy==2.5.5 tokenizers==0.23.3 pyyaml==6.0.4

if ($LASTEXITCODE -ne 0) { throw "pip install failed ($LASTEXITCODE)" }

Write-Host "site-packages rebuilt."
& $pyExe -c "import sys; sys.path.insert(0, r'$site'); import ctranslate2, tokenizers, numpy; print('runtime ok', ctranslate2.__version__)"

if ($Model) {
    Write-Host "Downloading model from hf-mirror..."
    $dir  = Join-Path $plugin "models\nllb-200-distilled-600M-int8"
    $base = "https://hf-mirror.com/JustFrederik/nllb-200-distilled-600M-ct2-int8/resolve/main"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    foreach ($f in @("config.json","tokenizer_config.json","special_tokens_map.json","shared_vocabulary.txt","tokenizer.json","model.bin")) {
        Write-Host "  -> $f"
        & curl.exe -L --retry 5 --retry-delay 3 -C - --silent --show-error -o (Join-Path $dir $f) "$base/$f"
        if ($LASTEXITCODE -ne 0) { throw "download failed: $f" }
    }
}

Write-Host ""
Write-Host "Done. Now run: runtime\python\python.exe service\selftest.py"
