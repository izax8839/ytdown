"""
YouTube Video & Music Downloader - CLI Version
Command-line interface for downloading YouTube videos or audio.
"""

import sys
import os
import argparse
from pathlib import Path
import downloader
from downloader import YouTubeDownloader, get_media_info

DEFAULT_DOWNLOAD_DIR = str(Path.home() / "Downloads" / "YouTube_Downloads")


def print_progress(d):
    status = d.get('status')
    if status == 'downloading':
        percent = d.get('percent', 0)
        speed = d.get('speed_str', '--')
        eta = d.get('eta_str', '--')
        downloaded = d.get('downloaded_str', '--')
        total = d.get('total_str', '--')
        print(f"\r[다운로드 중] {percent:.1f}% | 속도: {speed} | 남은 시간: {eta} | 크기: {downloaded}/{total}", end="", flush=True)
    elif status == 'finished':
        print("\n[변환 중] 후처리 작업 진행 중...", flush=True)


def print_status(msg):
    print(f"\n[*] {msg}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="YouTube 동영상 및 고음질 음원 다운로더 CLI")
    parser.add_argument("--url", "-u", type=str, help="다운로드할 YouTube 링크")
    parser.add_argument("--mode", "-m", choices=["audio", "video"], default="audio", help="모드: audio (음원) 또는 video (동영상)")
    parser.add_argument("--format", "-f", type=str, default=None, help="포맷 (audio: mp3, m4a, flac, wav / video: mp4, mkv)")
    parser.add_argument("--quality", "-q", type=str, default="320", help="음질 (kbps, 기본값: 320) 또는 비디오 해상도 (best, 1080, 720 등)")
    parser.add_argument("--output", "-o", type=str, default=DEFAULT_DOWNLOAD_DIR, help="저장 디렉터리")
    parser.add_argument("--playlist", action="store_true", help="재생목록 전체 다운로드")

    args = parser.parse_args()

    url = args.url
    if not url:
        print("========================================")
        print("  YouTube 동영상 & 음원 다운로더 CLI")
        print("========================================")
        url = input("YouTube URL을 입력하세요: ").strip()
        if not url:
            print("URL이 입력되지 않아 종료합니다.")
            return

        print("\n모드를 선택하세요:")
        print("1. 음원만 다운로드 (MP3 / 320kbps)")
        print("2. 동영상 다운로드 (MP4 / 최고화질)")
        mode_choice = input("선택 (1 또는 2, 기본값 1): ").strip()
        mode = "video" if mode_choice == "2" else "audio"
    else:
        mode = args.mode

    print(f"\n[*] 영상 정보 조회 중: {url}")
    try:
        info = get_media_info(url)
        print(f"[*] 제목: {info['title']}")
        print(f"[*] 채널: {info['uploader']}")
        print(f"[*] 재생시간: {info['duration_str']}")
    except Exception as e:
        print(f"[!] 정보 조회 경고: {e}")

    options = {
        'is_playlist': args.playlist
    }

    if mode == 'audio':
        options['format'] = args.format or 'mp3'
        options['quality'] = args.quality or '320'
        options['embed_thumbnail'] = True
        options['add_metadata'] = True
        print(f"[*] 음원 다운로드 시작 (포맷: {options['format']}, 음질: {options['quality']}kbps)")
    else:
        options['format'] = args.format or 'mp4'
        options['resolution'] = args.quality or 'best'
        options['subtitles'] = False
        print(f"[*] 동영상 다운로드 시작 (포맷: {options['format']}, 해상도: {options['resolution']})")

    out_dir = os.path.abspath(args.output)
    print(f"[*] 저장 위치: {out_dir}\n")

    dl = YouTubeDownloader(
        progress_callback=print_progress,
        status_callback=print_status
    )

    try:
        dl.download(url, out_dir, mode=mode, options=options)
        print(f"\n[성공] 다운로드가 완료되었습니다! 폴더: {out_dir}")
    except Exception as e:
        print(f"\n[오류] {e}")


if __name__ == '__main__':
    main()
