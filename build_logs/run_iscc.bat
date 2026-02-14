@echo off
set APP_VERSION=2.0.0
"C:\Users\Acer\AppData\Local\Programs\Inno Setup 6\ISCC.exe" "D:\GitHub\YTDownloader\installers\setup.iss" > "D:\GitHub\YTDownloader\build_logs\iscc_build.log" 2>&1
exit /b %errorlevel%
