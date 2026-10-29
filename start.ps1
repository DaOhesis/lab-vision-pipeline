# IoT Lab Vision Pipeline PowerShell Launcher
param (
    [switch]$Split,
    [switch]$NoWebcam,
    [switch]$Simulator,
    [double]$Fps = 5.0,
    [int]$DeviceIndex = 0,
    [switch]$NoPreview,
    [switch]$NoBrowser
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$venvPython = Join-Path $scriptDir "backend\venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    $venvPython = "python"
}

$launchArgs = @("start.py")

if ($Split) { $launchArgs += "--split" }
if ($NoWebcam) { $launchArgs += "--no-webcam" }
if ($Simulator) { $launchArgs += "--simulator" }
if ($Fps) { $launchArgs += @("--fps", $Fps) }
if ($DeviceIndex) { $launchArgs += @("--device-index", $DeviceIndex) }
if ($NoPreview) { $launchArgs += "--no-preview" }
if ($NoBrowser) { $launchArgs += "--no-browser" }

& $venvPython @launchArgs
