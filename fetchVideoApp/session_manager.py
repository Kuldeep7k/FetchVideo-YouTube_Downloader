"""
Session-based temporary directory and video caching management for FetchVideo
"""
import os
import shutil
import hashlib
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.contrib.sessions.models import Session

logger = logging.getLogger(__name__)

class SessionTempManager:
    """Manages temporary directories and video caching based on user sessions"""

    @staticmethod
    def get_session_temp_dir(request):
        """Get or create a session-specific temporary directory"""
        session_key = request.session.session_key
        if not session_key:
            # Create session if it doesn't exist
            request.session.create()
            session_key = request.session.session_key

        temp_dir = os.path.join(settings.MEDIA_ROOT, f"session_{session_key}")
        os.makedirs(temp_dir, exist_ok=True)

        # Store temp dir in session for cleanup
        if 'temp_dirs' not in request.session:
            request.session['temp_dirs'] = []
        if temp_dir not in request.session['temp_dirs']:
            request.session['temp_dirs'].append(temp_dir)
            request.session.save()

        return temp_dir

    @staticmethod
    def cleanup_session_temp_dirs(session_key):
        """Clean up all temporary directories for a session"""
        try:
            session_temp_dir = os.path.join(settings.MEDIA_ROOT, f"session_{session_key}")
            if os.path.exists(session_temp_dir):
                shutil.rmtree(session_temp_dir)
                logger.info(f"Cleaned up session temp directory: {session_temp_dir}")
        except Exception as e:
            logger.error(f"Failed to cleanup session temp dir {session_key}: {str(e)}")

    @staticmethod
    def cleanup_expired_sessions():
        """Clean up temporary directories for expired sessions"""
        try:
            # Get all expired sessions
            expired_sessions = Session.objects.filter(
                expire_date__lt=datetime.now()
            )

            for session in expired_sessions:
                SessionTempManager.cleanup_session_temp_dirs(session.session_key)

            # Delete expired sessions from database
            expired_sessions.delete()
            logger.info(f"Cleaned up {expired_sessions.count()} expired sessions")

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {str(e)}")

class VideoCacheManager:
    """Manages caching of processed videos to avoid reprocessing"""

    CACHE_TIMEOUT = 3600  # 1 hour
    CACHE_KEY_PREFIX = "video_cache_"

    @staticmethod
    def get_cache_key(video_id, quality, audio_quality=None):
        """Generate a unique cache key for video processing"""
        key_parts = [video_id, quality]
        if audio_quality:
            key_parts.append(audio_quality)
        key_string = "_".join(key_parts)
        return f"{VideoCacheManager.CACHE_KEY_PREFIX}{hashlib.md5(key_string.encode()).hexdigest()}"

    @staticmethod
    def is_video_cached(video_id, quality, audio_quality=None):
        """Check if a video with specific quality is cached"""
        cache_key = VideoCacheManager.get_cache_key(video_id, quality, audio_quality)
        cached_data = cache.get(cache_key)
        if cached_data and os.path.exists(cached_data.get('file_path', '')):
            return cached_data
        return None

    @staticmethod
    def cache_video(video_id, quality, file_path, metadata=None, audio_quality=None):
        """Cache a processed video file"""
        cache_key = VideoCacheManager.get_cache_key(video_id, quality, audio_quality)

        cache_data = {
            'file_path': file_path,
            'created_at': datetime.now().isoformat(),
            'metadata': metadata or {},
            'video_id': video_id,
            'quality': quality,
            'audio_quality': audio_quality
        }

        cache.set(cache_key, cache_data, VideoCacheManager.CACHE_TIMEOUT)
        logger.info(f"Cached video: {video_id} at quality {quality}")

    @staticmethod
    def get_cached_video_path(video_id, quality, audio_quality=None):
        """Get the cached video file path if it exists"""
        cached_data = VideoCacheManager.is_video_cached(video_id, quality, audio_quality)
        if cached_data:
            return cached_data['file_path']
        return None

    @staticmethod
    def clear_video_cache(video_id=None):
        """Clear video cache, optionally for a specific video"""
        try:
            if video_id:
                # Clear cache for specific video
                cache_keys = cache.keys(f"{VideoCacheManager.CACHE_KEY_PREFIX}*")
                for key in cache_keys:
                    cached_data = cache.get(key)
                    if cached_data and cached_data.get('video_id') == video_id:
                        cache.delete(key)
                        # Also remove the file if it exists
                        file_path = cached_data.get('file_path')
                        if file_path and os.path.exists(file_path):
                            os.remove(file_path)
                logger.info(f"Cleared cache for video: {video_id}")
            else:
                # Clear all video cache
                cache.delete_pattern(f"{VideoCacheManager.CACHE_KEY_PREFIX}*")
                logger.info("Cleared all video cache")
        except Exception as e:
            logger.error(f"Failed to clear video cache: {str(e)}")

    @staticmethod
    def cleanup_expired_cache():
        """Clean up expired cache entries and their associated files"""
        try:
            cache_keys = cache.keys(f"{VideoCacheManager.CACHE_KEY_PREFIX}*")
            cleaned_count = 0

            for key in cache_keys:
                cached_data = cache.get(key)
                if cached_data:
                    file_path = cached_data.get('file_path')
                    if file_path and os.path.exists(file_path):
                        # Check if file is older than cache timeout
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if datetime.now() - file_mtime > timedelta(seconds=VideoCacheManager.CACHE_TIMEOUT):
                            os.remove(file_path)
                            cache.delete(key)
                            cleaned_count += 1

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired cached videos")

        except Exception as e:
            logger.error(f"Failed to cleanup expired cache: {str(e)}")