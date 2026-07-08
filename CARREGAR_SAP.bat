@echo off
cd /d "%~dp0"
if "%~1"=="" (
  echo Uso: CARREGAR_SAP.bat "caminho\lista.xlsx" "Categoria"
  echo Exemplo: CARREGAR_SAP.bat "%USERPROFILE%\Desktop\MEDICAMENTOS.xlsx" "Medicamentos Pecuaria"
  pause
  exit /b 1
)
set CATEG=%~2
if "%CATEG%"=="" set CATEG=Medicamentos Pecuaria
python carregar_produtos_sap.py "%~1" --categoria "%CATEG%" --gerar-pdf
pause
