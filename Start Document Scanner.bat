@echo off
cd /d C:\apps\document_scanner
call .venv\Scripts\activate.bat
cd camera-scanner\backend
python server.py
pause
