@echo off
setlocal EnableExtensions
set "DIR=%CD%"

if not exist ".venv\Scripts\python.exe" (
    echo [AVISO] Aun no esta instalado. Ejecuta primero  instalar.bat
    pause
    exit /b 1
)

start "" ".venv\Scripts\python.exe" -m snake_game
if errorlevel 1 (
    echo [ERROR] No se pudo iniciar el juego.
    pause
)
