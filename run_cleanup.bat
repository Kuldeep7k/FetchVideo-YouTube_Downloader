@echo off
REM FetchVideo Cleanup Scheduler - Windows Batch Script
REM Run this periodically to clean up expired sessions and cache

cd /d "%~dp0"
echo Starting FetchVideo cleanup process...
python cleanup_scheduler.py --once
echo Cleanup completed at %DATE% %TIME%
pause