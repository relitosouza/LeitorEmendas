@echo off
echo -----------------------------------------
echo    INICIANDO ROBO DE PREENCHIMENTO
echo -----------------------------------------
echo.
echo 1. Certifique-se que o "Chrome Robo" esta aberto.
echo 2. Aguarde o servidor ligar...
echo.
timeout /t 2 >nul
start http://127.0.0.1:5000
python app.py
pause