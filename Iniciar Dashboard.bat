@echo off
setlocal
title Dashboard WBE-IoT
cd /d "%~dp0"
if errorlevel 1 goto pasta_invalida

if not exist "frontend\app.py" (
    echo Arquivo frontend\app.py nao encontrado.
    echo Mantenha este batch na pasta principal do projeto TCC.
    goto erro
)

if exist ".venv\Scripts\python.exe" (
    set "DASH_PYTHON=%~dp0.venv\Scripts\python.exe"
    goto executar
)
if exist "venv\Scripts\python.exe" (
    set "DASH_PYTHON=%~dp0venv\Scripts\python.exe"
    goto executar
)
python -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set "DASH_PYTHON=python"
    goto executar
)
py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set "DASH_PYTHON=py"
    goto executar_py
)
echo Python nao encontrado. Instale o Python e habilite a opcao Add Python to PATH.
goto erro

:executar
"%DASH_PYTHON%" -c "import streamlit, plotly, pandas, numpy, sqlalchemy, psycopg" >nul 2>&1
if errorlevel 1 (
    echo Faltam dependencias da aplicacao.
    echo Execute uma vez na pasta do projeto:
    echo "%DASH_PYTHON%" -m pip install -r requirements\frontend.txt
    goto erro
)
echo Projeto: %CD%
echo Iniciando o dashboard atualizado. O navegador sera aberto automaticamente.
echo Mantenha esta janela aberta enquanto usa a aplicacao.
echo Para encerrar, pressione Ctrl+C nesta janela.
echo.
"%DASH_PYTHON%" -m streamlit run "%~dp0frontend\app.py" --server.address localhost --server.port 8501 --server.headless false
if errorlevel 1 goto erro
exit /b 0

:executar_py
py -3 -c "import streamlit, plotly, pandas, numpy, sqlalchemy, psycopg" >nul 2>&1
if errorlevel 1 (
    echo Faltam dependencias da aplicacao.
    echo Execute uma vez na pasta do projeto:
    echo py -3 -m pip install -r requirements\frontend.txt
    goto erro
)
echo Projeto: %CD%
echo Iniciando o dashboard atualizado. O navegador sera aberto automaticamente.
echo Mantenha esta janela aberta enquanto usa a aplicacao.
echo Para encerrar, pressione Ctrl+C nesta janela.
echo.
py -3 -m streamlit run "%~dp0frontend\app.py" --server.address localhost --server.port 8501 --server.headless false
if errorlevel 1 goto erro
exit /b 0

:pasta_invalida
echo Nao foi possivel acessar a pasta do projeto.
:erro
echo.
echo Nao foi possivel iniciar o dashboard. Confira a mensagem acima.
pause
exit /b 1
