@echo off
REM Ollama GUI Command Center - Startup Script for Windows

echo Starting Ollama GUI Command Center...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo Node.js is not installed. Please install Node.js 16 or higher.
    pause
    exit /b 1
)

REM Check if Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo Warning: Ollama doesn't appear to be running on localhost:11434
    echo Please start Ollama before proceeding.
    echo.
    pause
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install Python dependencies
echo Installing Python dependencies...
pip install -q -r requirements.txt

REM Install Node.js dependencies if needed
if not exist "node_modules" (
    echo Installing Node.js dependencies...
    call npm install
)

REM Start backend
echo Starting backend server...
cd backend
start /B python main.py
cd ..

REM Wait for backend to start
echo Waiting for backend to initialize...
timeout /t 3 /nobreak >nul

REM Start Electron frontend
echo Starting Electron frontend...
call npm start

echo.
echo Ollama GUI Command Center is running!
echo.
pause
