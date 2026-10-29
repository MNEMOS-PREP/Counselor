@echo off
REM ============================================================
REM  M16 - Counselor, on its own.
REM
REM  This module's services only (PORTS.txt: API 8116, web 5216).
REM  It reads M06 (interview reports) and M04 (profile, skill
REM  graph); without M06 there is no report to talk through.
REM
REM  Usage:  start_counselor.bat          launch M16
REM          start_counselor.bat -Check   verify prerequisites only
REM ============================================================

cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launch.ps1" -Only m16 -Title "M16 - Counselor" %*
