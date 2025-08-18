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

# Make sure the dist folder exists
$distPath = "dist"
if (-not (Test-Path $distPath)) {
    Write-Host "Error: dist folder not found. PyInstaller may have failed."
    exit 1
}

# Collect all files from dist folder for zipping
$zipFiles = Get-ChildItem -Path $distPath -Recurse | ForEach-Object { $_.FullName }

# Remove existing zip if present
$zipPath = "$releasePath\deeRip-v$Version-win64.zip"
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

# Zip the EXE and all required files
Compress-Archive -Path $zipFiles -DestinationPath $zipPath -Force

Write-Host "Windows build completed: $zipPath"