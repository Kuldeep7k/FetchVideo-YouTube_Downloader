from django.db import models
from django.utils import timezone

def format_file_size(bytes_size):
    """Format file size in human readable format"""
    if not bytes_size:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return ".1f"
        bytes_size /= 1024.0
    return ".1f"

class Video(models.Model):
    title = models.CharField(max_length=255)
    url = models.URLField()
    video_id = models.CharField(max_length=100, unique=True)
    channel_title = models.CharField(max_length=254)
    duration = models.CharField(max_length=20)
    thumbnail_url = models.URLField()
    views = models.PositiveIntegerField(default=0)

    # Enhanced fields
    description = models.TextField(blank=True, null=True)
    publish_date = models.DateTimeField(blank=True, null=True)
    tags = models.JSONField(blank=True, null=True)  # Store video tags
    category = models.CharField(max_length=100, blank=True, null=True)
    is_available = models.BooleanField(default=True)

    # Download tracking
    download_count = models.PositiveIntegerField(default=0)
    last_downloaded = models.DateTimeField(blank=True, null=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['video_id']),
            models.Index(fields=['channel_title']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self) -> str:
        return f"{self.video_id} | {self.title}"

    def get_video_age(self):
        """Return how old the video is in days"""
        if self.publish_date:
            return (timezone.now() - self.publish_date).days
        return None

    def increment_download(self):
        """Increment download count and update timestamp"""
        self.download_count += 1
        self.last_downloaded = timezone.now()
        self.save(update_fields=['download_count', 'last_downloaded'])

class DownloadHistory(models.Model):
    """Track download history for analytics"""
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='downloads')
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    quality = models.CharField(max_length=20)
    format = models.CharField(max_length=10, default='mp4')
    file_size = models.PositiveIntegerField(blank=True, null=True)  # in bytes
    download_time = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-download_time']
        indexes = [
            models.Index(fields=['video', 'download_time']),
            models.Index(fields=['ip_address']),
        ]

    def __str__(self):
        return f"{self.video.title} - {self.quality} - {self.download_time}"

    def get_file_size_formatted(self):
        """Return formatted file size"""
        if not self.file_size:
            return "Unknown"
        return format_file_size(self.file_size)

class ProcessingLog(models.Model):
    """Log video processing operations"""
    video_id = models.CharField(max_length=100)
    operation = models.CharField(max_length=50)  # fetch, download, merge, etc.
    status = models.CharField(max_length=20)  # success, error, warning
    message = models.TextField()
    duration = models.FloatField(blank=True, null=True)  # in seconds
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['video_id', 'created_at']),
            models.Index(fields=['operation', 'status']),
        ]

    def __str__(self):
        return f"{self.video_id} - {self.operation} - {self.status}"



