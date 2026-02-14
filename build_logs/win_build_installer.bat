@echo off
setlocal
cd /d D:\GitHub\YTDownloader
"C:\Program Files\Python310\python.exe" scripts\build_installer.py > "D:\GitHub\YTDownloader\build_logs\win_build_installer.log" 2>&1
echo EXITCODE=%errorlevel% > "D:\GitHub\YTDownloader\build_logs\win_build_installer.exit.log"
endlocal
