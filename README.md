# FetchVideo - YouTube Video & Shorts Downloader

A powerful, user-friendly Django web application for downloading YouTube videos and shorts with advanced session management and caching capabilities.

## 🚀 Features

### Core Functionality

- ✅ **YouTube Video Download**: Download videos in multiple quality formats (1080p, 720p, 480p, etc.)
- ✅ **YouTube Shorts Support**: Full support for downloading YouTube Shorts
- ✅ **Audio Extraction**: Extract and download audio-only versions (MP3, M4A)
- ✅ **Multiple Formats**: Support for MP4, WebM, and other video formats
- ✅ **Batch Processing**: Process multiple videos efficiently

### Advanced Features

- 🔄 **Session-Based Management**: Each user gets isolated temporary directories
- 💾 **Smart Caching**: Processed videos are cached to avoid reprocessing
- 🧹 **Automatic Cleanup**: Expired sessions and cache are cleaned automatically
- 📊 **Progress Tracking**: Real-time download progress with WebSocket-like updates
- 🎯 **Quality Selection**: Choose from available video and audio quality combinations
- 🛡️ **Error Handling**: Robust error handling with user-friendly messages

### User Experience

- 🎨 **Modern UI**: Bootstrap 5 responsive design with dark theme
- 📱 **Mobile Friendly**: Fully responsive design for all devices
- ⚡ **Fast Processing**: Optimized for speed with background processing
- 🔍 **URL Validation**: Real-time YouTube URL validation
- 📋 **Copy-Friendly**: Easy URL input with validation feedback

## 📋 Requirements

- Python 3.8+
- Django 5.2+
- FFmpeg (for video processing)
- pytubefix (YouTube API library)
- Bootstrap 5.3+
- SQLite (default) or PostgreSQL/MySQL

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Kuldeep7k/FetchVideo-YouTube_Video_and_Shorts_Downloader.git
cd FetchVideo-YouTube_Video_and_Shorts_Downloader
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install FFmpeg

**Windows:**

- Download from [FFmpeg official site](https://ffmpeg.org/download.html)
- Add to system PATH or place in project directory

**Linux:**

```bash
sudo apt update && sudo apt install ffmpeg
```

**Mac:**

```bash
brew install ffmpeg
```

### 5. Database Setup

```bash
python manage.py migrate
```

### 6. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

## 🚀 Usage

### Start the Server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` in your browser.

### Basic Usage

1. **Enter YouTube URL**: Paste any YouTube video or shorts URL
2. **Validate**: The app automatically validates the URL
3. **Choose Quality**: Select from available video quality options
4. **Download**: Click download and monitor progress in real-time

### Supported URL Formats

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/shorts/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`

## ⚙️ Configuration

### Session Management

```python
# settings.py
SESSION_COOKIE_AGE = 3600  # 1 hour sessions
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Clean on browser close
```

### Caching Configuration

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': 'cache',
        'TIMEOUT': 3600,  # 1 hour cache
        'OPTIONS': {'MAX_ENTRIES': 1000}
    }
}
```

### Media Settings

```python
# settings.py
MEDIA_ROOT = 'media'  # Temporary files location
MEDIA_URL = '/media/'  # Media URL prefix
```

## 🧹 Maintenance & Cleanup

### Automatic Cleanup

The application includes multiple cleanup mechanisms:

1. **Session-Based**: Temp directories are cleaned when sessions expire
2. **Periodic**: Background cleanup runs on 5% of requests
3. **Cache Expiration**: Cached videos expire after 1 hour

### Manual Cleanup Options

#### Option 1: Management Command

```bash
# Clean everything
python manage.py cleanup_sessions

# Clean only cache
python manage.py cleanup_sessions --cache-only

# Clean only sessions
python manage.py cleanup_sessions --sessions-only

# Dry run (preview cleanup)
python manage.py cleanup_sessions --dry-run
```

#### Option 2: Standalone Scheduler

```bash
# Run once
python cleanup_scheduler.py --once

# Run continuously (every 30 minutes)
python cleanup_scheduler.py

# Custom interval (15 minutes)
python cleanup_scheduler.py --interval 15
```

#### Option 3: Batch Scripts

```bash
# Windows
run_cleanup.bat

# Linux/Mac
./run_cleanup.sh
```

### Scheduled Cleanup (Recommended)

**Windows Task Scheduler:**

1. Search for "Task Scheduler"
2. Create new task → Daily at 2:00 AM
3. Action: `cmd.exe /c "D:\Path\To\run_cleanup.bat"`

**Linux/Mac Cron:**

```bash
crontab -e
# Add: */30 * * * * /path/to/project/run_cleanup.sh
```

## 📁 Project Structure

```
FetchVideo-YouTube_Downloader/
├── fetchVideoApp/                 # Main Django app
│   ├── management/commands/       # Custom management commands
│   │   └── cleanup_sessions.py    # Cleanup management command
│   ├── static/                    # Static files (CSS, JS, images)
│   ├── templates/                 # HTML templates
│   ├── session_manager.py         # Session and cache management
│   ├── signals.py                 # Django signals for cleanup
│   ├── views.py                   # View functions
│   └── models.py                  # Database models
├── fetchVideoProject/             # Django project settings
├── media/                         # Temporary files and cache
├── cache/                         # Django cache files
├── cleanup_scheduler.py           # Standalone cleanup scheduler
├── run_cleanup.bat                # Windows cleanup script
├── run_cleanup.sh                 # Linux/Mac cleanup script
├── requirements.txt               # Python dependencies
├── manage.py                      # Django management script
└── README.md                      # This file
```

## 🔧 Technical Details

### Session Management

- **Isolation**: Each user session gets unique temp directory
- **Automatic Cleanup**: Expired sessions trigger directory cleanup
- **Storage**: Session data stored in database for reliability

### Video Caching

- **Smart Caching**: Avoids reprocessing same video/quality combinations
- **Expiration**: Cache entries expire after 1 hour
- **File-Based**: Uses Django's file-based cache backend

### Processing Pipeline

1. **URL Validation**: Regex-based YouTube URL validation
2. **Video Analysis**: Extract available streams and qualities
3. **Quality Selection**: Present user with quality options
4. **Download & Process**: Download video and audio streams
5. **Merging**: FFmpeg merges video and audio
6. **Caching**: Store result for future requests
7. **Cleanup**: Remove temporary files

### Error Handling

- **Network Issues**: Retry logic for YouTube API calls
- **Invalid URLs**: Real-time validation feedback
- **Processing Errors**: Detailed error messages with recovery options
- **File System**: Robust file operation error handling

## 🐛 Troubleshooting

### Common Issues

**FFmpeg Not Found:**

```bash
# Check FFmpeg installation
ffmpeg -version

# Add to PATH or update settings.py
FFMPEG_PATH = r"C:\path\to\ffmpeg.exe"
```

**Permission Errors:**

```bash
# Ensure write permissions on media/ directory
chmod 755 media/
```

**Cache Issues:**

```bash
# Clear cache manually
python manage.py cleanup_sessions --cache-only
```

**Session Issues:**

```bash
# Clear expired sessions
python manage.py cleanup_sessions --sessions-only
```

### Debug Mode

Enable debug logging in `settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        'fetchVideoApp': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

## 📄 API Endpoints

- `GET /` - Home page with URL input
- `POST /` - Process YouTube URL
- `GET /video/<video_id>/` - Video details and quality selection
- `POST /video/<video_id>/download/<quality>/` - Download video
- `GET /media/<path>/<filename>/` - Serve downloaded files
- `GET /api/status/<video_id>/` - Get processing status
- `POST /api/validate-url/` - Validate YouTube URL
- `POST /api/batch-download/` - Batch download (future feature)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Commit your changes: `git commit -am 'Add feature'`
5. Push to the branch: `git push origin feature-name`
6. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This application is for educational and personal use only. Please respect YouTube's Terms of Service and copyright laws. The developers are not responsible for any misuse of this software.

## 🙏 Acknowledgments

- [pytubefix](https://github.com/pytubefix/pytubefix) - YouTube API library
- [Django](https://www.djangoproject.com/) - Web framework
- [Bootstrap](https://getbootstrap.com/) - UI framework
- [FFmpeg](https://ffmpeg.org/) - Video processing

---

**Made with ❤️ for the YouTube downloading community**
