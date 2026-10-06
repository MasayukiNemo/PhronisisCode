@echo off
rem ============================================================
rem  quiz_web_stub.bat - offline demo launcher (no agy / no quota)
rem  Same as quiz_web.bat --stub. Safe for a first look.
rem  Extra args are forwarded, e.g. quiz_web_stub.bat --port 8765
rem ============================================================
call "%~dp0quiz_web.bat" --stub %*
exit /b %ERRORLEVEL%
