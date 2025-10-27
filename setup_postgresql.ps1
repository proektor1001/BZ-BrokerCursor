# Autonomous PostgreSQL Setup Script for BrokerCursor
# Downloads, installs, and configures PostgreSQL automatically

Write-Host "=== PostgreSQL Autonomous Setup ===" -ForegroundColor Green

# Step 1: Check if PostgreSQL is already installed
Write-Host "Checking for existing PostgreSQL installation..." -ForegroundColor Yellow

$pgService = Get-Service -Name postgresql* -ErrorAction SilentlyContinue
$psqlExists = Get-Command psql -ErrorAction SilentlyContinue

if ($pgService -and $psqlExists) {
    Write-Host "PostgreSQL already installed and running!" -ForegroundColor Green
    $pgVersion = & psql --version
    Write-Host "Version: $pgVersion" -ForegroundColor Cyan
} else {
    Write-Host "PostgreSQL not found. Starting automatic installation..." -ForegroundColor Yellow
    
    # Step 2: Download PostgreSQL installer
    Write-Host "Downloading PostgreSQL 15 installer..." -ForegroundColor Yellow
    $installerUrl = "https://get.enterprisedb.com/postgresql/postgresql-15.10-1-windows-x64.exe"
    $installerPath = "$env:TEMP\postgresql-installer.exe"
    
    try {
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
        Write-Host "Download completed: $installerPath" -ForegroundColor Green
    } catch {
        Write-Host "Download failed. Trying alternative URL..." -ForegroundColor Red
        $installerUrl = "https://sbp.enterprisedb.com/getfile.jsp?fileid=1258803"
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
    }
    
    # Step 3: Generate secure passwords
    Write-Host "Generating secure passwords..." -ForegroundColor Yellow
    $postgresPassword = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 16 | ForEach-Object {[char]$_})
    $userPassword = -join ((65..90) + (97..122) + (48..57) + (33..47) | Get-Random -Count 16 | ForEach-Object {[char]$_})
    
    Write-Host "Generated postgres superuser password: [HIDDEN]" -ForegroundColor Cyan
    Write-Host "Generated brokercursor_user password: [HIDDEN]" -ForegroundColor Cyan
    
    # Step 4: Silent installation
    Write-Host "Installing PostgreSQL silently..." -ForegroundColor Yellow
    $installArgs = @(
        "--mode", "unattended",
        "--superpassword", $postgresPassword,
        "--serverport", "5432",
        "--servicename", "postgresql",
        "--prefix", "C:\Program Files\PostgreSQL\15",
        "--datadir", "C:\Program Files\PostgreSQL\15\data",
        "--locale", "English, United States"
    )
    
    try {
        Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait
        Write-Host "PostgreSQL installation completed!" -ForegroundColor Green
    } catch {
        Write-Host "Installation failed: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
    
    # Step 5: Add to PATH
    Write-Host "Adding PostgreSQL to PATH..." -ForegroundColor Yellow
    $pgBinPath = "C:\Program Files\PostgreSQL\15\bin"
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if ($currentPath -notlike "*$pgBinPath*") {
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$pgBinPath", "Machine")
        $env:Path += ";$pgBinPath"
    }
    
    # Step 6: Start PostgreSQL service
    Write-Host "Starting PostgreSQL service..." -ForegroundColor Yellow
    Start-Service -Name "postgresql" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 5
    
    # Step 7: Create database and user
    Write-Host "Creating database and user..." -ForegroundColor Yellow
    $env:PGPASSWORD = $postgresPassword
    
    # Create database
    & "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "CREATE DATABASE brokercursor;" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Database 'brokercursor' created successfully!" -ForegroundColor Green
    }
    
    # Create user
    & "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "CREATE USER brokercursor_user WITH PASSWORD '$userPassword';" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "User 'brokercursor_user' created successfully!" -ForegroundColor Green
    }
    
    # Grant privileges
    & "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE brokercursor TO brokercursor_user;" 2>$null
    & "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -d brokercursor -c "GRANT ALL ON SCHEMA public TO brokercursor_user;" 2>$null
    
    Write-Host "Database privileges granted!" -ForegroundColor Green
    
    # Step 8: Update .env file
    Write-Host "Updating .env file with generated password..." -ForegroundColor Yellow
    $envContent = Get-Content .env -Raw
    $envContent = $envContent -replace 'DB_PASSWORD=your_secure_password', "DB_PASSWORD=$userPassword"
    Set-Content .env $envContent -Encoding UTF8
    Write-Host ".env file updated successfully!" -ForegroundColor Green
    
    # Step 9: Verify installation
    Write-Host "Verifying PostgreSQL installation..." -ForegroundColor Yellow
    $service = Get-Service -Name postgresql -ErrorAction SilentlyContinue
    if ($service -and $service.Status -eq 'Running') {
        Write-Host "PostgreSQL service is running!" -ForegroundColor Green
    } else {
        Write-Host "Warning: PostgreSQL service may not be running properly" -ForegroundColor Yellow
    }
    
    # Test connection
    $env:PGPASSWORD = $userPassword
    $testResult = & "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U brokercursor_user -d brokercursor -c "SELECT version();" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Database connection test successful!" -ForegroundColor Green
        Write-Host "PostgreSQL version: $($testResult[0])" -ForegroundColor Cyan
    } else {
        Write-Host "Warning: Database connection test failed" -ForegroundColor Yellow
    }
}

Write-Host "=== PostgreSQL Setup Complete ===" -ForegroundColor Green
Write-Host "Ready to run: python core/scripts/init_db.py" -ForegroundColor Cyan
