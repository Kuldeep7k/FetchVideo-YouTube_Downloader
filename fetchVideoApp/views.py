import os
import re
import shlex
import subprocess
from django.http import HttpResponse, HttpResponseNotFound
from django import forms
from django.conf import settings
from django.shortcuts import render, redirect
from pytubefix import YouTube
from .forms import VideoForm
from .models import Video
from datetime import datetime

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

def seconds_to_hhmmss(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def get_video_id(youtube_link):
    video_id = None
    video_id_regex = r"(?:youtu\.be/|watch\?v=|embed/|playlist\?list=|shorts/)([^&?/\s]+)"

    match = re.search(video_id_regex, youtube_link)

    if match:
        video_id = match.group(1)

    return video_id


def remove_emojis(text):
    # Remove emoji characters from the given text
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F700-\U0001F77F"  # alchemical symbols
                               u"\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
                               u"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
                               u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
                               u"\U0001FA00-\U0001FA6F"  # Chess Symbols
                               u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
                               u"\U00002702-\U000027B0"  # Dingbats
                               u"\U000024C2-\U0001F251" 
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)


def fetch_video_details(video_id):
    try:
        video = Video.objects.get(video_id=video_id)
    except Video.DoesNotExist:
        youtube_link = f'https://www.youtube.com/watch?v={video_id}'
        try:
            yt = YouTube(youtube_link)
            title = remove_emojis(yt.title)
            video = Video(
                title=title,
                url=youtube_link,
                video_id=video_id,
                channel_title=yt.author,
                duration=str(seconds_to_hhmmss(yt.length)),
                thumbnail_url=yt.thumbnail_url,
            )
            video.save()

        except Exception as e:
            print(f"Error fetching video details: {e}")
            return None

    return video


class VideoDownloadForm(forms.Form):
    video_quality = forms.CharField(widget=forms.HiddenInput)
    audio_quality = forms.CharField(widget=forms.HiddenInput)


def extract_numeric_bitrate(abr):
    match = re.search(r'\d+', abr)
    return int(match.group()) if match else 0


def video_detail(request, video_id):
    try:
        # Use the fetched YouTube link
        youtube_link = f'https://www.youtube.com/watch?v={video_id}'
        video = fetch_video_details(video_id)

        # Increment views count if the video is found
        if video:
            video.views += 1
            video.save()

        # Get all available video and audio qualities from pytube
        yt = YouTube(youtube_link)

        #  Get all video streams and sort them by resolution in descending order
        video_streams = yt.streams.filter(type="video").order_by('resolution')
        video_streams = list(reversed(video_streams))

        # Initialize lists for video qualities
        av01_qualities = []
        vp9_qualities = []

        for stream in video_streams:
            resolution = stream.resolution
            codecs = stream.codecs

            # Collect AV1 streams
            if 'av01' in codecs:
                av01_qualities.append({
                    'format': resolution,
                    'fps': stream.fps,
                    'url': stream.url,
                    'mime_type': stream.mime_type,
                    'codecs': codecs
                })
            # Collect VP9 streams
            elif 'vp9' in codecs:
                vp9_qualities.append({
                    'format': resolution,
                    'fps': stream.fps,
                    'url': stream.url,
                    'mime_type': stream.mime_type,
                    'codecs': codecs
                })

        # Use AV1 qualities if available, otherwise fall back to VP9 qualities
        video_qualities = av01_qualities if av01_qualities else vp9_qualities

        # Get all available audio streams and sort them by audio bitrate in descending order
        audio_streams = yt.streams.filter(type="audio")
        audio_qualities = [
            {
                'itag': stream.itag,
                'abr': stream.abr,
                'audio_codec': stream.audio_codec,
                'mime_type': stream.mime_type,
                'url': stream.url,
            }
            for stream in audio_streams
        ]

        # Sort audio_qualities in descending order based on abr
        audio_qualities = sorted(audio_qualities, key=lambda x: extract_numeric_bitrate(x['abr']), reverse=True)

        # Use a dictionary to keep track of the latest item for each 'itag'
        unique_audio_qualities = {}
        for audio_quality in audio_qualities:
            itag = audio_quality['itag']
            unique_audio_qualities[itag] = audio_quality

        # Get the values (filtered audio_qualities) from the dictionary
        filtered_audio_qualities = list(unique_audio_qualities.values())


        # Prepare video_audio_qualities list containing tuples of (video_quality, filtered_audio_qualities)
        video_audio_qualities = []
        for video_quality, filtered_audio_qualities in zip(video_qualities, filtered_audio_qualities):
            video_audio_qualities.append((video_quality, filtered_audio_qualities))

        # If the number of video qualities is greater than filtered_audio_qualities, add the remaining video qualities separately
        if len(video_qualities) > len(filtered_audio_qualities):
            remaining_video_qualities = video_qualities[len(filtered_audio_qualities):]
            for video_quality in remaining_video_qualities:
                video_audio_qualities.append((video_quality, None))

        # If the number of filtered_audio_qualities is greater than video qualities, add the remaining filtered_audio_qualities separately
        elif len(filtered_audio_qualities) > len(video_qualities):
            remaining_audio_qualities = filtered_audio_qualities[len(video_qualities):]
            for filtered_audio_qualities in remaining_audio_qualities:
                video_audio_qualities.append((None, filtered_audio_qualities))

        # Handle video download form submission
        if request.method == 'POST':
            form = VideoDownloadForm(request.POST)
            if form.is_valid():
                video_quality = form.cleaned_data['video_quality']

                # Call the download_video_with_best_audio view with the selected qualities
                video_name, temp_dir = download_video_with_best_audio(request, video_id, video_quality)

                # Check if the download_video_with_best_audio function returns a path
                if video_name:
                # Use the path to serve the merged video for download
                    return render(request, 'download.html', {'video_name': video_name, 'temp_dir': temp_dir})
        else:
            # If it's a GET request, create an empty form
            form = VideoDownloadForm()

    except Exception as e:
        error_message = str(e)
        return render(request, 'error_page.html', {'error_message': error_message})

    return render(request, 'video_details.html', {'video': video, 'video_audio_qualities': video_audio_qualities, 'form': form})


# Function to sanitize the video title
def sanitize_video_title(title):
    # Remove invalid symbols and replace spaces with underscores
    sanitized_title = re.sub(r'[^\w\s.-]', '', title)
    sanitized_title = sanitized_title.replace(' ', '_')
    return sanitized_title


def download_video_with_best_audio(request, video_id, video_quality):
    video = fetch_video_details(video_id)

    if video:
        try:
            # Create a temporary directory with the current date and time as the name
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            temp_dir = os.path.join(settings.MEDIA_ROOT, f"temp_{timestamp}")
            os.makedirs(temp_dir, exist_ok=True)

            youtube_link = f'https://www.youtube.com/watch?v={video.video_id}'
            yt = YouTube(youtube_link)

            # Try to get the video stream with the selected quality
            video_stream = yt.streams.filter(type="video", resolution=video_quality).first()

            # Get available audio streams
            audio_streams = yt.streams.filter(type="audio")

            # Filter audio streams with itag 251
            filtered_audio_streams = [stream for stream in audio_streams if stream.itag == 251]

            # Initialize audio_path as None
            audio_path = None

            # Check if there are any streams with itag 251
            if filtered_audio_streams:
                # Get the last audio stream with itag 251
                audio_stream = filtered_audio_streams[-1]

                # Download the audio stream
                audio_path = os.path.join(temp_dir, f"{video.video_id}_audio.{audio_stream.subtype}")
                audio_stream.download(output_path=temp_dir, filename=os.path.basename(audio_path))
            else:
                error_message = "No audio stream with itag 251 found."
                return render(request, 'error_page.html', {'error_message': error_message}, status=500)

            # Handle cases where no matching audio stream is found
            if not audio_path:
                error_message = "No audio stream with the specified URL was found."
                return render(request, 'error_page.html', {'error_message': error_message}, status=500)

            # Check if the audio stream was found
            if audio_path is None:
                error_message = "Selected audio stream not found."
                return render(request, 'error_page.html', {'error_message': error_message}, status=500)

            audio_format = os.path.splitext(audio_path)[1].lstrip('.')

            if video_stream:
                # Download video in the temporary directory
                video_format = video_stream.subtype
                fps = int(video_stream.fps) if video_stream.fps else 30  # Default to 30 fps if fps is not available
                video_path = os.path.join(temp_dir, f"{video.video_id}.{video_format}")
                video_stream.download(output_path=temp_dir, filename=f"{video.video_id}.{video_format}")

                # Check if video and audio files were downloaded successfully
                if not os.path.exists(video_path) or not os.path.exists(audio_path):
                    error_message = "Error downloading video or audio."
                    return render(request, 'error_page.html', {'error_message': error_message}, status=500)

                # Convert audio to M4A format if it's in MP4 or WebM format
                if audio_format in ['mp4', 'webm']:
                    m4a_audio_path = os.path.join(temp_dir, f"{video.video_id}_audio.m4a")
                    
                    if audio_format == 'mp4':
                        # For MP4 audio, simply copy the audio stream without conversion
                        cmd = f'"{FFmpeg_PATH}" -i "{audio_path}" -vn -c:a copy "{m4a_audio_path}"'
                    elif audio_format == 'webm':
                        # For WebM audio, convert it to M4A without changing the quality
                        cmd = f'"{FFmpeg_PATH}" -i "{audio_path}" -vn -c:a aac -strict -2 "{m4a_audio_path}"'

                    process = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = process.communicate()

                    # Check if the ffmpeg command executed successfully
                    if process.returncode != 0:
                        error_message = f"Error converting audio to M4A: {stderr.decode('utf-8')}"
                        return render(request, 'error_page.html', {'error_message': error_message}, status=500)

                    # Remove the old audio file
                    try:
                        print(f"Removing old audio file: {audio_path}")
                        os.remove(audio_path)
                    except Exception as e:
                        error_message = f"Error removing old audio file: {str(e)}"
                        return render(request, 'error_page.html', {'error_message': error_message}, status=500)

                    # Replace the audio path with the M4A file
                    audio_path = m4a_audio_path

                # Merge video and audio using ffmpeg, output as WebM
                merged_filename = f"{sanitize_video_title(video.title)}_-_{video_quality}_{fps}fps.mp4"

                merged_path = os.path.join(temp_dir, merged_filename)
                cmd = f'"{FFmpeg_PATH}" -i "{video_path}" -i "{audio_path}" -c:v copy -c:a copy "{merged_path}"'
                print(f"\nMerging video and audio: {cmd}\n")

                process = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()

                # Check if the ffmpeg command executed successfully
                if process.returncode != 0:
                    error_message = f"Error merging video and audio: {stderr.decode('utf-8')}"
                    return render(request, 'error_page.html', {'error_message': error_message}, status=500)

                # Check if the merged file exists using merged_path
                if not os.path.exists(merged_path):
                    error_message = "Error creating merged video."
                    return render(request, 'error_page.html', {'error_message': error_message}, status=500)
                
                 # Determine the video format using the file extension
                _, file_extension = os.path.splitext(merged_path)
                file_extension = file_extension.lstrip('.').lower()

                # If the merged video is in WebM format, convert it to MP4
                if file_extension == 'webm':
                    new_filename = merged_filename[:-3]
                    mp4_merged_path = os.path.join(temp_dir, new_filename)
                    cmd_convert_to_mp4 = f'"{FFmpeg_PATH}" -i "{merged_path}" -c:v copy -c:a copy "{mp4_merged_path}.mp4"'
                    print(f"\nConverting WebM to MP4: {cmd_convert_to_mp4}\n")

                    process_convert_to_mp4 = subprocess.Popen(shlex.split(cmd_convert_to_mp4), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout_convert_to_mp4, stderr_convert_to_mp4 = process_convert_to_mp4.communicate()

                    # Check if the conversion to MP4 executed successfully
                    if process_convert_to_mp4.returncode != 0:
                        error_message = f"Error converting WebM to MP4: {stderr_convert_to_mp4.decode('utf-8')}"
                        return render(request, 'error_page.html', {'error_message': error_message}, status=500)

                    # Remove the original WebM file after converting to MP4
                    try:
                        print(f"Removing WebM file: {merged_path}")
                        os.remove(merged_path)
                    except Exception as e:
                        print(f"Error removing WebM file: {str(e)}")
                        error_message = "Error removing WebM file."
                        return render(request, 'error_page.html', {'error_message': error_message}, status=500)

                    # Update the merged path to the MP4 file
                    merged_filename = mp4_merged_path

                # Clean up video_path and audio_path before redirecting
                try:
                    print(f"Removing video file: {video_path}")
                    os.remove(video_path)
                except Exception as e:
                    print(f"Error removing video file: {str(e)}")
                    error_message = "Error removing video file."
                    return render(request, 'error_page.html', {'error_message': error_message}, status=500)

                try:
                    print(f"Removing audio file: {audio_path}")
                    os.remove(audio_path)
                except Exception as e:
                    print(f"Error removing audio file: {str(e)}\n")
                    error_message = "Error removing audio file."
                    return render(request, 'error_page.html', {'error_message': error_message}, status=500)



                relative_temp_dir = os.path.relpath(temp_dir, settings.MEDIA_ROOT)

                return merged_filename, relative_temp_dir

        except Exception as e:
            error_message = f"Error: {str(e)}"
            return render(request, 'error_page.html', {'error_message': error_message}, status=500)

        return redirect('FetchVideoApp:video_detail', video_id=video_id)


def download(request, temp_dir, video_name):
    try:
        # Construct the relative path to the video file
        relative_video_path = os.path.join('media', temp_dir, video_name.replace('\\', '/'))

        # Verify file existence
        if not os.path.exists(relative_video_path):
            raise FileNotFoundError("Merged video file not found.")
        
        with open(relative_video_path, 'rb') as video_file:
            response = HttpResponse(video_file.read(), content_type='video/mp4')
            response['Content-Disposition'] = f'attachment; filename="{video_name}"'
            return response

    except FileNotFoundError:
        return HttpResponseNotFound("Error: Merged video file not found.")

def undefined_page(request, undefined_path):
    error_message = f"The page you are looking for ('{undefined_path}') does not exist."
    return render(request, 'error_page.html', {'error_message': error_message})

