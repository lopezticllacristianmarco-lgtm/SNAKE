@echo off
setlocal EnableExtensions
set "DIR=%CD%"
echo ============================================================
echo   SNAKE GAME - Instalacion automatica
echo   (descarga pequena: solo pygame, que se necesita para jugar)
echo ============================================================
echo.

REM ---- 1) Buscar Python (py launcher o directamente en PATH) ----
set "PYCMD="
where py >nul 2>&1 && set "PYCMD=py"
if not defined PYCMD (
    where python >nul 2>&1 && set "PYCMD=python"
)
if not defined PYCMD (
    echo [ERROR] No se encontro Python.
    echo Descargas Python 3.10+ desde  https://www.python.org/downloads/
    echo IMPORTANTE: al instalar, marca la casilla "Add python.exe to PATH".
    echo Luego vuelve a ejecutar este `instalar.bat`.
    echo.
    pause
    exit /b 1
)
echo [1/4] Python detectado. Version:
%PYCMD% --version
echo.

REM ---- 2) Crear entorno virtual .venv ----
echo [2/4] Creando entorno virtual (.venv)... (solo la primera vez)
if not exist ".venv\Scripts\python.exe" (
    %PYCMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
)
set "VENVPY=%DIR%\.venv\Scripts\python.exe"
echo.

REM ---- 3) Instalar dependencias (descarga pygame) ----
echo [3/4] Instalando dependencias (pygame). Esto descarga lo necesario...
"%VENVPY%" -m pip install --upgrade pip >nul
"%VENVPY%" -m pip install -e .
if errorlevel 1 (
    echo [ERROR] Fallo al instalar las dependencias. Revisa tu conexion a internet.
    pause
    exit /b 1
)
echo.

echo ============================================================
echo   INSTALACION COMPLETADA CORRECTAMENTE!
echo   Para jugar, doble clic en  ejecutar.bat
echo ============================================================
echo.
pause
