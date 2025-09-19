"""
Management command to clean up expired sessions and cached videos
"""
from django.core.management.base import BaseCommand
from fetchVideoApp.session_manager import SessionTempManager, VideoCacheManager


class Command(BaseCommand):
    help = 'Clean up expired sessions and cached videos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it',
        )
        parser.add_argument(
            '--cache-only',
            action='store_true',
            help='Only clean up expired cache, not sessions',
        )
        parser.add_argument(
            '--sessions-only',
            action='store_true',
            help='Only clean up expired sessions, not cache',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        cache_only = options['cache_only']
        sessions_only = options['sessions_only']

        if dry_run:
            self.stdout.write('DRY RUN - No actual cleanup will be performed\n')

        if not sessions_only:
            self.stdout.write('Cleaning up expired video cache...')
            try:
                VideoCacheManager.cleanup_expired_cache()
                self.stdout.write(
                    self.style.SUCCESS('Successfully cleaned up expired video cache')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to cleanup video cache: {str(e)}')
                )

        if not cache_only:
            self.stdout.write('Cleaning up expired sessions...')
            try:
                SessionTempManager.cleanup_expired_sessions()
                self.stdout.write(
                    self.style.SUCCESS('Successfully cleaned up expired sessions')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to cleanup sessions: {str(e)}')
                )

        self.stdout.write(self.style.SUCCESS('Cleanup completed!'))