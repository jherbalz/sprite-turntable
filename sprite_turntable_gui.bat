@echo off
REM Sprite Turntable - the window. Pick a model, press MAKE SPRITE SHEET.
REM
REM Usage:
REM   sprite_turntable_gui.bat
REM
REM Needs Blender (free). If Blender is somewhere unusual, set BLENDER_EXE
REM to the full path of blender.exe before running this.

powershell -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0sprite_turntable_gui.ps1"
exit /b %ERRORLEVEL%
