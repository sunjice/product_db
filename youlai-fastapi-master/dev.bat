@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
fastapi dev app\main.py
