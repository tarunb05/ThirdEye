Write-Host ""
Write-Host "  ========================================" -ForegroundColor DarkCyan
Write-Host "     THIRDEYE" -ForegroundColor Cyan
Write-Host "       Powered by Raven" -ForegroundColor DarkGray
Write-Host "  ========================================" -ForegroundColor DarkCyan
Write-Host ""

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"

# Find Python
$pyVer = $null
foreach ($ver in @("3.12", "3.11", "3.10")) {
    try { $null = & py "-$ver" --version 2>&1; if ($LASTEXITCODE -eq 0) { $pyVer = $ver; break } } catch {}
}
if (-not $pyVer) {
    Write-Host "  ERROR: Python 3.10-3.12 required" -ForegroundColor Red
    Write-Host "  Download: https://www.python.org/downloads/release/python-3129/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"; exit 1
}
Write-Host "  Python $pyVer" -ForegroundColor Green

# Backend
$venvPy = Join-Path $backendDir "venv\Scripts\python.exe"
$venvPip = Join-Path $backendDir "venv\Scripts\pip.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "[1/4] Setting up backend..." -ForegroundColor Yellow
    $venvDir = Join-Path $backendDir "venv"
    if (Test-Path $venvDir) { Remove-Item -Recurse -Force $venvDir }
    & py "-$pyVer" -m venv (Join-Path $backendDir "venv")
    & $venvPy -m pip install --upgrade pip -q 2>$null
    & $venvPip install -r "$backendDir\requirements.txt" -q
    Write-Host "  Done." -ForegroundColor Green
} else {
    $check = & $venvPy -c "import uvicorn; import reportlab" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[1/4] Installing deps..." -ForegroundColor Yellow
        & $venvPip install -r "$backendDir\requirements.txt" -q
    } else { Write-Host "[1/4] Backend ready." -ForegroundColor DarkGray }
}

# Frontend
if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "[2/4] Installing frontend..." -ForegroundColor Yellow
    Push-Location $frontendDir; cmd /c "npm install --silent 2>&1"; Pop-Location
    Write-Host "  Done." -ForegroundColor Green
} else { Write-Host "[2/4] Frontend ready." -ForegroundColor DarkGray }

# Ollama
$ollamaOk = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaOk) {
    Write-Host "[3/4] Ollama found." -ForegroundColor Green
    $models = ollama list 2>&1
    if ($models -notmatch "llama" -and $models -notmatch "mistral" -and $models -notmatch "gemma" -and $models -notmatch "phi" -and $models -notmatch "qwen") {
        Write-Host "  Pulling llama3.2:3b..." -ForegroundColor Yellow
        ollama pull llama3.2:3b
    }
} else { Write-Host "[3/4] Ollama not found! https://ollama.com" -ForegroundColor Red }

# Launch
Write-Host "[4/4] Launching..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Backend  -> http://127.0.0.1:8000" -ForegroundColor DarkCyan
Write-Host "  Frontend -> http://localhost:5173" -ForegroundColor DarkCyan
Write-Host ""

$backendJob = Start-Process -PassThru -NoNewWindow -FilePath $venvPy -ArgumentList "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $backendDir
Start-Sleep -Seconds 2
$frontendJob = Start-Process -PassThru -NoNewWindow -FilePath "cmd.exe" -ArgumentList "/c", "npm run dev" -WorkingDirectory $frontendDir
Start-Sleep -Seconds 4
Start-Process "http://localhost:5173"

Write-Host "  Raven is live." -ForegroundColor Green
Write-Host "  Press ENTER to shut down." -ForegroundColor DarkGray
Read-Host | Out-Null

Write-Host "Shutting down..." -ForegroundColor Yellow
try { Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue } catch {}
try { Stop-Process -Id $frontendJob.Id -Force -ErrorAction SilentlyContinue } catch {}
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Write-Host "Done." -ForegroundColor Green
