@echo off
REM Budowanie SecureVisioMonitor.exe
REM
REM Wymaga jednorazowo: pip install pyinstaller
REM Wynik: dist\SecureVisioMonitor.exe

cd /d "%~dp0"

echo Sprawdzanie PyInstaller...
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller nie jest zainstalowany.
    echo Instaluje...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo BLAD: nie udalo sie zainstalowac PyInstaller.
        pause
        exit /b 1
    )
)

echo.
echo Budowanie aplikacji...
python -m PyInstaller SecureVisioMonitor.spec --noconfirm --clean

if errorlevel 1 (
    echo.
    echo BLAD: budowanie nie powiodlo sie.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Gotowe: dist\SecureVisioMonitor.exe
echo ==========================================
echo.
echo Plik settings.json zostanie utworzony obok .exe przy pierwszym
echo uruchomieniu i zapamieta konfiguracje.
echo.
pause