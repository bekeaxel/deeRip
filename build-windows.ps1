param(
    [string]$Version
)

# Strip leading 'v' if present (tags are usually like v0.3.0)
if ($Version.StartsWith("v")) {
    $Version = $Version.Substring(1)
}

if (-not $Version) {
    Write-Host "Usage: ./build-windows.ps1 <version>"
    exit 1
}

Write-Host "Building Windows version $Version"

# Run PyInstaller
pyinstaller deeRip.spec --noconfirm --clean

# Ensure release folder exists
$releasePath = "releases\$Version"
if (-not (Test-Path $releasePath)) {
    New-Item -ItemType Directory -Force -Path $releasePath | Out-Null
}

# Zip the EXE and any required files (adjust paths if you have additional files)
Compress-Archive -Path "dist\deeRip.exe" -DestinationPath "$releasePath\deeRip-v$Version-win64.zip" -Force

Write-Host "Windows build completed: $releasePath\deeRip-v$Version-win64.zip"