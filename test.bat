
@echo off
echo.
echo ============================================
echo  FirstStep - Test Runner
echo ============================================
echo.

:: Step 1 - Install dependencies
echo [1/3] Installing dependencies...
pip install pandas scikit-learn --quiet
if %errorlevel% neq 0 (
    echo ERROR: pip install failed. Is Python installed?
    pause
    exit /b 1
)
echo Done.
echo.

:: Step 2 - Run cleaner
echo [2/3] Running cleaner.py...
python cleaner.py --input data/raw/Scholarships.csv --output data/clean/scholarships_clean.csv
if %errorlevel% neq 0 (
    echo ERROR: cleaner.py failed. Check output above.
    pause
    exit /b 1
)
echo.

:: Step 3 - Run model
echo [3/3] Running model.py...
python model.py
if %errorlevel% neq 0 (
    echo ERROR: model.py failed. Check output above.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  All tests passed.
echo ============================================
echo.
pause