@echo off
chcp 65001 > nul
cls
title SIGEduc Auto - Instalador da Extensão

echo ======================================================================
echo             SIGEduc Auto — Lançador de Notas (Extensão)
echo ======================================================================
echo.
echo Olá, Professor(a)!
echo Este assistente vai preparar a extensão para instalação no seu navegador.
echo.

set "ORIGEM=%~dp0"
set "DESTINO=%LOCALAPPDATA%\SIGEduc-Extensao"

echo [1/3] Configurando pasta segura permanente...
if not exist "%DESTINO%" mkdir "%DESTINO%"
robocopy "%ORIGEM%." "%DESTINO%." /E /XD tests scripts /XF *.zip *.bat > nul 2>&1
if not exist "%DESTINO%\manifest.json" (
    xcopy /E /I /Y "%ORIGEM%*" "%DESTINO%" > nul 2>&1
)
echo       ✓ Extensão salva com segurança em:
echo         %DESTINO%
echo.

echo [2/3] Escolha o seu navegador principal:
echo.
echo   [1] Google Chrome
echo   [2] Microsoft Edge
echo   [3] Brave Browser
echo   [4] Opera / Opera GX
echo   [5] Outro navegador Chromium
echo.
set /p OPCAO="Digite o número correspondente [1 a 5]: "

echo.
echo [3/3] Abrindo a página de extensões e a pasta de arquivos...

if "%OPCAO%"=="1" (
    start chrome "chrome://extensions" > nul 2>&1
) else if "%OPCAO%"=="2" (
    start msedge "edge://extensions" > nul 2>&1
) else if "%OPCAO%"=="3" (
    start brave "brave://extensions" > nul 2>&1
) else if "%OPCAO%"=="4" (
    start opera "opera://extensions" > nul 2>&1
) else (
    start "" "chrome://extensions" > nul 2>&1
)

:: Abre a pasta da extensão no Windows Explorer para facilitar o carregamento
explorer "%DESTINO%"

echo.
echo ======================================================================
echo                  PASSO A PASSO FINAL (SUPER FÁCIL!):
echo ======================================================================
echo.
echo 1. Na janela de extensões que acabou de abrir no seu navegador:
echo    -> Ative a chavinha "Modo do desenvolvedor" (no canto superior direito).
echo.
echo 2. Clique no botão "Carregar sem compactação" (Load unpacked).
echo.
echo 3. Selecione a pasta que acabou de abrir no Windows Explorer:
echo    -> "%DESTINO%"
echo.
echo ======================================================================
echo Pronto! O ícone 📊 SIGEduc Auto aparecerá no topo do seu navegador!
echo Dica: Clique no ícone de 'Quebra-cabeça' da barra e fixe a extensão.
echo ======================================================================
echo.
pause
