#!/usr/bin/env python
"""
Standalone cleanup scheduler for FetchVideo
Run this as a background process or cron job for cleanup when server is not running
"""
import os
import sys
import time
import logging
from datetime import datetime

# Add Django project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fetchVideoProject.settings')

import django
django.setup()

from fetchVideoApp.session_manager import SessionTempManager, VideoCacheManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleanup_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CleanupScheduler:
    """Standalone cleanup scheduler that runs independently of Django server"""

    def __init__(self, interval_minutes=30):
        self.interval_seconds = interval_minutes * 60
        self.running = True

    def cleanup_cycle(self):
        """Perform one complete cleanup cycle"""
        try:
            logger.info("Starting cleanup cycle...")

            # Clean expired sessions
            SessionTempManager.cleanup_expired_sessions()

            # Clean expired cache
            VideoCacheManager.cleanup_expired_cache()

            logger.info("Cleanup cycle completed successfully")

        except Exception as e:
            logger.error(f"Cleanup cycle failed: {str(e)}")

    def run_forever(self):
        """Run cleanup scheduler continuously"""
        logger.info(f"Starting cleanup scheduler (interval: {self.interval_seconds//60} minutes)")

        while self.running:
            try:
                self.cleanup_cycle()
                logger.info(f"Sleeping for {self.interval_seconds//60} minutes...")
                time.sleep(self.interval_seconds)

            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                self.running = False
            except Exception as e:
                logger.error(f"Unexpected error in cleanup scheduler: {str(e)}")
                time.sleep(60)  # Wait 1 minute before retrying

        logger.info("Cleanup scheduler stopped")

    def run_once(self):
        """Run cleanup once and exit"""
        logger.info("Running one-time cleanup...")
        self.cleanup_cycle()
        logger.info("One-time cleanup completed")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='FetchVideo Cleanup Scheduler')
    parser.add_argument('--once', action='store_true', help='Run cleanup once and exit')
    parser.add_argument('--interval', type=int, default=30, help='Cleanup interval in minutes (default: 30)')

    args = parser.parse_args()

    scheduler = CleanupScheduler(interval_minutes=args.interval)

    if args.once:
        scheduler.run_once()
    else:
        scheduler.run_forever()