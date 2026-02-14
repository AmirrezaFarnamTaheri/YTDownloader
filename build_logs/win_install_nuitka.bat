@echo off
setlocal
set PY="C:\Program Files\Python310\python.exe"
%PY% -m pip install --upgrade pip > "D:\GitHub\YTDownloader\build_logs\win_pip_upgrade.log" 2>&1
%PY% -m pip install nuitka > "D:\GitHub\YTDownloader\build_logs\win_install_nuitka.log" 2>&1
echo EXITCODE=%errorlevel% > "D:\GitHub\YTDownloader\build_logs\win_install_nuitka.exit.log"
endlocal
