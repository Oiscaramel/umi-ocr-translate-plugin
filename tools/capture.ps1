# Capture the Umi-OCR main window (dev helper).
#   powershell -ExecutionPolicy Bypass -File tools\capture.ps1 -Out <png>
param(
    [string]$Out = "$env:TEMP\umi_window.png"
)

Add-Type -AssemblyName System.Drawing

Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinCap {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
    public static readonly IntPtr HWND_TOPMOST = new IntPtr(-1);
    public static readonly IntPtr HWND_NOTOPMOST = new IntPtr(-2);
    public const uint SWP_NOMOVE = 0x0002;
    public const uint SWP_NOSIZE = 0x0001;
    public const uint SWP_SHOWWINDOW = 0x0040;
}
'@

[void][WinCap]::SetProcessDPIAware()

$p = Get-Process -Name "Umi-OCR" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $p -or $p.MainWindowHandle -eq 0) { Write-Output "Umi-OCR is not running"; exit 1 }

$h = $p.MainWindowHandle
if ([WinCap]::IsIconic($h)) { [void][WinCap]::ShowWindow($h, 9) }
[void][WinCap]::SetWindowPos($h, [WinCap]::HWND_TOPMOST, 0, 0, 0, 0, [WinCap]::SWP_NOMOVE -bor [WinCap]::SWP_NOSIZE -bor [WinCap]::SWP_SHOWWINDOW)
[void][WinCap]::BringWindowToTop($h)
[void][WinCap]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 700

$r = New-Object WinCap+RECT
[void][WinCap]::GetWindowRect($h, [ref]$r)
$w = $r.Right - $r.Left
$hgt = $r.Bottom - $r.Top
Write-Output ("capture: {0},{1} {2}x{3}" -f $r.Left, $r.Top, $w, $hgt)

$bmp = New-Object System.Drawing.Bitmap $w, $hgt
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.Left, $r.Top, 0, 0, $bmp.Size)
$g.Dispose()
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()

[void][WinCap]::SetWindowPos($h, [WinCap]::HWND_NOTOPMOST, 0, 0, 0, 0, [WinCap]::SWP_NOMOVE -bor [WinCap]::SWP_NOSIZE)
Write-Output ("saved: {0}" -f $Out)
