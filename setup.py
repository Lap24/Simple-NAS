from pathlib import Path

setup_bat = r'''@echo off
setlocal EnableExtensions EnableDelayedExpansion
title NAS Setup

cd /d "%~dp0"

echo ==========================================
echo        Python NAS - Automatic Setup
echo ==========================================
echo.

REM Check app.py
if not exist "app.py" (
    echo ERROR: app.py was not found.
    echo Put setup.bat in the same folder as app.py.
    pause
    exit /b 1
)

REM ------------------------------------------------
REM 1. Find or install Python
REM ------------------------------------------------
echo [1/5] Checking Python...

where py >nul 2>&1
if %errorlevel%==0 (
    set "PY=py"
    goto PYTHON_OK
)

where python >nul 2>&1
if %errorlevel%==0 (
    set "PY=python"
    goto PYTHON_OK
)

echo Python is not installed.
echo Downloading Python installer...

set "PYFILE=%TEMP%\python-installer.exe"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.13.7/python-3.13.7-amd64.exe' -OutFile '%PYFILE%'"

if not exist "%PYFILE%" (
    echo ERROR: Could not download Python.
    pause
    exit /b 1
)

echo Installing Python...
"%PYFILE%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1

del "%PYFILE%" >nul 2>&1

REM Refresh PATH / find Python again
where py >nul 2>&1
if %errorlevel%==0 (
    set "PY=py"
    goto PYTHON_OK
)

where python >nul 2>&1
if %errorlevel%==0 (
    set "PY=python"
    goto PYTHON_OK
)

echo ERROR: Python was installed but could not be found.
echo Close this window, open a new Command Prompt, and run setup.bat again.
pause
exit /b 1

:PYTHON_OK
echo Python found:
%PY% --version
echo.

REM ------------------------------------------------
REM 2. Create virtual environment
REM ------------------------------------------------
echo [2/5] Creating Python virtual environment...

if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv ".venv"
    if errorlevel 1 (
        echo ERROR: Could not create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists.
)

echo.

REM ------------------------------------------------
REM 3. Install Python packages
REM ------------------------------------------------
echo [3/5] Installing Flask and Pillow...

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: pip update failed.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install Flask Pillow
if errorlevel 1 (
    echo ERROR: Flask/Pillow installation failed.
    pause
    exit /b 1
)

echo Python packages installed.
echo.

REM ------------------------------------------------
REM 4. Install/check FFmpeg
REM ------------------------------------------------
echo [4/5] Checking FFmpeg...

where ffmpeg >nul 2>&1
if %errorlevel%==0 (
    echo FFmpeg is already installed.
    ffmpeg -version 2>nul | findstr /B /C:"ffmpeg version"
    goto FFMPEG_DONE
)

echo FFmpeg is not installed.

where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Windows Package Manager (winget) is not available.
    echo FFmpeg could not be installed automatically.
    echo The NAS will work, but video trimming will not work.
    goto FFMPEG_DONE
)

echo Installing FFmpeg with winget...
winget install --id Gyan.FFmpeg.Shared --exact --source winget --accept-source-agreements --accept-package-agreements

echo.
echo Checking FFmpeg again...

REM winget may update PATH only for future terminals
where ffmpeg >nul 2>&1
if %errorlevel%==0 (
    echo FFmpeg installed successfully.
) else (
    echo FFmpeg was installed, but Windows has not refreshed PATH yet.
    echo Restarting Command Prompt before using video trimming is recommended.
)

:FFMPEG_DONE
echo.

REM ------------------------------------------------
REM 5. Create storage folder
REM ------------------------------------------------
echo [5/5] Preparing NAS storage...

if not exist "nas_storage" mkdir "nas_storage"

echo.
echo ==========================================
echo             SETUP COMPLETE
echo ==========================================
echo.
echo Python environment: %CD%\.venv
echo Flask: installed
echo Pillow: installed
echo FFmpeg: checked/installed when possible
echo Storage: %CD%\nas_storage
echo.
echo You can now run start.bat
echo.
pause
exit /b 0
'''

path = Path("/mnt/data/setup.bat")
path.write_text(setup_bat, encoding="utf-8")
print(str(path))
