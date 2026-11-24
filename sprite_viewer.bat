@echo off
REM Sprite Turntable - play a sheet that was already made.
REM
REM Usage:
REM   sprite_viewer.bat C:\path\to\your\sheet
REM
REM The player is the sprite_viewer.html file that sits in the sheet folder.

if "%~1"=="" (
  echo Give it the folder that holds your frames.
  exit /b 1
)
if not exist "%~1\sprite_viewer.html" (
  echo No sprite_viewer.html in "%~1".
  echo Make the sheet first - the player is written next to the frames.
  exit /b 1
)
start "" "%~1\sprite_viewer.html"
exit /b 0
