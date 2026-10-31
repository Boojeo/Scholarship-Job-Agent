@echo off
REM Starts the Career Autopilot Telegram bot. Put a shortcut to this file in shell:startup to run it at login.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python main.py run
pause
