@echo off
echo ==========================================
echo      Setting up Adobe Mid Prep Project
echo ==========================================

echo.
echo [1/4] Creating Python Virtual Environment...
py -3.12 -m venv venv
call venv\Scripts\activate

echo.
echo [2/4] Installing Python Requirements...
pip install -r requirements.txt
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install gdown

echo.
echo [3/4] Installing Website Dependencies...
cd website
call npm install --legacy-peer-deps
cd ..

echo.
echo [4/4] Installing Mobile App Dependencies...
cd mobile-app
call npm install --legacy-peer-deps
cd ..

echo.
echo ==========================================
echo           Setup Complete!
echo ==========================================
pause
