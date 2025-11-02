@echo off
REM Package RPS for distribution
REM Creates a clean ZIP file with README

echo ========================================
echo  RPS Packaging Script
echo ========================================
echo.

if not exist "dist\RPS\RPS.exe" (
    echo ERROR: Build not found. Please run build.bat first.
    pause
    exit /b 1
)

echo [1/4] Copying README to distribution...
copy /Y DIST_README.txt "dist\RPS\README.txt"
echo Done.
echo.

echo [2/4] Creating version file...
echo Version: 1.7.0 > "dist\RPS\VERSION.txt"
echo Build Date: %date% %time% >> "dist\RPS\VERSION.txt"
echo Platform: Windows x64 >> "dist\RPS\VERSION.txt"
echo Done.
echo.

echo [3/4] Calculating checksums...
cd dist\RPS
powershell -command "Get-FileHash RPS.exe -Algorithm SHA256 | Select-Object -ExpandProperty Hash" > RPS.exe.sha256
cd ..\..
echo Done.
echo.

echo [4/4] Creating distribution package...
set version=1.7.0
set output=RPS_v%version%_Windows_x64.zip

if exist "dist\%output%" del "dist\%output%"
powershell -command "Compress-Archive -Path 'dist\RPS\*' -DestinationPath 'dist\%output%' -CompressionLevel Optimal"

echo Done.
echo.

echo ========================================
echo  Package Complete!
echo ========================================
echo.
echo Distribution package: dist\%output%
echo.
echo Package includes:
echo   - RPS.exe (main application)
echo   - _internal\ (dependencies)
echo   - README.txt (user guide)
echo   - VERSION.txt (build info)
echo   - RPS.exe.sha256 (checksum)
echo.
echo To deploy:
echo   1. Upload the ZIP file to your distribution platform
echo   2. Users extract and run RPS.exe
echo   3. No installation required!
echo.
pause
