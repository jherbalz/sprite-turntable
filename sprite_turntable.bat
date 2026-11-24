@echo off
REM Sprite Turntable - makes a fake-3D sprite sheet from a 3D model.
REM
REM Usage:
REM   sprite_turntable.bat --model model.glb --out .\sheet --angles 64
REM
REM Needs Blender (free). If Blender is somewhere unusual, set BLENDER_EXE
REM to the full path of blender.exe before running this.

setlocal
set "HERE=%~dp0"
if not "%BLENDER_EXE%"=="" set "BT_BLENDER=%BLENDER_EXE%"
if not defined BT_BLENDER call :find_blender
if not defined BT_BLENDER (
  echo.
  echo Could not find Blender.
  echo.
  echo Install Blender from https://www.blender.org/download/ and run this again,
  echo or set BLENDER_EXE to the full path of blender.exe.
  echo.
  exit /b 1
)
echo Using Blender: %BT_BLENDER%
"%BT_BLENDER%" --background --factory-startup --python "%HERE%sprite_turntable.py" -- %*
exit /b %ERRORLEVEL%

:find_blender
for %%P in (
  "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
  "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
  "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
  "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
  "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
  "C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"
  "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
  "C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"
  "C:\Program Files\Blender Foundation\Blender 3.6\blender.exe"
) do (
  if exist %%P if not defined BT_BLENDER set "BT_BLENDER=%%~P"
)
goto :eof
