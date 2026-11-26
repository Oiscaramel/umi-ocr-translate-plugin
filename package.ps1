# Build the distributable zip from build\umi_local_translate
#   powershell -ExecutionPolicy Bypass -File package.ps1
#   powershell -ExecutionPolicy Bypass -File package.ps1 -Version 1.0.1
param(
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$src  = Join-Path $root "build\umi_local_translate"
$dist = Join-Path $root "dist"

if (-not (Test-Path (Join-Path $src "__init__.py"))) {
    throw "build\umi_local_translate not found. Run build.ps1 first."
}

Write-Host "== cleaning build folder"
Remove-Item -Recurse -Force (Join-Path $src "logs") -ErrorAction SilentlyContinue
Get-ChildItem $src -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item -Recurse -Force $_.FullName }

Write-Host "== resetting config.json to defaults"
Copy-Item -Force (Join-Path $root "src\umi_local_translate\config.json") (Join-Path $src "config.json")
Copy-Item -Force (Join-Path $root "src\umi_local_translate\README.md") (Join-Path $src "README.md")

if (-not (Test-Path $dist)) { New-Item -ItemType Directory -Force -Path $dist | Out-Null }
$zip = Join-Path $dist ("umi_local_translate_v{0}.zip" -f $Version)
if (Test-Path $zip) { Remove-Item -Force $zip }

Write-Host "== zipping (this takes a few minutes for ~760MB)"
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $src,
    $zip,
    [System.IO.Compression.CompressionLevel]::Fastest,
    $true
)

$size = (Get-Item $zip).Length / 1MB
$hash = (Get-FileHash $zip -Algorithm SHA256).Hash

Write-Host ""
Write-Host ("zip  : {0}" -f $zip)
Write-Host ("size : {0:N0} MB" -f $size)
Write-Host ("sha256: {0}" -f $hash)
