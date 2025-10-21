@echo off
REM Quick test script for Windows

echo ============================================
echo  Results Processing System - Windows Test
echo ============================================
echo.

REM Check if pipenv is installed
where pipenv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: pipenv not found!
    echo Install it with: pip install pipenv
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist "Pipfile.lock" (
    echo Installing dependencies...
    pipenv install --dev
)

REM Run database migrations
echo Running database migrations...
pipenv run alembic upgrade head

REM Launch the app
echo.
echo Launching RPS...
echo.
pipenv run python src/main.py

pause
