"""
Signal handlers for session cleanup and cache management
"""
import logging
from django.core.signals import request_finished
from django.dispatch import receiver
from .session_manager import SessionTempManager, VideoCacheManager

logger = logging.getLogger(__name__)

@receiver(request_finished)
def cleanup_on_request_finished(sender, **kwargs):
    """Perform cleanup operations when a request finishes"""
    try:
        # Clean up expired sessions and cache periodically
        import random
        if random.random() < 0.05:  # 5% chance on each request to avoid overhead
            SessionTempManager.cleanup_expired_sessions()
            VideoCacheManager.cleanup_expired_cache()
            logger.info("Performed periodic cleanup")
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")