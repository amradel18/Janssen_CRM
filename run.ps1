# ==============================================================================
# JANSSEN CRM - Launch Script (PowerShell)
# ==============================================================================

# Ensure script runs from the project root directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "       Starting JANSSEN CRM App         " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Working Directory: $scriptDir" -ForegroundColor Gray

# Define paths
$venvPython = Join-Path $scriptDir "venv\Scripts\python.exe"
$venvStreamlit = Join-Path $scriptDir "venv\Scripts\streamlit.exe"
$entryPoint = Join-Path $scriptDir "login.py"

# Verify login.py exists
if (-not (Test-Path $entryPoint)) {
    Write-Host "[ERROR] Entry point '$entryPoint' was not found!" -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}

# Determine Python / Streamlit command
if (Test-Path $venvPython) {
    Write-Host "[OK] Using virtual environment: .\venv" -ForegroundColor Green
    $pythonCmd = $venvPython
} else {
    Write-Host "[WARNING] Virtual environment 'venv' not found." -ForegroundColor Yellow
    Write-Host "Searching for system Python..." -ForegroundColor Yellow
    
    $systemPython = Get-Command python -ErrorAction SilentlyContinue
    if ($systemPython) {
        $pythonCmd = "python"
        Write-Host "[OK] Using system Python ($($systemPython.Source))" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Neither 'venv' nor system Python could be found!" -ForegroundColor Red
        Write-Host "Please create a virtual environment or install Python." -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }
}

# Launch the Streamlit application
Write-Host "`nLaunching Streamlit ($entryPoint)..." -ForegroundColor Cyan
Write-Host "To stop the app, press Ctrl + C in this terminal.`n" -ForegroundColor DarkGray

try {
    & $pythonCmd -m streamlit run $entryPoint $args
} catch {
    Write-Host "`n[ERROR] An error occurred while running the app:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}
