@echo off
echo =======================================================
echo          Installing VIGH-02 AI AGENT Globally
echo =======================================================
echo.

cd /d "%~dp0"

echo [1/3] Installing package in editable mode with pip...
pip install -e .
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install package via pip.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Registering global command wrappers...
python -m vigh_agent.cli --install-global

echo.
echo [3/3] Checking Local AI Models...
python -c "from vigh_agent.models.registry import model_registry; models = model_registry.scan_all_models(); print(f'Detected {len(models)} local models: ' + ', '.join([m['name'] for m in models]) if models else 'No local models running yet. Start Ollama with `ollama serve`')"

echo.
echo =======================================================
echo   VIGH-02 AI AGENT Installation Complete!
echo =======================================================
echo You can now open ANY folder in terminal and type:
echo   vigh-02
echo or
echo   vigh-02 --web
echo   vigh-02 --cli
echo =======================================================
echo.
pause
