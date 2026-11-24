@echo off
cd /d "C:\Users\B6822149\Documents\Default Project\transistor-simulator"
set GIT="C:\Users\B6822149\AppData\Local\Programs\Git\bin\git.exe"
set /p TOKEN="Paste GitHub PAT (classic, repo scope): "
%GIT% remote set-url origin "https://pepo2391256-stack:%TOKEN%@github.com/pepo2391256-stack/Lab04.git"
%GIT% push -u origin master:main
set ERR=%ERRORLEVEL%
%GIT% remote set-url origin "https://github.com/pepo2391256-stack/Lab04.git"
if %ERR% NEQ 0 (
  echo.
  echo PUSH FAILED - check token / repo permission
  pause
  exit /b %ERR%
)
echo.
echo PUSH SUCCESS - check https://github.com/pepo2391256-stack/Lab04
pause
