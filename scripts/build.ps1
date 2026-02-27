param(
    [ValidateSet("onefile", "onedir")]
    [string]$Mode = "onefile",
    [string]$Name = "ghost_browser",
    [switch]$Console,
    [switch]$Sign,
    [string]$CertPath = "",
    [string]$TimestampUrl = "http://timestamp.digicert.com",
    [string]$CertPassword = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$icon = Join-Path $root "assets\ghost_browser.ico"
$versionFile = Join-Path $root "assets\version_info.txt"
$entry = Join-Path $root "ghost_browser.py"

$args = @(
    "-m", "PyInstaller",
    "--clean",
    "--name", $Name,
    "--icon", $icon,
    "--version-file", $versionFile
)

if ($Mode -eq "onefile") {
    $args += "--onefile"
} else {
    $args += "--onedir"
}

if (-not $Console) {
    $args += "--noconsole"
}

$args += $entry
python @args
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE."
}

$distDir = Join-Path $root "dist"
$target = if ($Mode -eq "onefile") {
    Join-Path $distDir "$Name.exe"
} else {
    Join-Path (Join-Path $distDir $Name) "$Name.exe"
}

if ($Sign) {
    if (-not $CertPath) {
        throw "Code signing requested but -CertPath was not provided."
    }
    if (-not (Get-Command signtool -ErrorAction SilentlyContinue)) {
        throw "Code signing requested but signtool was not found in PATH."
    }

    $signArgs = @("sign", "/fd", "sha256", "/tr", $TimestampUrl, "/td", "sha256", "/f", $CertPath)
    if ($CertPassword) {
        $signArgs += @("/p", $CertPassword)
    }
    $signArgs += $target
    & signtool @signArgs
    if ($LASTEXITCODE -ne 0) {
        throw "signtool failed with exit code $LASTEXITCODE."
    }
}

Write-Host "Build complete: $target"
