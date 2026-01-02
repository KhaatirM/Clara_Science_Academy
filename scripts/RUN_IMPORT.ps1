# Simple PostgreSQL Import Script
# Run this in PowerShell after updating the paths below

# ============================================
# UPDATE THESE PATHS FOR YOUR SYSTEM
# ============================================

# 1. Find your PostgreSQL installation and update this path:
#    Common locations:
#    - C:\Program Files\PostgreSQL\15\bin
#    - C:\Program Files\PostgreSQL\14\bin
#    - C:\Program Files (x86)\PostgreSQL\15\bin
$pgBinPath = "C:\Program Files\PostgreSQL\17\bin"  # UPDATE THIS!

# 2. Database name (you can change this)
$dbName = "clara_science_local"

# 3. Database export directory (will be auto-detected if not found)
$dbDir = "database_export\2025-11-20T14_32Z\csastudentdb_gaah"  # Auto-detected path

# ============================================
# SCRIPT (Don't modify below unless needed)
# ============================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "POSTGRESQL DATABASE IMPORT" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Check if PostgreSQL tools exist
if (-not (Test-Path "$pgBinPath\pg_restore.exe")) {
    Write-Host "[ERROR] pg_restore.exe not found at: $pgBinPath" -ForegroundColor Red
    Write-Host "`nPlease update `$pgBinPath in this script with your PostgreSQL installation path." -ForegroundColor Yellow
    Write-Host "`nTo find it, look in:" -ForegroundColor Yellow
    Write-Host "  - C:\Program Files\PostgreSQL\" -ForegroundColor Yellow
    Write-Host "  - C:\Program Files (x86)\PostgreSQL\" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Found PostgreSQL at: $pgBinPath" -ForegroundColor Green

# Find database directory (look for toc.dat)
if ([string]::IsNullOrEmpty($dbDir) -or -not (Test-Path $dbDir)) {
    Write-Host "`nLooking for database directory..." -ForegroundColor Yellow
    $tocFile = Get-ChildItem -Path "database_export" -Recurse -Filter "toc.dat" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($tocFile) {
        $dbDir = $tocFile.DirectoryName
        Write-Host "[OK] Found database directory: $dbDir" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Could not find database directory (toc.dat file)." -ForegroundColor Red
        Write-Host "Please check:" -ForegroundColor Yellow
        Write-Host "  1. The tar.gz file was extracted correctly" -ForegroundColor Yellow
        Write-Host "  2. The database_export folder exists and contains files" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "[OK] Database directory: $dbDir" -ForegroundColor Green

# Get PostgreSQL password from environment or prompt
$pgPassword = $env:PGPASSWORD
if (-not $pgPassword) {
    Write-Host "`nPostgreSQL Password Required" -ForegroundColor Yellow
    Write-Host "You can set it as an environment variable: `$env:PGPASSWORD = 'your_password'" -ForegroundColor Cyan
    $securePassword = Read-Host "Enter PostgreSQL postgres user password" -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $pgPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    $env:PGPASSWORD = $pgPassword
}

# Check if database exists
Write-Host "`nChecking if database '$dbName' exists..." -ForegroundColor Yellow
$checkDb = & "$pgBinPath\psql.exe" -U postgres -lqt 2>$null | Select-String -Pattern "^\s*$dbName\s"
if ($checkDb) {
    Write-Host "Database '$dbName' already exists." -ForegroundColor Yellow
    Write-Host "Dropping existing database..." -ForegroundColor Yellow
    & "$pgBinPath\dropdb.exe" -U postgres $dbName
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARNING] Could not drop database. You may need to drop it manually." -ForegroundColor Yellow
    }
}

# Create database
Write-Host "`nCreating database '$dbName'..." -ForegroundColor Yellow
& "$pgBinPath\createdb.exe" -U postgres $dbName
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to create database." -ForegroundColor Red
    Write-Host "Make sure:" -ForegroundColor Yellow
    Write-Host "  1. PostgreSQL service is running" -ForegroundColor Yellow
    Write-Host "  2. Password is correct" -ForegroundColor Yellow
    Write-Host "  3. You have permission to create databases" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Database created" -ForegroundColor Green

# Import the database
Write-Host "`nImporting database..." -ForegroundColor Yellow
Write-Host "This may take a few minutes..." -ForegroundColor Yellow
Write-Host ""

& "$pgBinPath\pg_restore.exe" -U postgres -d $dbName -v "$dbDir"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n============================================================" -ForegroundColor Green
    Write-Host "[OK] Successfully imported to PostgreSQL!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "`nNext step: Copy data to SQLite" -ForegroundColor Cyan
    Write-Host "1. Update copy_postgres_to_sqlite.py with your PostgreSQL password" -ForegroundColor Yellow
    Write-Host "2. Run: python copy_postgres_to_sqlite.py" -ForegroundColor Yellow
} else {
    Write-Host "`n[ERROR] Import failed. Check the error messages above." -ForegroundColor Red
    exit 1
}

