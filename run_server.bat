@echo off
echo Stopping existing Python processes to prevent port conflicts...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM py.exe 2>nul

echo Starting Financial Analyst Server...
echo The dashboard will be available at http://localhost:8000
py -3 server.py
pause
