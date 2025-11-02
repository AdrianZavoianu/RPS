@echo off
REM Build script for Results Processing System (RPS)
REM Creates a standalone executable for Windows

echo ========================================
echo  RPS Build Script
echo ========================================
echo.

REM Check if pipenv is available
where pipenv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: pipenv not found. Please install pipenv first.
    echo Run: pip install pipenv
    pause
    exit /b 1
)

echo [1/5] Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo Done.
echo.

echo [2/5] Installing dependencies...
pipenv install --dev
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Done.
echo.

echo [3/5] Running database migrations (verification)...
pipenv run alembic upgrade head
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Migration check failed, but continuing...
)
echo Done.
echo.

echo [4/5] Building executable with PyInstaller...
pipenv run pyinstaller --clean RPS.spec
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Build failed
    pause
    exit /b 1
)
echo Done.
echo.

echo [5/5] Creating distribution package...
if not exist "dist\RPS" (
    echo ERROR: Build output not found at dist\RPS
    pause
    exit /b 1
)

REM Get current timestamp for versioning
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set timestamp=%mydate%_%mytime%

REM Create versioned ZIP file
set output_name=RPS_Build_%timestamp%.zip
powershell -command "Compress-Archive -Path 'dist\RPS\*' -DestinationPath 'dist\%output_name%' -Force"

echo Done.
echo.
echo ========================================
echo  Build Complete!
echo ========================================
echo.
echo Executable location: dist\RPS\RPS.exe
echo Distribution package: dist\%output_name%
echo.
echo To test the application:
echo   1. Navigate to dist\RPS\
echo   2. Run RPS.exe
echo.
echo To deploy to another computer:
echo   1. Copy the entire dist\RPS\ folder
echo   2. Run RPS.exe on the target machine
echo.
pause
