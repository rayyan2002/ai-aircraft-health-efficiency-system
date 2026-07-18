# ─────────────────────────────────────────────────────────────
# AeroTwin — backend folder tidy-up
#
# Moves diagnostic / setup / test scripts into  scripts/
# Keeps main.py, the database, requirements.txt, and ANY module
# that main.py imports (moving those would break the project).
#
# Run from  src/backend :
#     powershell -ExecutionPolicy Bypass -File organize_scripts.ps1
#
# It runs in DRY-RUN mode first. Nothing moves until you confirm.
# ─────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"

if (-not (Test-Path "main.py")) {
    Write-Host "ERROR: run this from src/backend (main.py not found here)." -ForegroundColor Red
    exit 1
}

# 1. Work out which local modules main.py depends on — never move these.
$mainText = Get-Content "main.py" -Raw
$localModules = @()
Get-ChildItem -Filter "*.py" | ForEach-Object {
    $mod = [System.IO.Path]::GetFileNameWithoutExtension($_.Name)
    if ($mod -eq "main") { return }
    # does main.py import it?
    if ($mainText -match "(?m)^\s*(from\s+$mod\s+import|import\s+$mod)\b") {
        $localModules += $_.Name
    }
}

# 2. Files that must stay put regardless.
$keep = @("main.py") + $localModules

Write-Host ""
Write-Host "════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " STAYING IN backend/  (main.py needs these)"      -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════" -ForegroundColor Cyan
$keep | Sort-Object -Unique | ForEach-Object { Write-Host "   $_" -ForegroundColor Green }
if ($localModules.Count -eq 0) {
    Write-Host "   (main.py imports no local modules - good, it is self-contained)" -ForegroundColor DarkGray
}

# 3. Everything else that is a .py file gets moved.
$toMove = Get-ChildItem -Filter "*.py" |
          Where-Object { $keep -notcontains $_.Name } |
          Where-Object { $_.Name -ne "organize_scripts.ps1" }

Write-Host ""
Write-Host "════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host " MOVING TO scripts/"                              -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════" -ForegroundColor Yellow
if ($toMove.Count -eq 0) {
    Write-Host "   (nothing to move)" -ForegroundColor DarkGray
    exit 0
}
$toMove | ForEach-Object { Write-Host "   $($_.Name)" -ForegroundColor Yellow }

Write-Host ""
Write-Host "Untouched: aviation_data.db, requirements.txt, and all folders." -ForegroundColor DarkGray
Write-Host ""
$answer = Read-Host "Move these $($toMove.Count) file(s) into scripts/ ? (y/n)"
if ($answer -ne "y") { Write-Host "Cancelled - nothing moved."; exit 0 }

# 4. Move. Use git mv for tracked files so history is preserved.
New-Item -ItemType Directory -Force -Path "scripts" | Out-Null

$gitAvailable = $false
try { git rev-parse --is-inside-work-tree 2>$null | Out-Null; $gitAvailable = $true } catch {}

foreach ($f in $toMove) {
    $tracked = $false
    if ($gitAvailable) {
        git ls-files --error-unmatch $f.Name 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $tracked = $true }
    }
    if ($tracked) {
        git mv $f.Name "scripts/$($f.Name)"
        Write-Host "  git mv  $($f.Name)" -ForegroundColor Green
    } else {
        Move-Item $f.FullName "scripts/$($f.Name)" -Force
        Write-Host "  moved   $($f.Name)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Done. backend/ now contains:" -ForegroundColor Cyan
Get-ChildItem | Where-Object { -not $_.PSIsContainer } |
    ForEach-Object { Write-Host "   $($_.Name)" }

Write-Host ""
Write-Host "NOTE: scripts that read aviation_data.db now sit one level deeper." -ForegroundColor Yellow
Write-Host "      Run them from backend/ like:  python scripts\check_hex.py" -ForegroundColor Yellow
Write-Host "      (or update their connect path to  ..\aviation_data.db )" -ForegroundColor Yellow