@echo off
setlocal
cd /d D:\GitHub\YTDownloader
"C:\Program Files\Python310\python.exe" scripts\build_installer.py
set CODE=%errorlevel%
echo EXITCODE=%CODE% > "D:\GitHub\YTDownloader\build_logs\win_build_installer_live.exit.log"
exit /b %CODE%
