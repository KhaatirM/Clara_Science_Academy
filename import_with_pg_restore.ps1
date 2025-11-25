# PowerShell script to import PostgreSQL directory format export
# This script finds PostgreSQL installation and imports the database

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "POSTGRESQL DATABASE IMPORT" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Find PostgreSQL installation
$pgPaths = @(
    "C:\Program Files\PostgreSQL\*\bin",
    "C:\Program Files (x86)\PostgreSQL\*\bin",
    "$env:ProgramFiles\PostgreSQL\*\bin",
    "$env:LOCALAPPDATA\Programs\PostgreSQL\*\bin"
)

$pgBinPath = $null
foreach ($path in $pgPaths) {
    $found = Get-ChildItem -Path $path -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq "pg_restore.exe" } | Select-Object -First 1
    if ($found) {
        $pgBinPath = $found.DirectoryName
        Write-Host "[OK] Found PostgreSQL at: $pgBinPath" -ForegroundColor Green
        break
    }
}

if (-not $pgBinPath) {
    Write-Host "[ERROR] PostgreSQL not found in common locations." -ForegroundColor Red
    Write-Host "Please provide the path to PostgreSQL bin directory:" -ForegroundColor Yellow
    $pgBinPath = Read-Host "PostgreSQL bin path"
    if (-not (Test-Path "$pgBinPath\pg_restore.exe")) {
        Write-Host "[ERROR] pg_restore.exe not found at that location." -ForegroundColor Red
        exit 1
    }
}

# Find the database export directory
$exportBase = Join-Path $PSScriptRoot "database_export"
$tocFile = Get-ChildItem -Path $exportBase -Recurse -Filter "toc.dat" -ErrorAction SilentlyContinue | Select-Object -First 1

if (-not $tocFile) {
    Write-Host "[ERROR] Could not find toc.dat file in database_export directory" -ForegroundColor Red
    exit 1
}

$dbDir = $tocFile.DirectoryName
Write-Host "[OK] Found database directory: $dbDir" -ForegroundColor Green

# Database name
$dbName = "clara_science_local"

# Check if database already exists
Write-Host "`nChecking if database exists..." -ForegroundColor Yellow
$checkDb = & "$pgBinPath\psql.exe" -U postgres -lqt 2>$null | Select-String -Pattern "^\s*$dbName\s"
if ($checkDb) {
    Write-Host "Database '$dbName' already exists." -ForegroundColor Yellow
    $overwrite = Read-Host "Drop and recreate? (yes/no)"
    if ($overwrite -eq "yes") {
        Write-Host "Dropping database..." -ForegroundColor Yellow
        & "$pgBinPath\dropdb.exe" -U postgres $dbName
    } else {
        Write-Host "Using existing database." -ForegroundColor Yellow
    }
} else {
    Write-Host "Creating database '$dbName'..." -ForegroundColor Yellow
    & "$pgBinPath\createdb.exe" -U postgres $dbName
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create database. Check PostgreSQL is running and credentials are correct." -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Database created" -ForegroundColor Green
}

# Import the database
Write-Host "`nImporting database from: $dbDir" -ForegroundColor Yellow
Write-Host "This may take a few minutes..." -ForegroundColor Yellow

& "$pgBinPath\pg_restore.exe" -U postgres -d $dbName -v "$dbDir"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[OK] Successfully imported to PostgreSQL!" -ForegroundColor Green
    Write-Host "`nNext step: Copy data to SQLite" -ForegroundColor Cyan
    Write-Host "Run: python copy_postgres_to_sqlite.py" -ForegroundColor Cyan
} else {
    Write-Host "`n[ERROR] Import failed. Check the error messages above." -ForegroundColor Red
    exit 1
}

