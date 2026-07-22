@echo off
rem Wrapper so agy invokes the packaged Warden adapter as a single space-free token.
rem agy does not strip quotes from the hooks.json command; a .bat is cmd-native and passes
rem stdin/stdout through cleanly. %~dp0 = this file's own directory, so it is location-independent.
python "%~dp0agy_warden_adapter.py"
