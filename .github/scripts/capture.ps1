Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class CaptureNative {
 [StructLayout(LayoutKind.Sequential)] public struct Rect {public int Left,Top,Right,Bottom;}
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h,out Rect r);
 [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h,IntPtr dc,uint flags);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int cmd);
}
'@
function Save-Window([IntPtr]$Handle,[string]$Name) {
 [CaptureNative]::ShowWindow($Handle,9) | Out-Null
 [CaptureNative]::SetForegroundWindow($Handle) | Out-Null
 Start-Sleep -Milliseconds 700
 $rect=New-Object CaptureNative+Rect
 [CaptureNative]::GetWindowRect($Handle,[ref]$rect) | Out-Null
 $width=$rect.Right-$rect.Left; $height=$rect.Bottom-$rect.Top
 if ($width -le 0 -or $height -le 0) { throw 'Window has no visible bounds' }
 $bitmap=New-Object Drawing.Bitmap $width,$height
 $graphics=[Drawing.Graphics]::FromImage($bitmap)
 $dc=$graphics.GetHdc()
 try { $ok=[CaptureNative]::PrintWindow($Handle,$dc,2) } finally {$graphics.ReleaseHdc($dc)}
 if (-not $ok) {throw 'PrintWindow failed'}
 $bitmap.Save((Join-Path "$PWD/screenshots" "$Name.png"),[Drawing.Imaging.ImageFormat]::Png)
 $graphics.Dispose();$bitmap.Dispose()
}
function Save-Process([string]$ProcessName,[string]$Name) {
 $proc=Get-Process -Name $ProcessName | Where-Object {$_.MainWindowHandle -ne 0} | Select-Object -First 1
 if (-not $proc) {throw "No window for $ProcessName"}
 Save-Window $proc.MainWindowHandle $Name
}
New-Item -ItemType Directory -Force screenshots | Out-Null
