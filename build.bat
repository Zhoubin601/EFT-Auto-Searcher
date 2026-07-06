@echo off
echo Building Vue frontend...
cd EFK-WebUI
call npm install
call npm run build
cd ..

echo.
echo Packaging Python backend...
pip install pyinstaller

:: Package into a single executable
pyinstaller --noconfirm --onefile --windowed --add-data "EFK-WebUI/dist;dist" EFK/GameStart.py

echo.
echo Build complete! The executable is located in the 'dist' folder.
pause
