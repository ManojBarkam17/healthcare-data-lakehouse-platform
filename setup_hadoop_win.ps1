# setup_hadoop_win.ps1 — Download Hadoop winutils for PySpark on Windows
# Run this ONCE from the project root: powershell -ExecutionPolicy Bypass -File setup_hadoop_win.ps1

$ErrorActionPreference = "Stop"
$hadoopDir = "$PSScriptRoot\hadoop\bin"

Write-Host "Setting up Hadoop winutils for PySpark on Windows..." -ForegroundColor Cyan

# Create directory
if (!(Test-Path $hadoopDir)) {
    New-Item -ItemType Directory -Path $hadoopDir -Force | Out-Null
    Write-Host "  Created hadoop\bin directory"
}

# Download winutils.exe (Hadoop 3.3.5 compatible with Spark 3.5.x)
$winutilsUrl = "https://github.com/cdarlint/winutils/raw/master/hadoop-3.3.5/bin/winutils.exe"
$winutilsDest = "$hadoopDir\winutils.exe"

if (!(Test-Path $winutilsDest)) {
    Write-Host "  Downloading winutils.exe from GitHub..."
    try {
        Invoke-WebRequest -Uri $winutilsUrl -OutFile $winutilsDest -UseBasicParsing
        Write-Host "  Downloaded winutils.exe" -ForegroundColor Green
    } catch {
        Write-Host "  Primary download failed, trying alternate URL..." -ForegroundColor Yellow
        $altUrl = "https://github.com/kontext-tech/winutils/raw/master/hadoop-3.3.5/bin/winutils.exe"
        Invoke-WebRequest -Uri $altUrl -OutFile $winutilsDest -UseBasicParsing
        Write-Host "  Downloaded winutils.exe (alternate)" -ForegroundColor Green
    }
} else {
    Write-Host "  winutils.exe already exists" -ForegroundColor Green
}

# Download hadoop.dll (also required on Windows)
$hadoopDllUrl = "https://github.com/cdarlint/winutils/raw/master/hadoop-3.3.5/bin/hadoop.dll"
$hadoopDllDest = "$hadoopDir\hadoop.dll"

if (!(Test-Path $hadoopDllDest)) {
    Write-Host "  Downloading hadoop.dll..."
    try {
        Invoke-WebRequest -Uri $hadoopDllUrl -OutFile $hadoopDllDest -UseBasicParsing
        Write-Host "  Downloaded hadoop.dll" -ForegroundColor Green
    } catch {
        Write-Host "  hadoop.dll download failed (non-critical, may still work)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  hadoop.dll already exists" -ForegroundColor Green
}

# Set HADOOP_HOME for this session
$hadoopHome = "$PSScriptRoot\hadoop"
$env:HADOOP_HOME = $hadoopHome
$env:PATH = "$hadoopHome\bin;$env:PATH"

# Set JAVA_HOME to Java 17 if both 17 and 23 are installed
$java17Path = "C:\Program Files\Eclipse Adoptium\jdk-17*"
$java17 = Get-Item $java17Path -ErrorAction SilentlyContinue | Select-Object -First 1
if ($java17) {
    $env:JAVA_HOME = $java17.FullName
    Write-Host "  JAVA_HOME set to Java 17: $($java17.FullName)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Setup complete! Now run:" -ForegroundColor Cyan
Write-Host '  $env:HADOOP_HOME = "' -NoNewline
Write-Host "$hadoopHome" -NoNewline -ForegroundColor Yellow
Write-Host '"'
Write-Host "  python -m src.transformations.bronze.ingest" -ForegroundColor Yellow
Write-Host ""
Write-Host "To make HADOOP_HOME permanent, run (as Admin):" -ForegroundColor Cyan
Write-Host "  [System.Environment]::SetEnvironmentVariable('HADOOP_HOME', '$hadoopHome', 'User')" -ForegroundColor Yellow
