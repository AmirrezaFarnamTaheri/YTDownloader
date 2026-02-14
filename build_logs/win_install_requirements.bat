@echo off
setlocal
cd /d D:\GitHub\YTDownloader
"C:\Program Files\Python310\python.exe" -m pip install -r requirements.txt > "D:\GitHub\YTDownloader\build_logs\win_install_requirements.log" 2>&1
echo EXITCODE=%errorlevel% > "D:\GitHub\YTDownloader\build_logs\win_install_requirements.exit.log"
endlocal
