@echo off
setlocal enabledelayedexpansion
echo ============================================
echo  FirstStep - Full Pipeline Runner
echo  (scrape -^> clean -^> match -^> evaluate -^> backend -^> frontend)
echo ============================================
echo.

:: All paths below are written relative to the REPO ROOT.
:: Run this .bat from the repo root (double-click it there, or `cd` to
:: the repo root in a terminal before running it).

:: ---------------------------------------------------------------------
:: Step 0 - Create/activate a project-local virtual environment
:: ---------------------------------------------------------------------
if not exist ".venv\Scripts\activate.bat" (
    echo [0/6] No .venv found - creating one...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo ERROR: failed to create virtual environment.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"
if %errorlevel% neq 0 (
    echo ERROR: failed to activate virtual environment.
    pause
    exit /b 1
)

:: ---------------------------------------------------------------------
:: Step 1 - Install dependencies, but only if requirements.txt changed
:: since the last successful install. certutil is built into Windows,
:: so this needs no extra tools. Hash both requirements files together
:: and compare against the marker saved after the last install.
:: ---------------------------------------------------------------------
set "HASH_FILE=.venv\install.hash"
set "NEW_HASH="

for /f "skip=1 tokens=* delims=" %%H in ('certutil -hashfile backend\requirements.txt MD5 ^| findstr /v "CertUtil"') do (
    if not defined NEW_HASH set "NEW_HASH=%%H"
)
for /f "skip=1 tokens=* delims=" %%H in ('certutil -hashfile frontend\requirements.txt MD5 ^| findstr /v "CertUtil"') do (
    set "NEW_HASH=!NEW_HASH!%%H"
)

set "OLD_HASH="
if exist "%HASH_FILE%" set /p OLD_HASH=<"%HASH_FILE%"

if "%NEW_HASH%"=="%OLD_HASH%" (
    echo [1/6] Dependencies unchanged - skipping install.
) else (
    echo [1/6] Installing backend dependencies...
    pip install -r backend\requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: backend pip install failed.
        pause
        exit /b 1
    )

    echo [1/6] Installing frontend dependencies...
    pip install -r frontend\requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: frontend pip install failed.
        pause
        exit /b 1
    )

    >"%HASH_FILE%" echo %NEW_HASH%
)

:: ---------------------------------------------------------------------
:: Step 2 - Run scraper (writes data\raw\Scholarships.csv)
:: ---------------------------------------------------------------------
echo.
echo [2/6] Running scraper.py...
python data\raw\scrape_scholars4dev.py --output data\raw\Scholarships.csv
if %errorlevel% neq 0 (
    echo ERROR: scraper.py failed.
    pause
    exit /b 1
)

:: ---------------------------------------------------------------------
:: Step 3 - Run cleaner (backend\cleaner.py) with explicit root-relative
:: paths, so it doesn't matter that cleaner.py's own DEFAULT_INPUT/OUTPUT
:: constants are only correct when run from the repo root.
:: ---------------------------------------------------------------------
echo.
echo [3/6] Running cleaner.py...
python backend\cleaner.py --input data\raw\Scholarships.csv --output data\clean\scholarships_clean.csv
if %errorlevel% neq 0 (
    echo ERROR: cleaner.py failed.
    pause
    exit /b 1
)

:: ---------------------------------------------------------------------
:: Step 4 - Run matcher self-test (backend\matcher.py), explicit --csv so
:: it doesn't rely on matcher.py's __file__-anchored DEFAULT_CSV, which
:: is currently one directory level off after the backend\ move.
:: ---------------------------------------------------------------------
echo.
echo [4/6] Running matcher.py...
python backend\matcher.py --csv data\clean\scholarships_clean.csv
if %errorlevel% neq 0 (
    echo ERROR: matcher.py failed.
    pause
    exit /b 1
)

:: ---------------------------------------------------------------------
:: Step 5 - Evaluate (backend\evaluate.py), same explicit-path reasoning
:: ---------------------------------------------------------------------
echo.
echo [5/6] Evaluating results...
python backend\evaluate.py --csv data\clean\scholarships_clean.csv --truth evaluation\ground_truth.csv
if %errorlevel% neq 0 (
    echo ERROR: evaluate.py failed.
    pause
    exit /b 1
)

:: ---------------------------------------------------------------------
:: Step 6 - Launch backend + frontend as two live processes
:: ---------------------------------------------------------------------
echo.
echo [6/6] Starting backend API and frontend UI...
echo.

:: SCHOLARSHIPS_CSV overrides app.py's built-in CSV_PATH default, which is
:: currently pointed at the wrong folder/filename case after the backend\
:: move. This env var routes around that without needing app.py edited.
set "SCHOLARSHIPS_CSV=%CD%\data\clean\scholarships_clean.csv"

:: GEMINI_API_KEY: set this in your own environment or a .env file before
:: running this script if you want explainer.py's Gemini calls to work.
:: (Not currently wired into app.py's /recommend route - see note below.)

start "FirstStep Backend (Flask)" cmd /k "call .venv\Scripts\activate.bat && set SCHOLARSHIPS_CSV=%SCHOLARSHIPS_CSV% && python backend\app.py"

echo Waiting for backend to boot...
timeout /t 5 /nobreak >nul

start "FirstStep Frontend (Streamlit)" cmd /k "call .venv\Scripts\activate.bat && cd frontend && streamlit run app.py"

echo.
echo ============================================
echo  Backend running in its own window (port 5000)
echo  Frontend running in its own window (Streamlit)
echo  Close those windows to stop each process.
echo ============================================
echo.
pause