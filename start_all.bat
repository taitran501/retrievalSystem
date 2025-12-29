@echo off
echo ========================================
echo Starting DRES Full Stack
echo ========================================
echo.

echo [1/3] Starting Milvus (Docker)...
cd /d "%~dp0database"
docker-compose up -d
if %errorlevel% neq 0 (
    echo ERROR: Failed to start Milvus
    pause
    exit /b 1
)
echo Waiting for Milvus to initialize...
ping 127.0.0.1 -n 11 > nul

echo.
echo [2/3] Starting Backend...
set PYTHONIOENCODING=utf-8
start "DRES Backend" cmd /k "cd /d "%~dp0backend" && python main.py"
echo Waiting for backend to load models...
ping 127.0.0.1 -n 6 > nul

echo.
echo [3/3] Starting Frontend...
start "DRES Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ========================================
echo DRES Stack Started Successfully!
echo ========================================
echo.
echo Services:
echo   Milvus:   localhost:19530
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo.
echo Press any key to exit this window...
pause > nul
