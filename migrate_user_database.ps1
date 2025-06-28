# SQLite to PostgreSQL Migration Script
# This script migrates your para_crawl.db to PostgreSQL (Local Installation)

Write-Host "=== SQLite to PostgreSQL Migration Script ===" -ForegroundColor Green
Write-Host "This script will migrate your para_crawl.db (74.7M records) to local PostgreSQL" -ForegroundColor Yellow
Write-Host ""

# Step 1: Test local PostgreSQL connection
Write-Host "Step 1: Testing local PostgreSQL connection..." -ForegroundColor Cyan
Write-Host "✓ The migration tool will automatically create the target database if needed." -ForegroundColor Green
Write-Host ""

# Prompt for connection details
$dbHost = Read-Host "PostgreSQL host (default: localhost)"
if ([string]::IsNullOrEmpty($dbHost)) { $dbHost = "localhost" }

$dbPort = Read-Host "PostgreSQL port (default: 5432)"
if ([string]::IsNullOrEmpty($dbPort)) { $dbPort = "5432" }

$dbName = Read-Host "Database name (default: para_crawl)"
if ([string]::IsNullOrEmpty($dbName)) { $dbName = "para_crawl" }

$dbUser = Read-Host "Username with database creation privileges (default: postgres)"
if ([string]::IsNullOrEmpty($dbUser)) { $dbUser = "postgres" }

$dbPassword = Read-Host "Password" -AsSecureString
$dbPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPassword))

# Test connection to PostgreSQL server
Write-Host "Testing connection to PostgreSQL server..." -ForegroundColor Cyan
$env:PGPASSWORD = $dbPasswordPlain
try {
    psql -h $dbHost -p $dbPort -U $dbUser -d postgres -c "SELECT version();" | Out-Null
    Write-Host "✓ PostgreSQL server connection successful" -ForegroundColor Green
    Write-Host "✓ Ready for migration (database will be created automatically)" -ForegroundColor Green
} catch {
    Write-Host "✗ PostgreSQL server connection failed. Please check your connection details." -ForegroundColor Red
    Write-Host "  Make sure PostgreSQL is running and credentials are correct." -ForegroundColor Yellow
    exit 1
}

# Step 2: Run the migration
Write-Host ""
Write-Host "Step 2: Starting migration process..." -ForegroundColor Cyan
Write-Host "Source: D:\Dokumenty\para_crawl.db" -ForegroundColor White
Write-Host "Target: PostgreSQL ($dbHost`:$dbPort/$dbName)" -ForegroundColor White
Write-Host ""

# Build connection URL
$postgresUrl = "postgresql://$dbUser`:$dbPasswordPlain@$dbHost`:$dbPort/$dbName"

# Set environment variables
$env:DATABASE_URL = $postgresUrl

# Run the migration
python -m app.database.sqlite_postgres_migrator `
    --sqlite-path "D:\Dokumenty\para_crawl.db" `
    --postgres-url $postgresUrl `
    --batch-size 1000 `
    --verbose

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=== Migration completed successfully! ===" -ForegroundColor Green
    Write-Host "Your data is now available in PostgreSQL at:" -ForegroundColor White
    Write-Host "  Host: $dbHost" -ForegroundColor White
    Write-Host "  Port: $dbPort" -ForegroundColor White
    Write-Host "  Database: $dbName" -ForegroundColor White
    Write-Host "  Username: $dbUser" -ForegroundColor White
    Write-Host ""
    Write-Host "To connect: psql -h $dbHost -p $dbPort -U $dbUser -d $dbName" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "Migration failed. Please check the error messages above." -ForegroundColor Red
    exit 1
}
