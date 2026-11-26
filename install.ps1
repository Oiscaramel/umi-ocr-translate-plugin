# Install the plugin into Umi-OCR.
#
#   powershell -ExecutionPolicy Bypass -File install.ps1 -UmiData "D:\Umi-OCR\UmiOCR-data"
#
# The UmiOCR-data folder can also be passed via the UMI_OCR_DATA environment variable.
param(
    [string]$UmiData = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

if (-not $UmiData) { $UmiData = $env:UMI_OCR_DATA }
if (-not $UmiData) {
    throw "Please pass -UmiData, e.g.  -UmiData 'D:\Umi-OCR\UmiOCR-data'"
}

$root = $PSScriptRoot
$src  = Join-Path $root "build\umi_local_translate"

if (-not (Test-Path $src)) { throw "build\umi_local_translate not found. Run build.ps1 first." }
if (-not (Test-Path (Join-Path $UmiData "plugins"))) { throw "Not a UmiOCR-data folder: $UmiData" }

$plugins = Join-Path $UmiData "plugins"
$target  = Join-Path $plugins "umi_local_translate"

$running = Get-Process -Name "Umi-OCR" -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "!! Umi-OCR is running. Close it first, then run this script again." -ForegroundColor Yellow
    exit 1
}

if (Test-Path $target) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $bak = Join-Path $plugins "umi_local_translate.bak_$stamp"
    Write-Host "== backing up existing plugin -> $bak"
    Move-Item $target $bak
}

Write-Host "== copying to $target"
robocopy $src $target /E /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "copy failed ($LASTEXITCODE)" }

Write-Host ""
Write-Host "Installed. Start Umi-OCR, open a 'Screenshot OCR' tab, then click the new '翻译' tab." -ForegroundColor Green
Write-Host "Log: $target\logs\plugin.log"
Write-Host ("Size: {0:N0} MB" -f ((Get-ChildItem $target -Recurse -File | Measure-Object Length -Sum).Sum/1MB))
