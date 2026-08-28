# Konfiguracja PyInstaller dla SecureVisio Monitor.
#
# Budowanie:  Zbuduj_exe.bat
#     albo:   python -m PyInstaller SecureVisioMonitor.spec --noconfirm --clean
#
# Wynik: dist\SecureVisioMonitor.exe - pojedynczy plik, bez potrzeby
# instalowania Pythona na komputerze docelowym.
#
# Ikona: wykrywana automatycznie - pierwszy plik .ico znaleziony w katalogu
# projektu (dowolna nazwa). Brak pliku .ico oznacza ikonę domyślną.

import glob

block_cipher = None

_icon_candidates = sorted(glob.glob("*.ico"))
_icon_path = _icon_candidates[0] if _icon_candidates else None

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=[],
    # comtypes generuje część modułów dynamicznie w czasie działania,
    # przez co PyInstaller ich nie wykrywa automatycznie.
    hiddenimports=[
        "comtypes",
        "comtypes.client",
        "comtypes.stream",
        "uiautomation",
        "win32api",
        "win32con",
        "win32gui",
        "win32process",
        # Powiadomienia systemowe Windows. Moduly winrt sa ladowane
        # dynamicznie i nie sa wykrywane automatycznie.
        "winrt.windows.data.xml.dom",
        "winrt.windows.ui.notifications",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Wykluczamy biblioteki niepotrzebne w tej aplikacji - bez tego rozmiar
    # pliku rosnie o kilkadziesiat MB.
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "PIL",
        "pytest",
        "PySide6.QtNetwork",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtWebEngineCore",
        "PySide6.Qt3DCore",

        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SecureVisioMonitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    # console=False - aplikacja okienkowa, bez okna terminala w tle.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon_path,
)
