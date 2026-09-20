@echo off
echo ========================================================
echo Running TaskForge Backend Pytest Suite
echo ========================================================

cd /d "%~dp0\..\backend"
pytest tests/ -v

if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] All backend tests passed!
) else (
    echo [FAILURE] Tests failed with exit code %ERRORLEVEL%
)
