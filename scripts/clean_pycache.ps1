# PowerShell script to clean up all __pycache__ directories in the project
# Usage: Run this script from the project root in PowerShell

$ErrorActionPreference = 'Stop'

Write-Host "Searching for __pycache__ directories..."

$pycacheDirs = Get-ChildItem -Path . -Recurse -Directory -Filter '__pycache__'

if ($pycacheDirs.Count -eq 0) {
    Write-Host "No __pycache__ directories found."
    exit 0
}

foreach ($dir in $pycacheDirs) {
    Write-Host "Removing: $($dir.FullName)"
    Remove-Item -Recurse -Force -Path $dir.FullName
}

Write-Host "Cleanup complete. Removed $($pycacheDirs.Count) __pycache__ directories."
