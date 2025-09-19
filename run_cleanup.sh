#!/bin/bash
# FetchVideo Cleanup Scheduler - Linux/Mac Script
# Run this periodically to clean up expired sessions and cache

cd "$(dirname "$0")"
echo "Starting FetchVideo cleanup process..."
python cleanup_scheduler.py --once
echo "Cleanup completed at $(date)"