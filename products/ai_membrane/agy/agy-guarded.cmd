@echo off
rem Double-clickable / cmd entry point for the guarded agy launcher (packaged).
rem Bypasses PowerShell execution policy and forwards all arguments. %~dp0 = this folder.
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0run_agy.ps1" %*
