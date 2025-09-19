import os
import re
import shlex
import subprocess
import logging
import json
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django import forms
from django.conf import settings
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views import View
from pytubefix import YouTube
from .forms import VideoForm
from .models import Video
from datetime import datetime, timedelta
from urllib.parse import urlparse
import requests
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import threading
import time

# Setup logging
logger = logging.getLogger(__name__)

def contact(request):
    # Redirect to youtube.com
    return redirect('https://www.youtube.com/')

def about(request):
    # Render the aboutus.html template
    return render(request, 'about.html')

def privacypolicy(request):
    # Render the contactus.html template
    return render(request, 'privacypolicy.html')

def dmca(request):
    # Render the aboutus.html template
    return render(request, 'dmca.html')

def index(request):
    if request.method == 'POST':
        form = VideoForm(request.POST)
        if form.is_valid():
            youtube_link = form.cleaned_data['youtube_link']
            video_id = get_video_id(youtube_link)

            try:
                video = fetch_video_details(video_id)
                if video:
                    return redirect('FetchVideoApp:video_detail', video_id=video_id)
                else:
                    raise Exception("Unable to fetch video details.")
            except Exception as e:
                error_message = str(e)
                return render(request, 'error_page.html', {'error_message': error_message})

    else:
        form = VideoForm()

    return render(request, 'index.html', {'form': form})

# Get the base directory of the Django project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define the path to the FFmpeg executable
FFmpeg_PATH = os.path.join(BASE_DIR, 'ffmpeg', 'bin', 'ffmpeg.exe')

# Video processing status cache key prefix
VIDEO_STATUS_KEY = 'video_processing_status_'

class VideoProcessor:
    """Enhanced video processor with progress tracking and error handling"""

    def __init__(self, video_id):
        self.video_id = video_id
        self.status_key = f"{VIDEO_STATUS_KEY}{video_id}"
        self._update_status('initialized', 0, 'Video processor initialized')

    def _update_status(self, status, progress, message):
        """Update processing status in cache"""
        cache.set(self.status_key, {
            'status': status,
            'progress': progress,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }, timeout=3600)  # 1 hour timeout

    def get_status(self):
        """Get current processing status"""
        return cache.get(self.status_key, {
            'status': 'unknown',
            'progress': 0,
            'message': 'Status unknown',
            'timestamp': datetime.now().isoformat()
        })

def seconds_to_hhmmss(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def format_file_size(bytes_size):
    """Format file size in human readable format"""
    if not bytes_size:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} GB"

def is_valid_youtube_url(url):
    """Enhanced URL validation with better regex"""
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})'
    ]

    for pattern in patterns:
        if re.match(pattern, url):
            return True
    return False

def get_video_id(youtube_link):
    """Extract video ID from various YouTube URL formats"""
    video_id = None
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([^&\n?#]+)',
        r'youtube\.com/v/([^&\n?#]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, youtube_link)
        if match:
            video_id = match.group(1)
            break

    return video_id


def remove_emojis(text):
    """Remove emoji characters from text with better Unicode support"""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"  # Enclosed Alphanumerics
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)


def fetch_video_details(video_id, processor=None):
    """Enhanced video details fetching with progress tracking"""
    try:
        if processor:
            processor._update_status('fetching', 10, 'Fetching video details from YouTube...')

        # Check cache first
        cache_key = f"video_details_{video_id}"
        cached_video = cache.get(cache_key)
        if cached_video:
            if processor:
                processor._update_status('completed', 100, 'Video details loaded from cache')
            return cached_video

        # Try to get from database
        try:
            video = Video.objects.get(video_id=video_id)
            if processor:
                processor._update_status('completed', 100, 'Video details loaded from database')
            cache.set(cache_key, video, timeout=3600)  # Cache for 1 hour
            return video
        except Video.DoesNotExist:
            pass

        if processor:
            processor._update_status('processing', 30, 'Connecting to YouTube...')

        youtube_link = f'https://www.youtube.com/watch?v={video_id}'

        try:
            yt = YouTube(youtube_link)

            if processor:
                processor._update_status('processing', 60, 'Extracting video information...')

            title = remove_emojis(yt.title or 'Unknown Title')
            author = remove_emojis(yt.author or 'Unknown Author')

            # Get additional metadata
            try:
                view_count = yt.views or 0
                publish_date = yt.publish_date
                description = yt.description[:500] if yt.description else ''
            except:
                view_count = 0
                publish_date = None
                description = ''

            video = Video(
                title=title,
                url=youtube_link,
                video_id=video_id,
                channel_title=author,
                duration=str(seconds_to_hhmmss(yt.length)),
                thumbnail_url=yt.thumbnail_url,
                views=view_count,
                description=description,
                publish_date=publish_date
            )
            video.save()

            # Cache the result
            cache.set(cache_key, video, timeout=3600)

            if processor:
                processor._update_status('completed', 100, 'Video details fetched successfully')

            logger.info(f"Successfully fetched video details for {video_id}")
            return video

        except Exception as e:
            error_msg = f"Failed to fetch video details: {str(e)}"
            logger.error(f"Error fetching video {video_id}: {error_msg}")
            if processor:
                processor._update_status('error', 0, error_msg)
            return None

    except Exception as e:
        error_msg = f"Unexpected error fetching video details: {str(e)}"
        logger.error(f"Unexpected error for video {video_id}: {error_msg}")
        if processor:
            processor._update_status('error', 0, error_msg)
        return None


class VideoDownloadForm(forms.Form):
    video_quality = forms.CharField(widget=forms.HiddenInput)
    audio_quality = forms.CharField(widget=forms.HiddenInput)


def extract_numeric_bitrate(abr):
    match = re.search(r'\d+', abr)
    return int(match.group()) if match else 0


def video_detail(request, video_id):
    """Enhanced video detail view with progress tracking and better error handling"""
    try:
        # Validate video_id format
        if not video_id or len(video_id) != 11:
            return render(request, 'error_page.html', {
                'error_message': 'Invalid video ID format'
            })

        # Create video processor for progress tracking
        processor = VideoProcessor(video_id)

        # Fetch video details with progress tracking
        video = fetch_video_details(video_id, processor)

        if not video:
            return render(request, 'error_page.html', {
                'error_message': 'Unable to fetch video details. Please check the URL and try again.'
            })

        # Increment views count
        video.views += 1
        video.save()

        processor._update_status('processing', 20, 'Analyzing available streams...')

        # Get all available video and audio qualities from pytube
        youtube_link = f'https://www.youtube.com/watch?v={video_id}'

        try:
            yt = YouTube(youtube_link)
        except Exception as e:
            logger.error(f"Failed to create YouTube object for {video_id}: {str(e)}")
            return render(request, 'error_page.html', {
                'error_message': 'Failed to connect to YouTube. Please try again later.'
            })

        processor._update_status('processing', 40, 'Processing video streams...')

        # Get all video streams and sort them by resolution in descending order
        try:
            video_streams = yt.streams.filter(type="video").order_by('resolution')
            video_streams = list(reversed(video_streams))
        except Exception as e:
            logger.error(f"Failed to get video streams for {video_id}: {str(e)}")
            return render(request, 'error_page.html', {
                'error_message': 'Failed to retrieve video streams. The video might be unavailable.'
            })

        # Initialize lists for video qualities with enhanced metadata
        av01_qualities = []
        vp9_qualities = []
        h264_qualities = []

        for stream in video_streams:
            try:
                resolution = stream.resolution or 'Unknown'
                codecs = stream.codecs or []
                fps = stream.fps or 30
                file_size = getattr(stream, 'filesize', 0) or getattr(stream, 'filesize_approx', 0) or 0

                stream_info = {
                    'format': resolution,
                    'fps': fps,
                    'url': stream.url,
                    'mime_type': stream.mime_type,
                    'codecs': codecs,
                    'itag': stream.itag,
                    'file_size': file_size,
                    'file_size_formatted': format_file_size(file_size) if file_size else 'Unknown'
                }

                # Categorize by codec
                if 'av01' in str(codecs).lower():
                    av01_qualities.append(stream_info)
                elif 'vp9' in str(codecs).lower():
                    vp9_qualities.append(stream_info)
                elif 'avc1' in str(codecs).lower():
                    h264_qualities.append(stream_info)

            except Exception as e:
                logger.warning(f"Error processing stream {stream.itag}: {str(e)}")
                continue

        # Priority: AV1 > VP9 > H264
        video_qualities = av01_qualities + vp9_qualities + h264_qualities

        processor._update_status('processing', 60, 'Processing audio streams...')

        # Get all available audio streams with enhanced metadata
        try:
            audio_streams = yt.streams.filter(type="audio")
        except Exception as e:
            logger.error(f"Failed to get audio streams for {video_id}: {str(e)}")
            return render(request, 'error_page.html', {
                'error_message': 'Failed to retrieve audio streams.'
            })

        audio_qualities = []
        for stream in audio_streams:
            try:
                file_size = getattr(stream, 'filesize', 0) or getattr(stream, 'filesize_approx', 0) or 0
                audio_qualities.append({
                    'itag': stream.itag,
                    'abr': stream.abr or 'Unknown',
                    'audio_codec': stream.audio_codec or 'Unknown',
                    'mime_type': stream.mime_type,
                    'url': stream.url,
                    'file_size': file_size,
                    'file_size_formatted': format_file_size(file_size) if file_size else 'Unknown'
                })
            except Exception as e:
                logger.warning(f"Error processing audio stream {stream.itag}: {str(e)}")
                continue

        # Sort audio qualities by bitrate (numerical value)
        audio_qualities.sort(key=lambda x: extract_numeric_bitrate(x['abr']), reverse=True)

        # Group by codec and keep only the highest quality for each codec
        codec_groups = {}
        for audio_quality in audio_qualities:
            codec = audio_quality['audio_codec'].lower() if audio_quality['audio_codec'] != 'Unknown' else 'unknown'
            bitrate = extract_numeric_bitrate(audio_quality['abr'])
            
            if codec not in codec_groups or bitrate > extract_numeric_bitrate(codec_groups[codec]['abr']):
                codec_groups[codec] = audio_quality

        # Convert back to list and sort by bitrate
        filtered_audio_qualities = list(codec_groups.values())
        filtered_audio_qualities.sort(key=lambda x: extract_numeric_bitrate(x['abr']), reverse=True)

        processor._update_status('processing', 80, 'Preparing download options...')

        # Prepare video_audio_qualities list with better pairing logic
        video_audio_qualities = []

        # Pair highest quality videos with highest quality audio
        min_length = min(len(video_qualities), len(filtered_audio_qualities))

        for i in range(min_length):
            video_audio_qualities.append((video_qualities[i], filtered_audio_qualities[i]))

        # Add remaining videos with best audio
        for i in range(min_length, len(video_qualities)):
            video_audio_qualities.append((video_qualities[i], filtered_audio_qualities[0] if filtered_audio_qualities else None))

        # Add remaining audio with best video
        for i in range(min_length, len(filtered_audio_qualities)):
            video_audio_qualities.append((video_qualities[0] if video_qualities else None, filtered_audio_qualities[i]))

        processor._update_status('completed', 100, 'Ready for download')

        # Handle video download form submission
        if request.method == 'POST':
            form = VideoDownloadForm(request.POST)
            if form.is_valid():
                video_quality = form.cleaned_data['video_quality']

                # Start async download process
                processor._update_status('downloading', 0, 'Starting download process...')

                try:
                    # Call the download function
                    video_name, temp_dir = download_video_with_best_audio(request, video_id, video_quality, processor)

                    if video_name and temp_dir:
                        processor._update_status('completed', 100, 'Download completed successfully')
                        return render(request, 'download.html', {
                            'video_name': video_name,
                            'temp_dir': temp_dir,
                            'video': video
                        })
                    else:
                        processor._update_status('error', 0, 'Download failed')
                        return render(request, 'error_page.html', {
                            'error_message': 'Download failed. Please try again.'
                        })
                except Exception as e:
                    logger.error(f"Download error for {video_id}: {str(e)}")
                    processor._update_status('error', 0, f'Download failed: {str(e)}')
                    return render(request, 'error_page.html', {
                        'error_message': f'Download failed: {str(e)}'
                    })
        else:
            form = VideoDownloadForm()

        # Add additional context for template
        context = {
            'video': video,
            'video_audio_qualities': video_audio_qualities,
            'video_qualities': video_qualities,
            'audio_qualities': filtered_audio_qualities,
            'form': form,
            'video_qualities_count': len(video_qualities),
            'audio_qualities_count': len(filtered_audio_qualities),
            'processor': processor
        }

        return render(request, 'video_details.html', context)

    except Exception as e:
        logger.error(f"Unexpected error in video_detail for {video_id}: {str(e)}")
        return render(request, 'error_page.html', {
            'error_message': f'An unexpected error occurred: {str(e)}'
        })


# Function to sanitize the video title
def sanitize_video_title(title):
    # Remove invalid symbols and replace spaces with underscores
    sanitized_title = re.sub(r'[^\w\s.-]', '', title)
    sanitized_title = sanitized_title.replace(' ', '_')
    return sanitized_title


def download_video_with_best_audio(request, video_id, video_quality, processor=None):
    from .session_manager import SessionTempManager, VideoCacheManager

    video = fetch_video_details(video_id)

    if not video:
        error_msg = "Video details not found"
        if processor:
            processor._update_status('error', 0, error_msg)
        return None, None

    try:
        if processor:
            processor._update_status('downloading', 5, 'Creating temporary directory...')

        # Check if video is already cached
        cached_video = VideoCacheManager.is_video_cached(video_id, video_quality)
        if cached_video:
            if processor:
                processor._update_status('completed', 100, 'Video loaded from cache!')
            cached_file_path = cached_video['file_path']
            # Return relative path from MEDIA_ROOT
            relative_path = os.path.relpath(os.path.dirname(cached_file_path), settings.MEDIA_ROOT)
            filename = os.path.basename(cached_file_path)
            return filename, relative_path

        # Create session-based temporary directory
        temp_dir = SessionTempManager.get_session_temp_dir(request)

        youtube_link = f'https://www.youtube.com/watch?v={video.video_id}'

        if processor:
            processor._update_status('downloading', 10, 'Connecting to YouTube...')

        yt = YouTube(youtube_link)

        if processor:
            processor._update_status('downloading', 15, 'Finding video stream...')

        # Try to get the video stream with the selected quality
        video_stream = yt.streams.filter(type="video", resolution=video_quality).first()

        if not video_stream:
            # Try alternative approach - find closest quality
            available_resolutions = [s.resolution for s in yt.streams.filter(type="video") if s.resolution]
            if available_resolutions:
                # Find closest resolution
                target_height = int(video_quality.split('p')[0])
                closest_resolution = min(available_resolutions,
                    key=lambda x: abs(int(x.split('p')[0]) - target_height))
                video_stream = yt.streams.filter(type="video", resolution=closest_resolution).first()

        if not video_stream:
            error_msg = f"No video stream found for quality {video_quality}"
            if processor:
                processor._update_status('error', 0, error_msg)
            return None, None

        if processor:
            processor._update_status('downloading', 20, 'Finding audio stream...')

        # Get available audio streams with improved selection
        audio_streams = yt.streams.filter(type="audio")

        # Priority: webm > mp4 for audio quality
        webm_audio = [s for s in audio_streams if s.mime_type == 'audio/webm']
        mp4_audio = [s for s in audio_streams if s.mime_type == 'audio/mp4']

        # Select best audio stream
        if webm_audio:
            audio_stream = sorted(webm_audio, key=lambda x: extract_numeric_bitrate(x.abr), reverse=True)[0]
        elif mp4_audio:
            audio_stream = sorted(mp4_audio, key=lambda x: extract_numeric_bitrate(x.abr), reverse=True)[0]
        else:
            audio_stream = sorted(audio_streams, key=lambda x: extract_numeric_bitrate(x.abr), reverse=True)[0]

        if not audio_stream:
            error_msg = "No suitable audio stream found"
            if processor:
                processor._update_status('error', 0, error_msg)
            return None, None

        if processor:
            processor._update_status('downloading', 30, 'Downloading video stream...')

        # Download video stream
        video_format = video_stream.subtype
        fps = int(video_stream.fps) if video_stream.fps else 30
        video_path = os.path.join(temp_dir, f"{video.video_id}_video.{video_format}")

        try:
            video_stream.download(output_path=temp_dir, filename=os.path.basename(video_path))
        except Exception as e:
            error_msg = f"Failed to download video stream: {str(e)}"
            if processor:
                processor._update_status('error', 0, error_msg)
            return None, None

        if processor:
            processor._update_status('downloading', 60, 'Downloading audio stream...')

        # Download audio stream
        audio_path = os.path.join(temp_dir, f"{video.video_id}_audio.{audio_stream.subtype}")

        try:
            audio_stream.download(output_path=temp_dir, filename=os.path.basename(audio_path))
        except Exception as e:
            error_msg = f"Failed to download audio stream: {str(e)}"
            if processor:
                processor._update_status('error', 0, error_msg)
            return None, None

        # Verify downloads
        if not os.path.exists(video_path) or not os.path.exists(audio_path):
            error_msg = "Downloaded files not found"
            if processor:
                processor._update_status('error', 0, error_msg)
            return None, None

        if processor:
            processor._update_status('downloading', 70, 'Processing audio format...')

        audio_format = os.path.splitext(audio_path)[1].lstrip('.')

        # Convert audio to compatible format if needed
        if audio_format in ['mp4', 'webm']:
            m4a_audio_path = os.path.join(temp_dir, f"{video.video_id}_audio.m4a")

            try:
                if audio_format == 'mp4':
                    cmd = f'"{FFmpeg_PATH}" -i "{audio_path}" -vn -c:a copy "{m4a_audio_path}"'
                elif audio_format == 'webm':
                    cmd = f'"{FFmpeg_PATH}" -i "{audio_path}" -vn -c:a aac -strict -2 "{m4a_audio_path}"'

                process = subprocess.Popen(shlex.split(cmd),
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                stdout, stderr = process.communicate(timeout=300)  # 5 minute timeout

                if process.returncode != 0:
                    error_msg = f"Audio conversion failed: {stderr.decode('utf-8', errors='ignore')}"
                    if processor:
                        processor._update_status('error', 0, error_msg)
                    return None, None

                # Replace audio path
                os.remove(audio_path)
                audio_path = m4a_audio_path

            except subprocess.TimeoutExpired:
                error_msg = "Audio conversion timed out"
                if processor:
                    processor._update_status('error', 0, error_msg)
                return None, None
            except Exception as e:
                error_msg = f"Audio conversion error: {str(e)}"
                if processor:
                    processor._update_status('error', 0, error_msg)
                return None, None

        if processor:
            processor._update_status('downloading', 80, 'Merging video and audio...')

        # Merge video and audio
        merged_filename = f"{sanitize_video_title(video.title)}_-_{video_quality}_{fps}fps.mp4"
        merged_path = os.path.join(temp_dir, merged_filename)

        try:
            cmd = f'"{FFmpeg_PATH}" -i "{video_path}" -i "{audio_path}" -c:v copy -c:a copy -avoid_negative_ts make_zero "{merged_path}"'

            process = subprocess.Popen(shlex.split(cmd),
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            stdout, stderr = process.communicate(timeout=600)  # 10 minute timeout

            if process.returncode != 0:
                error_msg = f"Merging failed: {stderr.decode('utf-8', errors='ignore')}"
                if processor:
                    processor._update_status('error', 0, error_msg)
                return None, None

        except subprocess.TimeoutExpired:
            error_msg = "Video merging timed out"
            if processor:
                processor._update_status('error', 0, error_msg)
            return None, None
        except Exception as e:
            error_msg = f"Merging error: {str(e)}"
            if processor:
                processor._update_status('error', 0, error_msg)
            return None, None

        # Verify merged file
        if not os.path.exists(merged_path):
            error_msg = "Merged video file not created"
            if processor:
                processor._update_status('error', 0, error_msg)
            return None, None

        if processor:
            processor._update_status('downloading', 90, 'Cleaning up temporary files...')

        # Clean up temporary files
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception as e:
            logger.warning(f"Failed to clean up temporary files: {str(e)}")

        if processor:
            processor._update_status('completed', 100, 'Download completed successfully!')

        # Cache the processed video
        VideoCacheManager.cache_video(
            video_id=video_id,
            quality=video_quality,
            file_path=merged_path,
            metadata={
                'title': video.title,
                'duration': getattr(video, 'duration', None),
                'author': getattr(video, 'author', None)
            }
        )

        relative_temp_dir = os.path.relpath(temp_dir, settings.MEDIA_ROOT)
        return merged_filename, relative_temp_dir

    except Exception as e:
        error_msg = f"Unexpected download error: {str(e)}"
        logger.error(f"Download error for {video_id}: {error_msg}")
        if processor:
            processor._update_status('error', 0, error_msg)
        return None, None


def download(request, temp_dir, video_name):
    """Enhanced download function with better error handling"""
    try:
        # Construct the relative path to the video file
        relative_video_path = os.path.join(settings.MEDIA_ROOT, temp_dir, video_name)

        # Verify file existence
        if not os.path.exists(relative_video_path):
            logger.error(f"Video file not found: {relative_video_path}")
            return HttpResponseNotFound("Error: Video file not found.")

        # Get file size for progress indication
        file_size = os.path.getsize(relative_video_path)

        with open(relative_video_path, 'rb') as video_file:
            response = HttpResponse(video_file.read(), content_type='video/mp4')
            response['Content-Disposition'] = f'attachment; filename="{video_name}"'
            response['Content-Length'] = file_size
            return response

    except FileNotFoundError:
        logger.error(f"Video file not found: {temp_dir}/{video_name}")
        return HttpResponseNotFound("Error: Video file not found.")
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return HttpResponseNotFound("Error: Unable to download video.")

@require_POST
@csrf_exempt
def get_processing_status(request, video_id):
    """API endpoint to get video processing status"""
    try:
        processor = VideoProcessor(video_id)
        status = processor.get_status()
        return JsonResponse(status)
    except Exception as e:
        logger.error(f"Status check error for {video_id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'progress': 0,
            'message': 'Unable to check status',
            'timestamp': datetime.now().isoformat()
        })

def validate_youtube_url(request):
    """API endpoint to validate YouTube URLs"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            url = data.get('url', '').strip()

            if not url:
                return JsonResponse({'valid': False, 'message': 'URL is required'})

            if not is_valid_youtube_url(url):
                return JsonResponse({'valid': False, 'message': 'Invalid YouTube URL format'})

            video_id = get_video_id(url)
            if not video_id:
                return JsonResponse({'valid': False, 'message': 'Could not extract video ID'})

            return JsonResponse({
                'valid': True,
                'video_id': video_id,
                'message': 'Valid YouTube URL'
            })

        except json.JSONDecodeError:
            return JsonResponse({'valid': False, 'message': 'Invalid JSON data'})
        except Exception as e:
            logger.error(f"URL validation error: {str(e)}")
            return JsonResponse({'valid': False, 'message': 'Validation error'})

    return JsonResponse({'valid': False, 'message': 'Method not allowed'})

def batch_download(request):
    """Handle batch video downloads"""
    if request.method == 'POST':
        try:
            urls = request.POST.getlist('urls[]')
            if not urls:
                return JsonResponse({'error': 'No URLs provided'})

            results = []
            for url in urls[:10]:  # Limit to 10 videos
                url = url.strip()
                if url and is_valid_youtube_url(url):
                    video_id = get_video_id(url)
                    if video_id:
                        results.append({
                            'url': url,
                            'video_id': video_id,
                            'status': 'queued'
                        })

            return JsonResponse({'results': results})

        except Exception as e:
            logger.error(f"Batch download error: {str(e)}")
            return JsonResponse({'error': 'Batch processing failed'})

    return JsonResponse({'error': 'Method not allowed'})

def undefined_page(request, undefined_path):
    """Enhanced 404 page handler"""
    logger.warning(f"404 error: {undefined_path}")
    return render(request, 'error_page.html', {
        'error_message': f"The page you are looking for ('{undefined_path}') does not exist.",
        'status_code': 404
    })

# Enhanced index view with better error handling
def index(request):
    """Enhanced index view with URL validation and error handling"""
    if request.method == 'POST':
        form = VideoForm(request.POST)
        if form.is_valid():
            youtube_link = form.cleaned_data['youtube_link'].strip()

            # Validate URL format
            if not is_valid_youtube_url(youtube_link):
                return render(request, 'index.html', {
                    'form': form,
                    'error_message': 'Please enter a valid YouTube URL'
                })

            video_id = get_video_id(youtube_link)
            if not video_id:
                return render(request, 'index.html', {
                    'form': form,
                    'error_message': 'Could not extract video ID from URL'
                })

            try:
                # Create processor for progress tracking
                processor = VideoProcessor(video_id)

                # Try to fetch video details
                video = fetch_video_details(video_id, processor)

                if video:
                    return redirect('FetchVideoApp:video_detail', video_id=video_id)
                else:
                    return render(request, 'index.html', {
                        'form': form,
                        'error_message': 'Unable to fetch video details. Please check the URL and try again.'
                    })

            except Exception as e:
                logger.error(f"Index view error for {video_id}: {str(e)}")
                return render(request, 'index.html', {
                    'form': form,
                    'error_message': 'An error occurred while processing your request. Please try again.'
                })

    else:
        form = VideoForm()

    return render(request, 'index.html', {'form': form})

