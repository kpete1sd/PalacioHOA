@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

REM --- Locate Python ---
where python >nul 2>&1
if %ERRORLEVEL%==0 (
  set "PYEXE=python"
) else (
  where py >nul 2>&1
  if %ERRORLEVEL%==0 (
    set "PYEXE=py"
  ) else (
    echo [ERROR] Python not found on PATH.
    echo Visit https://www.python.org/downloads/ to install Python 3, then re-run this file.
    start https://www.python.org/downloads/
    pause
    exit /b 1
  )
)

REM --- Create and activate a local virtual environment ---
%PYEXE% -m venv .hoa_env
if not exist ".hoa_env\Scripts\activate.bat" (
  echo [ERROR] Failed to create virtual environment.
  pause
  exit /b 1
)

call ".hoa_env\Scripts\activate.bat"

REM --- Upgrade pip and install dependencies ---
python -m pip install --upgrade pip
pip install streamlit pandas numpy matplotlib

REM --- Launch the HOA simulator (assumes hoa_budget_simulator.py is in the same folder) ---
if not exist "hoa_budget_simulator.py" (
  echo [ERROR] Could not find hoa_budget_simulator.py in the current folder:
  cd
  echo Place this .bat file in the same folder as hoa_budget_simulator.py and run again.
  pause
  exit /b 1
)

echo.
echo [OK] Environment ready. Launching the simulator...
streamlit run hoa_budget_simulator.py

REM --- Keep window open after app exits ---
echo.
pause
