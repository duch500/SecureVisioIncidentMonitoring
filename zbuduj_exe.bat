@echo off
REM Budowanie SecureVisioMonitor.exe
REM
REM Wymaga jednorazowo: pip install pyinstaller
REM Wynik: dist\SecureVisioMonitor.exe

cd /d "%~dp0"

echo Zamykanie dzialajacych instancji...
taskkill /F /IM SecureVisioMonitor.exe >nul 2>&1
if not errorlevel 1 (
    echo   Zamknieto dzialajaca aplikacje.
    REM Chwila na zwolnienie blokady pliku przez system.
    timeout /t 2 /nobreak >nul
)

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

for %%f in (*.ico) do (
    echo Znaleziono ikone: %%f
    goto :icon_found
)
echo Brak pliku .ico - zostanie uzyta ikona domyslna.
:icon_found

echo.
echo Budowanie aplikacji...
python -m PyInstaller SecureVisioMonitor.spec --noconfirm --clean

if errorlevel 1 (
    echo.
    echo BLAD: budowanie nie powiodlo sie.
    echo.
    echo Najczestsze przyczyny:
    echo   - aplikacja nadal dziala (sprawdz Menedzer zadan)
    echo   - antywirus blokuje zapis do katalogu dist
    echo   - plik dist\SecureVisioMonitor.exe jest otwarty w innym programie
    echo.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Gotowe: dist\SecureVisioMonitor.exe
echo ==========================================
echo.
echo Plik settings.json oraz katalog sounds\ zostana utworzone obok .exe
echo przy pierwszym uruchomieniu.
echo.
pause