@echo off
echo ==========================================
echo      Starting Adobe Mid Prep Project
echo ==========================================

echo.
echo [1/4] Activating Python Environment...
call venv\Scripts\activate

echo.
echo [2/4] Updating IP Configuration...
python update_ip.py

echo.
echo [3/4] Starting Backend Server...
start "Backend Server" cmd /k "call venv\Scripts\activate && cd backend && python server.py"

echo.
echo [4/4] Starting Website...
start "Website" cmd /k "cd website && npm run dev"

echo.
echo [5/5] Starting Mobile App...
start "Mobile App" cmd /k "cd mobile-app && npx expo start"

echo.
echo ==========================================
echo      All Services Started!
echo ==========================================
