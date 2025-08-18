param(
    [string]$Version
)

if (-not $Version) {
    Write-Host "Usage: ./build-windows.ps1 <version>"
    exit 1
}

# Run PyInstaller
pyinstaller deeRip.spec --noconfirm

# Create release folder
New-Item -ItemType Directory -Force -Path "releases\$Version" | Out-Null

# Zip up exe + required files
Compress-Archive -Path "dist\deeRip.exe" -DestinationPath "releases\$Version\deeRip-v$Version-win64.zip" -Force