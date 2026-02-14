@echo off
setlocal
set PY="C:\Program Files\Python310\python.exe"
%PY% -m nuitka --version > "D:\GitHub\YTDownloader\build_logs\win_nuitka_version.log" 2>&1
echo EXITCODE=%errorlevel% > "D:\GitHub\YTDownloader\build_logs\win_nuitka_exit.log"
endlocal
