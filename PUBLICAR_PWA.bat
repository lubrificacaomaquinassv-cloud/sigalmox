@echo off
chcp 65001 >nul
set WS=D:\borracharia\SIGALMOX
set SRC=%WS%\pwa-sigalmox
set REPO=D:\git-sigcf\painel-frota-sv\almox

echo.
echo  PUBLICAR PWA SIGALMOX — GitHub Pages
echo  =====================================
echo.

if not exist "%SRC%\index.html" (
  echo ERRO: pasta fonte nao encontrada: %SRC%
  pause
  exit /b 1
)

if not exist "%REPO%" mkdir "%REPO%"
xcopy /E /Y /I "%SRC%\*" "%REPO%\"
echo sigalmox-v1> "%REPO%\version.txt"

cd /d "D:\git-sigcf\painel-frota-sv"
git -c safe.directory=D:/git-sigcf/painel-frota-sv add almox
git -c safe.directory=D:/git-sigcf/painel-frota-sv status -sb
echo.
set /p OK=Digite S para commit+push ou Enter para sair:
if /i not "%OK%"=="S" exit /b 0

git -c safe.directory=D:/git-sigcf/painel-frota-sv commit -m "Adiciona PWA SIGALMOX retirada estoque"
git -c safe.directory=D:/git-sigcf/painel-frota-sv push origin main
echo.
echo  Aguarde 1-2 min:
echo  https://lubrificacaomaquinassv-cloud.github.io/painel-frota-sv/almox/
pause
