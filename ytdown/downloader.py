"""
Core YouTube Downloader module using yt-dlp and FFmpeg.
Provides metadata extraction and downloading for both video and audio.
"""

import os
import re
import sys
import shutil
import yt_dlp


class DownloadCancelledException(Exception):
    """Raised when the user cancels the download."""
    pass


def format_duration(seconds):
    """Convert seconds into HH:MM:SS or MM:SS."""
    if not seconds:
        return "00:00"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_bytes(bytes_val):
    """Convert bytes to human-readable string (KB, MB, GB)."""
    if not bytes_val or bytes_val <= 0:
        return "0 MB"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"


def format_speed(speed_val):
    """Convert download speed in bytes/sec to human-readable string."""
    if not speed_val or speed_val <= 0:
        return "0 KB/s"
    return f"{format_bytes(speed_val)}/s"


def clean_filename(name):
    """Remove invalid filesystem characters from filename."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


def get_media_info(url):
    """
    Extract information from YouTube URL without downloading.
    Returns a dict with title, uploader, duration, thumbnail, formats, is_playlist, etc.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',
        'skip_download': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        if not info:
            raise ValueError("영상 정보를 가져올 수 없습니다. URL을 확인해 주세요.")
        
        # Check if playlist
        is_playlist = 'entries' in info and bool(info.get('entries'))
        playlist_count = len(info.get('entries', [])) if is_playlist else 0
        
        # For playlist, peek the first video for display
        display_info = info
        if is_playlist and playlist_count > 0:
            first_entry = info['entries'][0]
            if first_entry:
                display_info = first_entry
                
        title = display_info.get('title', '제목 없음')
        uploader = display_info.get('uploader') or display_info.get('channel') or '알 수 없음'
        duration = display_info.get('duration')
        thumbnail = display_info.get('thumbnail')
        view_count = display_info.get('view_count')
        webpage_url = display_info.get('webpage_url', url)

        # Find best available thumbnail if not present
        if not thumbnail and display_info.get('thumbnails'):
            thumbnails = display_info['thumbnails']
            thumbnail = thumbnails[-1].get('url')

        return {
            'title': title,
            'uploader': uploader,
            'duration': duration,
            'duration_str': format_duration(duration),
            'thumbnail': thumbnail,
            'view_count': view_count,
            'view_count_str': f"{view_count:,}회" if view_count else "-",
            'is_playlist': is_playlist,
            'playlist_count': playlist_count,
            'playlist_title': info.get('title') if is_playlist else None,
            'url': webpage_url,
            'raw_info': info
        }


class YouTubeDownloader:
    """Manages the download process with progress reporting and cancellation."""

    def __init__(self, cancel_check=None, progress_callback=None, status_callback=None):
        self.cancel_check = cancel_check  # Callable returning True if cancelled
        self.progress_callback = progress_callback  # Callable(dict)
        self.status_callback = status_callback  # Callable(str)
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def _check_cancellation(self):
        if self._is_cancelled or (self.cancel_check and self.cancel_check()):
            raise DownloadCancelledException("다운로드가 사용자에 의해 취소되었습니다.")

    def _hook_progress(self, d):
        self._check_cancellation()
        status = d.get('status')
        
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes') or 0
            speed = d.get('speed') or 0
            eta = d.get('eta')
            
            percent = (downloaded / total * 100) if total > 0 else 0
            
            info = {
                'status': 'downloading',
                'percent': percent,
                'downloaded_bytes': downloaded,
                'total_bytes': total,
                'downloaded_str': format_bytes(downloaded),
                'total_str': format_bytes(total),
                'speed': speed,
                'speed_str': format_speed(speed),
                'eta': eta,
                'eta_str': f"{eta}초" if eta is not None else "--",
                'filename': d.get('filename', ''),
            }
            if self.progress_callback:
                self.progress_callback(info)
                
        elif status == 'finished':
            if self.status_callback:
                self.status_callback("다운로드 완료. 후처리(변환 및 태그 삽입) 진행 중...")
            if self.progress_callback:
                self.progress_callback({
                    'status': 'finished',
                    'percent': 100,
                    'message': "변환 처리 중..."
                })

    def _hook_postprocessor(self, d):
        self._check_cancellation()
        status = d.get('status')
        pp_name = d.get('postprocessor', '')
        
        if status == 'started':
            if 'ExtractAudio' in pp_name:
                msg = "고음질 음원(오디오) 추출 및 변환 중..."
            elif 'EmbedThumbnail' in pp_name:
                msg = "앨범 커버(썸네일) 이미지 삽입 중..."
            elif 'Metadata' in pp_name:
                msg = "곡 정보 메타데이터 기록 중..."
            elif 'MoveFiles' in pp_name:
                msg = "파일 저장 중..."
            else:
                msg = f"후처리 진행 중 ({pp_name})..."
            if self.status_callback:
                self.status_callback(msg)

    def download(self, url, output_dir, mode='audio', options=None):
        """
        Download media from URL.
        
        mode: 'audio' or 'video'
        options:
          - for audio:
              format: 'mp3' | 'm4a' | 'flac' | 'wav' | 'opus' (default 'mp3')
              quality: '320' | '256' | '192' | '128' (default '320')
              embed_thumbnail: bool (default True)
              add_metadata: bool (default True)
          - for video:
              resolution: 'best' | '2160' | '1440' | '1080' | '720' | '480'
              format: 'mp4' | 'mkv' (default 'mp4')
              subtitles: bool (default False)
          - general:
              is_playlist: bool (default False)
        """
        options = options or {}
        os.makedirs(output_dir, exist_ok=True)
        self._is_cancelled = False

        outtmpl = os.path.join(output_dir, '%(title)s [%(id)s].%(ext)s')
        if options.get('is_playlist'):
            outtmpl = os.path.join(output_dir, '%(playlist_title)s', '%(playlist_index)s - %(title)s.%(ext)s')

        # Check ffmpeg availability
        ffmpeg_location = shutil.which('ffmpeg')
        if not ffmpeg_location:
            winget_pkg = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
            if os.path.exists(winget_pkg):
                for root, _, files in os.walk(winget_pkg):
                    if 'ffmpeg.exe' in [f.lower() for f in files]:
                        ffmpeg_location = os.path.join(root, 'ffmpeg.exe')
                        break

        ydl_opts = {
            'outtmpl': outtmpl,
            'progress_hooks': [self._hook_progress],
            'postprocessor_hooks': [self._hook_postprocessor],
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'nocheckcertificate': True,
        }

        if ffmpeg_location:
            ydl_opts['ffmpeg_location'] = os.path.dirname(ffmpeg_location)

        if mode == 'audio':
            audio_format = options.get('format', 'mp3').lower()
            audio_quality = str(options.get('quality', '320'))
            embed_thumb = options.get('embed_thumbnail', True)
            add_meta = options.get('add_metadata', True)

            ydl_opts['format'] = 'bestaudio/best'
            postprocessors = [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': audio_format,
                    'preferredquality': audio_quality,
                }
            ]

            if add_meta:
                postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})

            if embed_thumb and audio_format in ['mp3', 'm4a', 'flac']:
                ydl_opts['writethumbnail'] = True
                postprocessors.append({'key': 'EmbedThumbnail'})

            ydl_opts['postprocessors'] = postprocessors

        else:  # video mode
            resolution = options.get('resolution', 'best')
            video_format = options.get('format', 'mp4').lower()
            add_subs = options.get('subtitles', False)

            if resolution == 'best':
                ydl_opts['format'] = f'bestvideo[ext={video_format}]+bestaudio/bestvideo+bestaudio/best'
            else:
                ydl_opts['format'] = f'bestvideo[height<={resolution}][ext={video_format}]+bestaudio/bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]/best'

            ydl_opts['merge_output_format'] = video_format
            postprocessors = [
                {'key': 'FFmpegMetadata', 'add_metadata': True}
            ]

            if add_subs:
                ydl_opts['writesubtitles'] = True
                ydl_opts['writeautomaticsub'] = True
                ydl_opts['subtitleslangs'] = ['ko', 'en']
                postprocessors.append({'key': 'FFmpegEmbedSubtitle'})

            ydl_opts['postprocessors'] = postprocessors

        if self.status_callback:
            self.status_callback("다운로드 준비 중...")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self._check_cancellation()
                ydl.download([url])
                self._check_cancellation()
        except DownloadCancelledException:
            raise
        except Exception as e:
            if self._is_cancelled:
                raise DownloadCancelledException("다운로드가 사용자에 의해 취소되었습니다.")
            raise RuntimeError(f"다운로드 중 오류가 발생했습니다: {str(e)}")

        if self.status_callback:
            self.status_callback("다운로드가 성공적으로 완료되었습니다!")
