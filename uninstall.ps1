# Remove the plugin from Umi-OCR.
#
#   powershell -ExecutionPolicy Bypass -File uninstall.ps1 -UmiData "D:\Umi-OCR\UmiOCR-data"
#
# The UmiOCR-data folder can also be passed via the UMI_OCR_DATA environment variable.
param(
    [string]$UmiData = ""
)

$ErrorActionPreference = "Stop"

if (-not $UmiData) { $UmiData = $env:UMI_OCR_DATA }
if (-not $UmiData) {
    throw "Please pass -UmiData, e.g.  -UmiData 'D:\Umi-OCR\UmiOCR-data'"
}

$target = Join-Path $UmiData "plugins\umi_local_translate"

if (-not (Test-Path $target)) {
    Write-Host "Plugin folder not found: $target"
    exit 0
}

Write-Host "== stopping translation service if running"
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and $_.CommandLine.Contains("umi_local_translate") } |
    ForEach-Object {
        Write-Host "   kill pid $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

Write-Host "== removing $target"
Remove-Item -Recurse -Force $target
Write-Host "Done." -ForegroundColor Green
Write-Host "Restart Umi-OCR to make sure the '翻译' tab is gone."
