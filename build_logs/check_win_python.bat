@echo off
"C:\Program Files\Python310\python.exe" -V > "D:\GitHub\YTDownloader\build_logs\win_python_version.log" 2>&1
set ERR1=%errorlevel%
"C:\Python314\python.exe" -V > "D:\GitHub\YTDownloader\build_logs\win_python314_version.log" 2>&1
set ERR2=%errorlevel%
echo ERR1=%ERR1% ERR2=%ERR2%
exit /b 0
