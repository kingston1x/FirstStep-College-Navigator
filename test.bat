@echo off
echo ============================================
echo  FirstStep - Full Pipeline Runner
echo ============================================
echo.

:: Step 1 - Install dependencies
echo [1/5] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: pip install failed. [cite: 2]
    pause
    exit /b 1
)

:: Step 2 - Run Scraper
echo [2/5] Running scraper.py...
python data/raw/scrape_scholars4dev.py
if %errorlevel% neq 0 (
    echo ERROR: scraper.py failed.
    pause
    exit /b 1
)

:: Step 3 - Run Cleaner
echo [3/5] Running cleaner.py...
python cleaner.py --input data/raw/Scholarships.csv --output data/clean/scholarships_clean.csv
if %errorlevel% neq 0 (
    echo ERROR: cleaner.py failed. [cite: 3]
    pause
    exit /b 1
)

:: Step 4 - Run Matcher
echo [4/5] Running matcher.py...
python matcher.py
if %errorlevel% neq 0 (
    echo ERROR: matcher.py failed.
    pause
    exit /b 1
)

:: Step 5 - Evaluate
echo [5/5] Evaluating results...
python evaluate.py 
if %errorlevel% neq 0 (
    echo ERROR: evaluate.py failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  All processes completed successfully.
echo ============================================
echo.
pause