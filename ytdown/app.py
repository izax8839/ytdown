"""
YouTube Video & Music Downloader (유튜브 영상 및 음원 다운로더)
Modern PyQt6 Desktop Application
"""

import os
import sys
import shutil
import urllib.request
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QProgressBar, QFileDialog, QFrame, QScrollArea, QMessageBox,
    QRadioButton, QButtonGroup, QSizePolicy, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QPixmap, QImage, QIcon, QColor, QPalette, QCursor

import downloader
from downloader import YouTubeDownloader, get_media_info, DownloadCancelledException


# Default Download Directory: User's Downloads/YouTube_Downloads
DEFAULT_DOWNLOAD_DIR = str(Path.home() / "Downloads" / "YouTube_Downloads")


class InfoFetchThread(QThread):
    """Background thread to fetch YouTube metadata without freezing the UI."""
    info_fetched = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            info = get_media_info(self.url)
            self.info_fetched.emit(info)
        except Exception as e:
            self.error_occurred.emit(str(e))


class ThumbnailFetchThread(QThread):
    """Background thread to download thumbnail image."""
    thumbnail_loaded = pyqtSignal(bytes)

    def __init__(self, thumbnail_url):
        super().__init__()
        self.thumbnail_url = thumbnail_url

    def run(self):
        try:
            req = urllib.request.Request(
                self.thumbnail_url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()
                self.thumbnail_loaded.emit(data)
        except Exception:
            pass


class DownloadThread(QThread):
    """Background thread to download video/audio with real-time progress."""
    progress_updated = pyqtSignal(dict)
    status_updated = pyqtSignal(str)
    download_finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, url, output_dir, mode, options):
        super().__init__()
        self.url = url
        self.output_dir = output_dir
        self.mode = mode
        self.options = options
        self.downloader = None

    def run(self):
        try:
            self.downloader = YouTubeDownloader(
                cancel_check=lambda: self.isInterruptionRequested(),
                progress_callback=lambda d: self.progress_updated.emit(d),
                status_callback=lambda s: self.status_updated.emit(s)
            )
            self.downloader.download(
                url=self.url,
                output_dir=self.output_dir,
                mode=self.mode,
                options=self.options
            )
            self.download_finished.emit(self.output_dir)
        except DownloadCancelledException as e:
            self.status_updated.emit("사용자에 의해 다운로드가 취소되었습니다.")
            self.error_occurred.emit("CANCELLED")
        except Exception as e:
            self.error_occurred.emit(str(e))

    def cancel(self):
        self.requestInterruption()
        if self.downloader:
            self.downloader.cancel()


DARK_STYLESHEET = """
QMainWindow {
    background-color: #121417;
}

QWidget {
    color: #E2E8F0;
    font-family: 'Pretendard', 'Malgun Gothic', 'Segoe UI', sans-serif;
    font-size: 13px;
}

/* Scroll area */
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    background: #1A1D23;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #3B4252;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #4C566A;
}

/* Card Frame */
QFrame.card {
    background-color: #1A1D24;
    border: 1px solid #2B303C;
    border-radius: 12px;
}

/* Header */
QLabel#headerTitle {
    font-size: 20px;
    font-weight: 700;
    color: #FFFFFF;
}
QLabel#headerSubtitle {
    font-size: 12px;
    color: #8C9BAB;
}

/* Section Title */
QLabel.sectionTitle {
    font-size: 14px;
    font-weight: 600;
    color: #94A3B8;
}

/* LineEdit */
QLineEdit {
    background-color: #0F1115;
    border: 1px solid #333A48;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    color: #FFFFFF;
    selection-background-color: #E11D48;
}
QLineEdit:focus {
    border: 1px solid #E11D48;
    background-color: #13171F;
}

/* PushButtons */
QPushButton {
    background-color: #272C38;
    border: 1px solid #3A4254;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
    color: #E2E8F0;
}
QPushButton:hover {
    background-color: #343B4B;
    border-color: #4C566A;
}
QPushButton:pressed {
    background-color: #1F232D;
}
QPushButton:disabled {
    background-color: #181B22;
    border-color: #252A35;
    color: #555E6D;
}

/* Primary Action Button (Red YouTube Style) */
QPushButton#primaryBtn {
    background-color: #E11D48;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 14px;
    font-weight: 700;
    color: #FFFFFF;
}
QPushButton#primaryBtn:hover {
    background-color: #F43F5E;
}
QPushButton#primaryBtn:pressed {
    background-color: #BE123C;
}
QPushButton#primaryBtn:disabled {
    background-color: #3D2228;
    color: #7A535B;
}

/* Secondary Button */
QPushButton#cancelBtn {
    background-color: #2B303C;
    border: 1px solid #434B5C;
    border-radius: 8px;
    padding: 12px 20px;
    font-size: 13px;
    font-weight: 600;
    color: #CBD5E1;
}
QPushButton#cancelBtn:hover {
    background-color: #3E4657;
    color: #FFFFFF;
}

/* Mode Selection Segment Buttons */
QPushButton.modeBtn {
    background-color: #1E222B;
    border: 1px solid #333A48;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
    color: #94A3B8;
}
QPushButton.modeBtn:checked {
    background-color: #E11D48;
    border: 1px solid #E11D48;
    color: #FFFFFF;
}

/* ComboBox */
QComboBox {
    background-color: #0F1115;
    border: 1px solid #333A48;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
    color: #FFFFFF;
    min-height: 24px;
}
QComboBox:hover {
    border-color: #4B5568;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #1A1D24;
    border: 1px solid #333A48;
    selection-background-color: #E11D48;
    color: #FFFFFF;
    outline: none;
    border-radius: 4px;
    padding: 4px;
}

/* CheckBox */
QCheckBox {
    spacing: 8px;
    color: #CBD5E1;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #434B5C;
    border-radius: 4px;
    background-color: #0F1115;
}
QCheckBox::indicator:hover {
    border-color: #E11D48;
}
QCheckBox::indicator:checked {
    background-color: #E11D48;
    border-color: #E11D48;
    image: none;
}

/* ProgressBar */
QProgressBar {
    background-color: #0F1115;
    border: 1px solid #2B303C;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    font-size: 10px;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #FB7185);
    border-radius: 5px;
}

/* Badges & Status */
QLabel#statusLabel {
    color: #94A3B8;
    font-size: 12px;
}
QLabel#badgeAudio {
    background-color: #1E3A8A;
    color: #93C5FD;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#badgeVideo {
    background-color: #831843;
    color: #FBCFE8;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
}
"""


class YouTubeDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube 미디어 다운로더 (동영상 & 고음질 음원)")
        self.resize(800, 780)
        self.setMinimumSize(700, 680)

        # Set Window Icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Download destination
        self.output_dir = DEFAULT_DOWNLOAD_DIR
        os.makedirs(self.output_dir, exist_ok=True)

        # State
        self.current_mode = 'audio'  # 'audio' or 'video'
        self.fetched_info = None
        self.fetch_thread = None
        self.thumb_thread = None
        self.download_thread = None

        self.setStyleSheet(DARK_STYLESHEET)
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # 1. Header
        header_layout = QHBoxLayout()
        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(2)

        title_lbl = QLabel("🎬 YouTube 미디어 다운로더")
        title_lbl.setObjectName("headerTitle")
        subtitle_lbl = QLabel("YouTube 영상 및 음악(MP3/M4A/FLAC) 고화질·고음질 다운로드 프로그램")
        subtitle_lbl.setObjectName("headerSubtitle")
        header_text_layout.addWidget(title_lbl)
        header_text_layout.addWidget(subtitle_lbl)

        header_layout.addLayout(header_text_layout)
        header_layout.addStretch()

        # Mode Badge
        self.mode_badge = QLabel("🎵 음원 다운로드 모드")
        self.mode_badge.setObjectName("badgeAudio")
        header_layout.addWidget(self.mode_badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        main_layout.addLayout(header_layout)

        # 2. Mode Toggle Segment
        mode_frame = QFrame()
        mode_frame.setObjectName("card")
        mode_frame.setProperty("class", "card")
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(12, 10, 12, 10)
        mode_layout.setSpacing(12)

        mode_lbl = QLabel("다운로드 모드:")
        mode_lbl.setStyleSheet("font-weight: 600; color: #CBD5E1;")
        mode_layout.addWidget(mode_lbl)

        self.btn_mode_audio = QPushButton("🎵 음원만 다운로드 (MP3 / FLAC / M4A)")
        self.btn_mode_audio.setCheckable(True)
        self.btn_mode_audio.setChecked(True)
        self.btn_mode_audio.setProperty("class", "modeBtn")
        self.btn_mode_audio.clicked.connect(lambda: self.switch_mode('audio'))

        self.btn_mode_video = QPushButton("🎬 동영상 다운로드 (최고화질 / 1080p / 4K)")
        self.btn_mode_video.setCheckable(True)
        self.btn_mode_video.setChecked(False)
        self.btn_mode_video.setProperty("class", "modeBtn")
        self.btn_mode_video.clicked.connect(lambda: self.switch_mode('video'))

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.btn_mode_audio)
        self.mode_group.addButton(self.btn_mode_video)

        mode_layout.addWidget(self.btn_mode_audio, 1)
        mode_layout.addWidget(self.btn_mode_video, 1)
        main_layout.addWidget(mode_frame)

        # 3. URL Input Card
        url_frame = QFrame()
        url_frame.setObjectName("card")
        url_frame.setProperty("class", "card")
        url_layout = QVBoxLayout(url_frame)
        url_layout.setContentsMargins(16, 14, 16, 14)
        url_layout.setSpacing(10)

        url_header_layout = QHBoxLayout()
        url_lbl = QLabel("YouTube 링크(URL)")
        url_lbl.setStyleSheet("font-weight: 600; color: #CBD5E1;")
        url_header_layout.addWidget(url_lbl)
        url_header_layout.addStretch()

        self.btn_paste = QPushButton("📋 클립보드 붙여넣기")
        self.btn_paste.clicked.connect(self.paste_from_clipboard)
        url_header_layout.addWidget(self.btn_paste)
        url_layout.addLayout(url_header_layout)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=... 또는 Shorts 링크를 입력하세요")
        self.url_input.returnPressed.connect(self.fetch_info)
        self.url_input.textChanged.connect(self.on_url_changed)
        input_row.addWidget(self.url_input, 1)

        self.btn_fetch = QPushButton("🔍 정보 확인")
        self.btn_fetch.clicked.connect(self.fetch_info)
        input_row.addWidget(self.btn_fetch)
        url_layout.addLayout(input_row)

        main_layout.addWidget(url_frame)

        # 4. Media Info Preview Card (Thumbnail, Title, Duration, etc.)
        self.info_frame = QFrame()
        self.info_frame.setObjectName("card")
        self.info_frame.setProperty("class", "card")
        self.info_frame.setVisible(False)  # Hidden initially until info is fetched
        info_layout = QHBoxLayout(self.info_frame)
        info_layout.setContentsMargins(16, 14, 16, 14)
        info_layout.setSpacing(16)

        # Thumbnail Label
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(160, 90)
        self.thumb_label.setStyleSheet("background-color: #0F1115; border-radius: 8px; border: 1px solid #333A48;")
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setText("썸네일 로딩 중")
        info_layout.addWidget(self.thumb_label)

        # Details Layout
        details_layout = QVBoxLayout()
        details_layout.setSpacing(6)

        self.info_title = QLabel("영상 제목")
        self.info_title.setWordWrap(True)
        self.info_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        details_layout.addWidget(self.info_title)

        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(16)
        self.info_channel = QLabel("채널: -")
        self.info_channel.setStyleSheet("color: #94A3B8; font-size: 12px;")
        self.info_duration = QLabel("재생시간: -")
        self.info_duration.setStyleSheet("color: #94A3B8; font-size: 12px;")
        self.info_views = QLabel("조회수: -")
        self.info_views.setStyleSheet("color: #94A3B8; font-size: 12px;")
        meta_layout.addWidget(self.info_channel)
        meta_layout.addWidget(self.info_duration)
        meta_layout.addWidget(self.info_views)
        meta_layout.addStretch()
        details_layout.addLayout(meta_layout)

        # Playlist option if detected
        self.playlist_container = QWidget()
        playlist_layout = QHBoxLayout(self.playlist_container)
        playlist_layout.setContentsMargins(0, 4, 0, 0)
        self.playlist_label = QLabel("📋 재생목록 감지됨")
        self.playlist_label.setStyleSheet("color: #F59E0B; font-weight: 600; font-size: 12px;")
        self.check_download_playlist = QCheckBox("재생목록 전체 다운로드")
        self.check_download_playlist.setChecked(False)
        playlist_layout.addWidget(self.playlist_label)
        playlist_layout.addWidget(self.check_download_playlist)
        playlist_layout.addStretch()
        self.playlist_container.setVisible(False)
        details_layout.addWidget(self.playlist_container)

        info_layout.addLayout(details_layout, 1)
        main_layout.addWidget(self.info_frame)

        # 5. Options Card (Audio / Video Settings)
        self.options_frame = QFrame()
        self.options_frame.setObjectName("card")
        self.options_frame.setProperty("class", "card")
        options_layout = QVBoxLayout(self.options_frame)
        options_layout.setContentsMargins(16, 14, 16, 14)
        options_layout.setSpacing(12)

        # Audio Options Container
        self.audio_opts_widget = QWidget()
        audio_opts_layout = QVBoxLayout(self.audio_opts_widget)
        audio_opts_layout.setContentsMargins(0, 0, 0, 0)
        audio_opts_layout.setSpacing(10)

        audio_row = QHBoxLayout()
        audio_row.setSpacing(16)

        # Audio Format
        fmt_layout = QVBoxLayout()
        fmt_layout.setSpacing(4)
        fmt_label = QLabel("음원 포맷")
        fmt_label.setStyleSheet("color: #94A3B8; font-weight: 500;")
        self.combo_audio_format = QComboBox()
        self.combo_audio_format.addItems(["MP3 (가장 대중적)", "M4A (Apple AAC 고음질)", "FLAC (무손실)", "WAV (비압축 원음)", "OPUS (웹 표준)"])
        fmt_layout.addWidget(fmt_label)
        fmt_layout.addWidget(self.combo_audio_format)
        audio_row.addLayout(fmt_layout, 1)

        # Audio Quality
        qty_layout = QVBoxLayout()
        qty_layout.setSpacing(4)
        qty_label = QLabel("음질 (비트레이트)")
        qty_label.setStyleSheet("color: #94A3B8; font-weight: 500;")
        self.combo_audio_quality = QComboBox()
        self.combo_audio_quality.addItems(["최고음질 (320 kbps)", "고음질 (256 kbps)", "표준음질 (192 kbps)", "일반음질 (128 kbps)"])
        qty_layout.addWidget(qty_label)
        qty_layout.addWidget(self.combo_audio_quality)
        audio_row.addLayout(qty_layout, 1)

        audio_opts_layout.addLayout(audio_row)

        audio_checks_row = QHBoxLayout()
        self.check_embed_thumb = QCheckBox("앨범 커버(썸네일) 및 곡 정보 메타데이터 자동 삽입")
        self.check_embed_thumb.setChecked(True)
        audio_checks_row.addWidget(self.check_embed_thumb)
        audio_checks_row.addStretch()
        audio_opts_layout.addLayout(audio_checks_row)

        options_layout.addWidget(self.audio_opts_widget)

        # Video Options Container
        self.video_opts_widget = QWidget()
        video_opts_layout = QVBoxLayout(self.video_opts_widget)
        video_opts_layout.setContentsMargins(0, 0, 0, 0)
        video_opts_layout.setSpacing(10)

        video_row = QHBoxLayout()
        video_row.setSpacing(16)

        # Resolution
        res_layout = QVBoxLayout()
        res_layout.setSpacing(4)
        res_label = QLabel("해상도 (화질)")
        res_label.setStyleSheet("color: #94A3B8; font-weight: 500;")
        self.combo_video_res = QComboBox()
        self.combo_video_res.addItems([
            "최고 화질 (원본 해상도 자동 선택)",
            "4K UHD (2160p)",
            "2K QHD (1440p)",
            "Full HD (1080p)",
            "HD (720p)",
            "SD (480p)"
        ])
        res_layout.addWidget(res_label)
        res_layout.addWidget(self.combo_video_res)
        video_row.addLayout(res_layout, 1)

        # Video Format
        vfmt_layout = QVBoxLayout()
        vfmt_layout.setSpacing(4)
        vfmt_label = QLabel("동영상 포맷")
        vfmt_label.setStyleSheet("color: #94A3B8; font-weight: 500;")
        self.combo_video_format = QComboBox()
        self.combo_video_format.addItems(["MP4 (권장 / 호환성 최고)", "MKV (고급 미디어 컨테이너)"])
        vfmt_layout.addWidget(vfmt_label)
        vfmt_layout.addWidget(self.combo_video_format)
        video_row.addLayout(vfmt_layout, 1)

        video_opts_layout.addLayout(video_row)

        video_checks_row = QHBoxLayout()
        self.check_subtitles = QCheckBox("자막 다운로드 및 비디오에 포함 (가능한 경우)")
        self.check_subtitles.setChecked(False)
        video_checks_row.addWidget(self.check_subtitles)
        video_checks_row.addStretch()
        video_opts_layout.addLayout(video_checks_row)

        self.video_opts_widget.setVisible(False)
        options_layout.addWidget(self.video_opts_widget)

        main_layout.addWidget(self.options_frame)

        # 6. Destination Path Card
        dest_frame = QFrame()
        dest_frame.setObjectName("card")
        dest_frame.setProperty("class", "card")
        dest_layout = QHBoxLayout(dest_frame)
        dest_layout.setContentsMargins(16, 12, 16, 12)
        dest_layout.setSpacing(10)

        dest_lbl = QLabel("저장 폴더:")
        dest_lbl.setStyleSheet("font-weight: 600; color: #CBD5E1;")
        dest_layout.addWidget(dest_lbl)

        self.dest_input = QLineEdit(self.output_dir)
        self.dest_input.setReadOnly(True)
        dest_layout.addWidget(self.dest_input, 1)

        self.btn_browse = QPushButton("📁 변경...")
        self.btn_browse.clicked.connect(self.browse_folder)
        dest_layout.addWidget(self.btn_browse)

        self.btn_open_folder = QPushButton("📂 열기")
        self.btn_open_folder.clicked.connect(self.open_output_folder)
        dest_layout.addWidget(self.btn_open_folder)

        main_layout.addWidget(dest_frame)

        # 7. Progress & Status Card
        progress_frame = QFrame()
        progress_frame.setObjectName("card")
        progress_frame.setProperty("class", "card")
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(16, 14, 16, 14)
        progress_layout.setSpacing(10)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        # Metrics row (Speed, ETA, Size, Percent)
        metrics_layout = QHBoxLayout()
        self.lbl_percent = QLabel("0%")
        self.lbl_percent.setStyleSheet("font-weight: 700; color: #FFFFFF; font-size: 13px;")
        self.lbl_speed = QLabel("속도: --")
        self.lbl_speed.setStyleSheet("color: #94A3B8; font-size: 12px;")
        self.lbl_eta = QLabel("남은 시간: --")
        self.lbl_eta.setStyleSheet("color: #94A3B8; font-size: 12px;")
        self.lbl_size = QLabel("크기: -- / --")
        self.lbl_size.setStyleSheet("color: #94A3B8; font-size: 12px;")

        metrics_layout.addWidget(self.lbl_percent)
        metrics_layout.addSpacing(16)
        metrics_layout.addWidget(self.lbl_speed)
        metrics_layout.addSpacing(16)
        metrics_layout.addWidget(self.lbl_eta)
        metrics_layout.addSpacing(16)
        metrics_layout.addWidget(self.lbl_size)
        metrics_layout.addStretch()
        progress_layout.addLayout(metrics_layout)

        # Status label
        self.lbl_status = QLabel("준비 완료 - YouTube 링크를 입력하고 다운로드를 시작하세요.")
        self.lbl_status.setObjectName("statusLabel")
        self.lbl_status.setWordWrap(True)
        progress_layout.addWidget(self.lbl_status)

        main_layout.addWidget(progress_frame)

        # 8. Action Buttons (Start Download, Cancel)
        action_layout = QHBoxLayout()
        action_layout.setSpacing(12)

        self.btn_cancel = QPushButton("⏹ 취소")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_download)
        action_layout.addWidget(self.btn_cancel)

        self.btn_start = QPushButton("📥 다운로드 시작")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.clicked.connect(self.start_download)
        action_layout.addWidget(self.btn_start, 1)

        main_layout.addLayout(action_layout)

    def switch_mode(self, mode):
        self.current_mode = mode
        if mode == 'audio':
            self.btn_mode_audio.setChecked(True)
            self.btn_mode_video.setChecked(False)
            self.audio_opts_widget.setVisible(True)
            self.video_opts_widget.setVisible(False)
            self.mode_badge.setText("🎵 음원 다운로드 모드")
            self.mode_badge.setObjectName("badgeAudio")
            self.mode_badge.setStyle(self.mode_badge.style())
            self.btn_start.setText("📥 음원(오디오) 다운로드 시작")
        else:
            self.btn_mode_audio.setChecked(False)
            self.btn_mode_video.setChecked(True)
            self.audio_opts_widget.setVisible(False)
            self.video_opts_widget.setVisible(True)
            self.mode_badge.setText("🎬 동영상 다운로드 모드")
            self.mode_badge.setObjectName("badgeVideo")
            self.mode_badge.setStyle(self.mode_badge.style())
            self.btn_start.setText("📥 동영상 다운로드 시작")

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.url_input.setText(text)
            self.fetch_info()

    def on_url_changed(self, text):
        text = text.strip()
        # If user pasted a valid youtube link, enable fetch
        if "youtube.com" in text or "youtu.be" in text:
            self.btn_fetch.setEnabled(True)

    def fetch_info(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "입력 오류", "YouTube 링크(URL)를 입력해 주세요.")
            return

        self.lbl_status.setText("영상 정보를 분석하는 중입니다...")
        self.btn_fetch.setEnabled(False)
        self.btn_start.setEnabled(False)

        self.fetch_thread = InfoFetchThread(url)
        self.fetch_thread.info_fetched.connect(self.on_info_fetched)
        self.fetch_thread.error_occurred.connect(self.on_info_error)
        self.fetch_thread.start()

    def on_info_fetched(self, info):
        self.fetched_info = info
        self.info_frame.setVisible(True)
        self.info_title.setText(info['title'])
        self.info_channel.setText(f"채널: {info['uploader']}")
        self.info_duration.setText(f"재생시간: {info['duration_str']}")
        self.info_views.setText(f"조회수: {info['view_count_str']}")

        if info.get('is_playlist'):
            self.playlist_container.setVisible(True)
            self.playlist_label.setText(f"📋 재생목록 감지됨 ({info.get('playlist_count', 0)}개 영상)")
        else:
            self.playlist_container.setVisible(False)

        # Fetch thumbnail
        thumb_url = info.get('thumbnail')
        if thumb_url:
            self.thumb_thread = ThumbnailFetchThread(thumb_url)
            self.thumb_thread.thumbnail_loaded.connect(self.on_thumbnail_loaded)
            self.thumb_thread.start()

        self.lbl_status.setText(f"정보 확인 완료: {info['title']}")
        self.btn_fetch.setEnabled(True)
        self.btn_start.setEnabled(True)

    def on_info_error(self, err_msg):
        self.lbl_status.setText(f"정보 확인 실패: {err_msg}")
        self.btn_fetch.setEnabled(True)
        self.btn_start.setEnabled(True)
        QMessageBox.warning(self, "정보 가져오기 실패", f"영상 정보를 가져올 수 없습니다.\n\n오류: {err_msg}")

    def on_thumbnail_loaded(self, data):
        image = QImage()
        if image.loadFromData(data):
            pixmap = QPixmap.fromImage(image)
            scaled = pixmap.scaled(
                160, 90,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            self.thumb_label.setPixmap(scaled)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "저장 폴더 선택", self.output_dir)
        if folder:
            self.output_dir = folder
            self.dest_input.setText(folder)

    def open_output_folder(self):
        if os.path.exists(self.output_dir):
            os.startfile(self.output_dir)
        else:
            QMessageBox.information(self, "안내", "저장 폴더가 아직 생성되지 않았습니다.")

    def get_audio_options(self):
        format_map = {0: 'mp3', 1: 'm4a', 2: 'flac', 3: 'wav', 4: 'opus'}
        quality_map = {0: '320', 1: '256', 2: '192', 3: '128'}
        
        fmt_idx = self.combo_audio_format.currentIndex()
        qty_idx = self.combo_audio_quality.currentIndex()
        
        return {
            'format': format_map.get(fmt_idx, 'mp3'),
            'quality': quality_map.get(qty_idx, '320'),
            'embed_thumbnail': self.check_embed_thumb.isChecked(),
            'add_metadata': True,
            'is_playlist': self.check_download_playlist.isChecked() if self.playlist_container.isVisible() else False
        }

    def get_video_options(self):
        res_map = {
            0: 'best',
            1: '2160',
            2: '1440',
            3: '1080',
            4: '720',
            5: '480'
        }
        fmt_map = {0: 'mp4', 1: 'mkv'}
        
        res_idx = self.combo_video_res.currentIndex()
        fmt_idx = self.combo_video_format.currentIndex()
        
        return {
            'resolution': res_map.get(res_idx, 'best'),
            'format': fmt_map.get(fmt_idx, 'mp4'),
            'subtitles': self.check_subtitles.isChecked(),
            'is_playlist': self.check_download_playlist.isChecked() if self.playlist_container.isVisible() else False
        }

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "입력 오류", "YouTube 링크(URL)를 입력해 주세요.")
            return

        # Prepare options
        if self.current_mode == 'audio':
            options = self.get_audio_options()
        else:
            options = self.get_video_options()

        # UI State update
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_fetch.setEnabled(False)
        self.url_input.setEnabled(False)
        self.progress_bar.setValue(0)
        self.lbl_percent.setText("0%")
        self.lbl_speed.setText("속도: --")
        self.lbl_eta.setText("남은 시간: --")
        self.lbl_size.setText("크기: -- / --")
        self.lbl_status.setText("다운로드 준비 중...")

        # Start thread
        self.download_thread = DownloadThread(
            url=url,
            output_dir=self.output_dir,
            mode=self.current_mode,
            options=options
        )
        self.download_thread.progress_updated.connect(self.on_download_progress)
        self.download_thread.status_updated.connect(self.on_status_updated)
        self.download_thread.download_finished.connect(self.on_download_finished)
        self.download_thread.error_occurred.connect(self.on_download_error)
        self.download_thread.start()

    def cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.lbl_status.setText("다운로드 취소 요청 중...")
            self.download_thread.cancel()
            self.btn_cancel.setEnabled(False)

    def on_download_progress(self, d):
        if d.get('status') == 'downloading':
            percent = int(d.get('percent', 0))
            self.progress_bar.setValue(percent)
            self.lbl_percent.setText(f"{percent}%")
            self.lbl_speed.setText(f"속도: {d.get('speed_str', '--')}")
            self.lbl_eta.setText(f"남은 시간: {d.get('eta_str', '--')}")
            self.lbl_size.setText(f"크기: {d.get('downloaded_str', '--')} / {d.get('total_str', '--')}")
            self.lbl_status.setText("다운로드 진행 중...")
        elif d.get('status') == 'finished':
            self.progress_bar.setValue(100)
            self.lbl_percent.setText("100%")
            self.lbl_status.setText("다운로드 완료! 후처리(변환 및 태그 삽입) 진행 중...")

    def on_status_updated(self, msg):
        self.lbl_status.setText(msg)

    def on_download_finished(self, out_dir):
        self.progress_bar.setValue(100)
        self.lbl_percent.setText("100%")
        self.lbl_status.setText("🎉 모든 작업이 완료되었습니다! 파일이 저장되었습니다.")
        self.reset_download_controls()

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("다운로드 완료")
        msg_box.setText("다운로드가 성공적으로 완료되었습니다!\n\n저장 폴더를 여시겠습니까?")
        msg_box.setIcon(QMessageBox.Icon.Information)
        btn_open = msg_box.addButton("폴더 열기", QMessageBox.ButtonRole.AcceptRole)
        btn_close = msg_box.addButton("확인", QMessageBox.ButtonRole.RejectRole)
        msg_box.setDefaultButton(btn_open)
        msg_box.exec()

        if msg_box.clickedButton() == btn_open:
            self.open_output_folder()

    def on_download_error(self, err_msg):
        self.reset_download_controls()
        if err_msg == "CANCELLED":
            self.lbl_status.setText("다운로드가 취소되었습니다.")
            return
        self.lbl_status.setText("오류가 발생했습니다.")
        QMessageBox.critical(self, "다운로드 오류", f"다운로드 중 오류가 발생했습니다:\n\n{err_msg}")

    def reset_download_controls(self):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_fetch.setEnabled(True)
        self.url_input.setEnabled(True)


def main():
    try:
        import ctypes
        myappid = 'antigravity.youtubedownloader.gui.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("YouTubeDownloader")
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    window = YouTubeDownloaderApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
