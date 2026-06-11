@echo off
cd /d C:\apps\document_scanner
call .venv\Scripts\activate.bat
python backend\server.py
pause
