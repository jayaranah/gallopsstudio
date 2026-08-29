#!/usr/bin/env python3
"""
Gallops Studio — PyQt6 Edition
Modern GUI built with PyQt6; core render/player/export engine unchanged.
"""

# ─── stdlib ──────────────────────────────────────────────────────────────────
import sys, os, re, time, threading, subprocess, platform, math
import json, random, colorsys, tempfile, glob
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from pathlib import Path

# ─── third-party ─────────────────────────────────────────────────────────────
import pygame
import numpy as np
from PIL import Image, ImageFilter

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QScrollArea,
    QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QSlider, QComboBox, QCheckBox, QLineEdit,
    QColorDialog, QFileDialog, QInputDialog, QProgressBar, QTextEdit,
    QTabWidget, QFrame, QSizePolicy, QToolButton, QStatusBar,
    QDialog, QDialogButtonBox, QMessageBox, QToolBar, QSpinBox,
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize, QRect, QPointF, QRectF,
)
from PyQt6.QtGui import (
    QImage, QPixmap, QPainter, QColor, QFont, QIcon, QPalette,
    QAction, QKeySequence, QLinearGradient,
)

def _subprocess_flags() -> int:
    """Return CREATE_NO_WINDOW flag on Windows, 0 otherwise."""
    if platform.system() == "Windows":
        return subprocess.CREATE_NO_WINDOW
    return 0


# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
DEFAULT_WIN_W, DEFAULT_WIN_H = 1280, 720
ANIMATION_SPEED = 8.0
IS_WINDOWS = platform.system() == "Windows"
IS_MAC     = platform.system() == "Darwin"

CONFIG_PATH   = os.path.join(os.path.expanduser("~"), ".gallops_studio_config.json")
PROFILES_DIR  = os.path.join(os.path.expanduser("~"), ".gallops_studio_profiles")
PROJECTS_PATH = os.path.join(os.path.expanduser("~"), ".gallops_studio_projects.json")
RECENT_MAX    = 5
PROJECTS_MAX  = 10
UNDO_MAX      = 50

# Keys deliberately left out of saved presets — a preset is a "look", not a
# reference to specific media files, so the currently loaded audio, lyrics,
# and background image/video are always left untouched by save/load preset.
PRESET_EXCLUDED_KEYS = {"audio_path", "lrc_path", "bg_image_path", "bg_video_path"}

LYRIC_STYLES   = ["filled", "outline", "glow", "gradient"]
LIGHTS_PATTERNS = ["random", "sync", "wave", "alternate", "converge", "chase",
                   "spiral", "figure8", "pulse", "shuffle"]
AUDIO_BITRATES = ["96k", "128k", "160k", "192k", "256k", "320k", "384k"]
ENCODING_PRESETS = ["ultrafast","superfast","veryfast","faster","fast",
                    "medium","slow","slower","veryslow"]
EXPORT_CODECS    = ["libx264", "libx265", "libvpx-vp9"]
EXPORT_TUNES_264 = ["none","film","animation","grain","fastdecode"]
EXPORT_TUNES_265 = ["none","grain","animation","fastdecode","zerolatency"]
EXPORT_PROFILES  = ["baseline", "main", "high"]

VIDEO_PRESETS = {
    "Archive/Master": {"crf":16,"preset":"slow",   "audio_bitrate":"320k"},
    "YouTube/1080p":  {"crf":18,"preset":"medium", "audio_bitrate":"256k"},
    "Standard/720p":  {"crf":20,"preset":"fast",   "audio_bitrate":"192k"},
    "Social Media":   {"crf":22,"preset":"fast",   "audio_bitrate":"160k"},
    "Mobile/Quick":   {"crf":25,"preset":"veryfast","audio_bitrate":"128k"},
}
RESOLUTIONS = {
    "480p (SD)":  (854,  480),
    "720p (HD)":  (1280, 720),
    "1080p (FHD)":(1920,1080),
    "1440p (QHD)":(2560,1440),
    "4K (UHD)":   (3840,2160),
    "1080p Vertical (9:16)": (1080, 1920),
}

C_BG = (10, 10, 30)

# pygame colour constants (used only by renderer)
_C_SUNG  = (255, 220, 60)
_C_NEXT  = (200, 200, 220)


# ══════════════════════════════════════════════════════════════════════════════
#  DARK THEME  (applied once at startup)
# ══════════════════════════════════════════════════════════════════════════════
DARK_QSS = """
QWidget          { background:#12102a; color:#e0e0f0; font-size:11px; }
QGroupBox        { border:1px solid #3a3860; border-radius:6px; margin-top:18px;
                   padding-top:4px; font-weight:bold; color:#ff8800; font-size: 13px; }
QGroupBox::title { subcontrol-origin:margin; subcontrol-position:top left;
                   left:8px; top:-2px; padding:0 4px; }
QPushButton      { background:#2a285a; border:1px solid #4a4880; border-radius:5px;
                   padding:4px 10px; }
QPushButton:hover{ background:#3a3870; }
QPushButton:pressed { background:#1a1840; }
QPushButton.danger   { background:#5a1a1a; border-color:#883333; }
QPushButton.danger:hover { background:#7a2020; }
QPushButton.action   { background:#1a5a2a; border-color:#338833; }
QPushButton.action:hover { background:#206030; }
QSlider::groove:horizontal { height:6px; background:#2a2850; border-radius:3px; }
QSlider::handle:horizontal { width:16px; height:16px; margin:-5px 0;
                              background:#a090ff; border-radius:8px; border:1px solid #c0b0ff; }
QSlider::sub-page:horizontal { background:#6050c0; border-radius:3px; }
QSlider { min-height:22px; }
QComboBox        { background:#2a285a; border:1px solid #4a4880; border-radius:5px;
                   padding:3px 8px; }
QComboBox::drop-down { border:none; width:20px; }
QComboBox QAbstractItemView { background:#1e1c40; selection-background-color:#4a4880; }
QCheckBox::indicator { width:16px; height:16px; border:1px solid #4a4880;
                       border-radius:3px; background:#1e1c40; }
QCheckBox::indicator:checked { background:#6050c0; }
QLineEdit        { background:#1e1c40; border:1px solid #3a3860; border-radius:5px;
                   padding:3px 8px; }
QTextEdit        { background:#0a0820; border:1px solid #2a2850; border-radius:5px;
                   font-family:Consolas,monospace; font-size:11px; color:#60d060; }
QScrollBar:vertical   { background:#0e0c28; width:10px; border-radius:5px; margin:0; }
QScrollBar::handle:vertical { background:#4a4890; border-radius:5px; min-height:30px; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height:0; border:none; }
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical { background:none; }
QTabWidget::pane  { border:1px solid #3a3860; }
QTabBar::tab      { background:#1e1c40; border:1px solid #3a3860; padding:5px 14px;
                    border-bottom:none; border-radius:5px 5px 0 0; }
QTabBar::tab:selected { background:#2a285a; color:#a090ff; }
QProgressBar      { background:#1e1c40; border:1px solid #3a3860; border-radius:5px;
                    text-align:center; }
QProgressBar::chunk { background:#6050c0; border-radius:5px; }
QToolBar          { background:#0e0c28; border-bottom:1px solid #3a3860; spacing:4px; }
QStatusBar        { background:#0e0c28; color:#808090; border-top:1px solid #2a2850; }
QSplitter::handle { background:#3a3860; }
"""


# ══════════════════════════════════════════════════════════════════════════════
#  SVG ICON LOADER
# ══════════════════════════════════════════════════════════════════════════════
def load_svg_icon(filename: str, size: QSize = QSize(24, 24)) -> QIcon:
    """Load an SVG icon from the icons/ folder."""
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, "icons", filename)
    
    if not os.path.exists(icon_path):
        # Return a simple colored rectangle as fallback
        pixmap = QPixmap(size)
        pixmap.fill(QColor(100, 100, 180))
        return QIcon(pixmap)
    
    # Load SVG as QIcon (Qt handles SVG rendering)
    return QIcon(icon_path)

def create_toolbar_icon(filename: str, size: int = 24) -> QIcon:
    """Create a toolbar icon with proper sizing."""
    icon = load_svg_icon(filename, QSize(size, size))
    # Ensure the icon is available at multiple sizes for HiDPI
    return icon


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS (non-GUI, ported from original)
# ══════════════════════════════════════════════════════════════════════════════
def _find_ffmpeg() -> str:
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        c = os.path.join(bundle, "ffmpeg.exe" if IS_WINDOWS else "ffmpeg")
        if os.path.isfile(c): return c
    beside = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "ffmpeg.exe" if IS_WINDOWS else "ffmpeg")
    if os.path.isfile(beside): return beside
    return "ffmpeg"

FFMPEG_BIN = _find_ffmpeg()

def get_audio_duration(path: str) -> Optional[float]:
    try:
        r = subprocess.run(
            ["ffprobe","-v","error","-show_entries","format=duration",
             "-of","default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=15, creationflags=_subprocess_flags())
        v = r.stdout.strip()
        return float(v) if v else None
    except Exception:
        return None

def _win_fonts() -> Dict[str, str]:
    roots = [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
             os.path.join(os.environ.get("LOCALAPPDATA",""),"Microsoft","Windows","Fonts")]
    cands = {"Arial Bold":["arialbd.ttf"],"Arial":["arial.ttf"],
             "Segoe UI Bold":["segoeuib.ttf"],"Segoe UI":["segoeui.ttf"],
             "Calibri Bold":["calibrib.ttf"],"Calibri":["calibri.ttf"],
             "Verdana Bold":["verdanab.ttf"],"Verdana":["verdana.ttf"]}
    found = {}
    for name, fns in cands.items():
        for root in roots:
            for fn in fns:
                p = os.path.join(root, fn)
                if os.path.exists(p): found[name]=p; break
            if name in found: break
    return found

def _mac_fonts() -> Dict[str, str]:
    roots = ["/Library/Fonts","/System/Library/Fonts",
             os.path.expanduser("~/Library/Fonts")]
    cands = {"Helvetica Neue Bold":["HelveticaNeue-Bold.ttf"],
             "Arial Bold":["Arial Bold.ttf"],"Arial":["Arial.ttf"]}
    found = {}
    for name, fns in cands.items():
        for root in roots:
            for fn in fns:
                p = os.path.join(root, fn)
                if os.path.exists(p): found[name]=p; break
    return found

def _linux_fonts() -> Dict[str, str]:
    cands = {"Liberation Sans":"/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
             "DejaVu Sans":"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"}
    return {k:v for k,v in cands.items() if os.path.exists(v)}

# ─── Custom fonts ──────────────────────────────────────────────────────────
def get_custom_fonts() -> Dict[str, str]:
    """Scan the fonts folder for .ttf and .otf files."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fonts_dir = os.path.join(script_dir, "fonts")
    if not os.path.isdir(fonts_dir):
        return {}
    custom = {}
    for file in os.listdir(fonts_dir):
        if file.lower().endswith(('.ttf', '.otf')):
            path = os.path.join(fonts_dir, file)
            name = os.path.splitext(file)[0]       # filename without extension
            # Avoid duplicate display names
            if name in custom:
                name = f"{name} (custom)"
            custom[name] = path
    return custom

def discover_fonts() -> Dict[str, str]:
    """Merge system fonts with custom fonts from the 'fonts' folder."""
    if IS_WINDOWS:
        f = _win_fonts()
    elif IS_MAC:
        f = _mac_fonts()
    else:
        f = _linux_fonts()
    if not f:
        f = {}
    custom = get_custom_fonts()
    # Merge custom fonts, avoiding name collisions
    for name, path in custom.items():
        if name not in f:
            f[name] = path
        else:
            f[f"Custom: {name}"] = path
    return f or {"System Default": None}

FONT_OPTIONS: Dict[str, Optional[str]] = discover_fonts()

def get_default_heart_svg() -> Optional[str]:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(script_dir, "hearts", "heart.svg")
    return p if os.path.exists(p) else None

def get_fallback_font_path() -> Optional[str]:
    for v in FONT_OPTIONS.values():
        if v and os.path.exists(v): return v
    return None

def strip_emoji(text: str) -> str:
    import unicodedata
    return "".join(c for c in text
                   if not (0x1F000 <= ord(c) <= 0x1FFFF or
                           0x2600  <= ord(c) <= 0x27BF  or
                           0xFE00  <= ord(c) <= 0xFE0F))


# ══════════════════════════════════════════════════════════════════════════════
#  LRC PARSER  (unchanged from original)
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class Syllable:
    time: float; text: str
    progress: float = 0.0; target_progress: float = 0.0

@dataclass
class LrcLine:
    start: float
    syllables: List[Syllable] = field(default_factory=list)
    @property
    def full_text(self): return "".join(s.text for s in self.syllables)
    @property
    def end(self):
        return (self.syllables[-1].time + 0.5) if self.syllables else self.start+3.0

def _clean(t): return (t.replace('\x92',"'").replace('\x91',"'")
                        .replace('\x93','"').replace('\x94','"'))

def parse_lrc(path: str) -> List[LrcLine]:
    lines = []
    with open(path, encoding="utf-8", errors="replace") as f:
        raw = f.read()
    for raw_line in raw.splitlines():
        raw_line = _clean(raw_line.strip())
        if not raw_line: continue
        if re.match(r'^\[[a-zA-Z]+:.+\]$', raw_line) and not re.match(r'^\[\d+:', raw_line):
            continue
        m = re.match(r'^\[(\d+):(\d+\.\d+)\](.*)', raw_line)
        if not m: continue
        line_start = int(m.group(1))*60 + float(m.group(2))
        rest = m.group(3)
        syllables, pending_text, pending_time = [], "", line_start
        for tok in re.split(r'(<\d+:\d+\.\d+>)', rest):
            ts = re.match(r'<(\d+):(\d+\.\d+)>', tok)
            if ts:
                if pending_text: syllables.append(Syllable(pending_time, pending_text))
                pending_time = int(ts.group(1))*60 + float(ts.group(2))
                pending_text = ""
            else:
                pending_text += tok
        if pending_text: syllables.append(Syllable(pending_time, pending_text))
        syllables = [s for s in syllables if s.text]
        if syllables: lines.append(LrcLine(line_start, syllables))
    lines.sort(key=lambda l: l.start)
    return lines

def extract_lrc_metadata(path: str) -> dict:
    meta = {"title":"","artist":""}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r'^\[([a-zA-Z]+):(.+)\]$', line.strip())
                if m:
                    k, v = m.group(1).lower(), m.group(2).strip()
                    if k == "ti": meta["title"] = v
                    elif k == "ar": meta["artist"] = v
    except Exception: pass
    return meta


# ══════════════════════════════════════════════════════════════════════════════
#  SETTINGS  (unchanged from original)
# ══════════════════════════════════════════════════════════════════════════════
class Settings:
    def __init__(self):
        self.font_name  = list(FONT_OPTIONS.keys())[0]
        self.font_size  = 52
        self.offset_x   = 0; self.offset_y = 0
        self.bg_image_path: Optional[str] = None
        self.bg_blur    = 0
        self.audio_path: Optional[str] = None
        self.lrc_path:   Optional[str] = None
        self.bg_video_path: Optional[str] = None
        self.bg_video_muted = True
        self.color_sung = _C_SUNG; self.color_next = _C_NEXT
        self.video_preset = "Standard/720p"
        self.video_resolution = "720p (HD)"
        self.export_fps = 30
        self.custom_crf = 20; self.custom_preset = "fast"
        self.custom_audio_bitrate = 3
        self.use_custom_settings = False
        self.custom_codec   = "libx264"; self.custom_tune = "none"
        self.custom_profile = "high"
        self.custom_two_pass = False; self.custom_target_size_mb = 0
        self.lyric_style = "filled"
        self.lyric_bg_opacity = 140
        self.lyric_bg_color   = (0, 0, 0)
        self.lyric_bg_radius  = -1
        self.glow_radius = 0; self.glow_color = (255,220,60); self.glow_distance = 2
        self.stroke_width = 0; self.stroke_color = (0,0,0)
        self.shadow_offset = 2; self.line_spacing = 50
        self.wipe_highlight = True; self.wipe_color = (255,255,255)
        self.countdown_bar = True
        self.countdown_bar_color_start = (255,80,80)
        self.countdown_bar_color_end   = (80,200,255)
        self.countdown_bar_height = 5
        self.countdown_bar_stroke_width = 0
        self.countdown_bar_stroke_color = (255, 255, 255)
        self.fade_out_floor = 0
        self.startup_info_enabled  = True
        self.startup_info_title    = ""
        self.startup_info_artist   = ""
        self.startup_info_duration = 40
        self.startup_info_offset_x = 0; self.startup_info_offset_y = 0
        self.startup_info_bg_image: Optional[str] = None
        self.startup_info_direction = "top"
        self.startup_info_neon_enabled = True
        self.startup_info_neon_width   = 3
        self.startup_info_neon_color   = (0,200,255)
        self.startup_info_delay        = 0
        self.visualizer_enabled = False
        self.visualizer_style   = "bars"
        self.visualizer_color   = (80,200,255)
        self.visualizer_height  = 120; self.visualizer_bands = 32
        self.visualizer_opacity = 200
        self.bg_pulse_enabled      = False
        self.bg_pulse_freq_low     = 20; self.bg_pulse_freq_high = 200
        self.bg_pulse_threshold    = 10; self.bg_pulse_oscillation = 40
        self.bg_pulse_initial_zoom = 0;  self.bg_pulse_zoom_level  = 20
        self.snow_enabled  = False; self.snow_count  = 120
        self.snow_speed    = 40;    self.snow_size   = 4
        self.snow_opacity  = 180;   self.snow_wind   = 0
        self.hearts_enabled  = False; self.hearts_count    = 40
        self.hearts_speed    = 35;    self.hearts_min_size = 12
        self.hearts_max_size = 32;    self.hearts_opacity  = 200
        self.hearts_color_r  = 255;   self.hearts_color_g  = 80
        self.hearts_color_b  = 120
        self.hearts_svg_path: Optional[str] = get_default_heart_svg()
        self.hearts_color_overlay = True   # tint SVG with hearts_color_r/g/b; if off, use SVG's own colors
        
        self.lights_enabled    = False; self.lights_count     = 6
        self.lights_speed      = 40;    self.lights_opacity   = 80
        self.lights_width      = 40;    self.lights_length    = 80
        self.lights_rainbow    = True;  self.lights_reactive  = True
        self.lights_pattern    = "random"   # random|sync|wave|alternate|converge|chase|spiral|figure8|pulse|shuffle
        self.lights_pulse      = True;  self.lights_pulse_sens= 60
        self.lights_neon_glow   = True
        self.lights_glow_radius = 8
        self.lyric_bg_image_path: Optional[str] = None
        self.lyric_bg_image_opacity = 180
        self.lyric_bg_image_mode    = "tile"
        self.lyric_bg_pad_extra     = 0
        self.lyric_bg_height_extra  = 0
        self.recent_audio: List[str] = []
        self.recent_lrc:   List[str] = []
        self.recent_bg:    List[str] = []
        self._lrc_meta_title  = ""
        self._lrc_meta_artist = ""
        self.glow_opacity = 140   # 0-255, default ~55%
        self.glow_brightness = 150   # 50% to 300%
        self.glow_intensity = 100   # 0–200%

    @property
    def font_path(self) -> Optional[str]:
        return FONT_OPTIONS.get(self.font_name)

    def _push_recent(self, lst, path):
        path = os.path.normpath(path)
        lst[:] = [p for p in lst if p != path and os.path.exists(p)]
        lst.insert(0, path)
        while len(lst) > RECENT_MAX: lst.pop()

    def push_recent_audio(self, p): self._push_recent(self.recent_audio, p)
    def push_recent_lrc(self,   p): self._push_recent(self.recent_lrc,   p)
    def push_recent_bg(self,    p): self._push_recent(self.recent_bg,    p)

    def _data_dict(self) -> dict:
        skip = {"_lrc_meta_title","_lrc_meta_artist"}
        d = {}
        for k, v in self.__dict__.items():
            if k.startswith("_") and k not in {"_lrc_meta_title","_lrc_meta_artist"}: continue
            if k in skip: continue
            d[k] = list(v) if isinstance(v, tuple) else v
        return d

    def save(self):
        try:
            with open(CONFIG_PATH,"w",encoding="utf-8") as f:
                json.dump(self._data_dict(), f, indent=2)
        except Exception as e:
            print(f"[Settings] save failed: {e}")

    def _apply(self, data: dict):
        for k, v in data.items():
            if not hasattr(self, k): continue
            cur = getattr(self, k)
            if isinstance(cur, tuple) and isinstance(v, list):
                setattr(self, k, tuple(v))
            else:
                setattr(self, k, v)

    def load(self):
        if not os.path.exists(CONFIG_PATH): return
        try:
            with open(CONFIG_PATH,"r",encoding="utf-8") as f:
                self._apply(json.load(f))
        except Exception as e:
            print(f"[Settings] load failed: {e}")

    def save_dict(self) -> dict:
        return json.loads(json.dumps(self._data_dict()))

    def load_dict(self, data: dict):
        backup = None
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH,"r") as f: backup = f.read()
            with open(CONFIG_PATH,"w") as f: json.dump(data, f)
            self.load()
        finally:
            if backup is not None:
                with open(CONFIG_PATH,"w") as f: f.write(backup)
            elif os.path.exists(CONFIG_PATH):
                os.remove(CONFIG_PATH)


# ══════════════════════════════════════════════════════════════════════════════
#  VIDEO BACKGROUND  (unchanged from original)
# ══════════════════════════════════════════════════════════════════════════════
class VideoBackground:
    def __init__(self):
        self._cap = None; self._path = None
        self._fps = 30.0; self._frame_count = 0; self._cv2_ok = False
        self._front = None; self._back = None
        self._buf_lock = threading.Lock()
        self._new_frame = False
        self._thread = None; self._stop_evt = threading.Event()
        self._elapsed = 0.0; self._playing = False
        self._state_lock = threading.Lock()
        self._target_size = None; self._blur = 0
        self._params_lock = threading.Lock()
        try:
            import cv2; self._cv2_ok = True
        except ImportError:
            print("[VideoBackground] pip install opencv-python")

    def load(self, path: str):
        if not self._cv2_ok: return
        import cv2
        self.close()
        cap = cv2.VideoCapture(path)
        if not cap.isOpened(): return
        self._cap = cap; self._path = path
        self._fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self._frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._front = self._back = None; self._new_frame = False
        self._elapsed = 0.0; self._playing = False
        self._stop_evt.clear()
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = cap.read()
            if ok:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self._front = pygame.surfarray.make_surface(rgb.swapaxes(0,1))
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        except Exception: pass
        self._thread = threading.Thread(target=self._decode_loop, daemon=True)
        self._thread.start()

    def close(self):
        self._stop_evt.set()
        if self._thread: self._thread.join(timeout=2.0); self._thread = None
        if self._cap:   self._cap.release(); self._cap = None
        self._front = self._back = None

    @property
    def loaded(self): return self._cap is not None and self._cv2_ok

    def set_render_params(self, size, blur=0):
        with self._params_lock: self._target_size = size; self._blur = blur

    def notify_elapsed(self, elapsed, playing):
        with self._state_lock: self._elapsed = elapsed; self._playing = playing

    def get_frame(self, elapsed, size, blur=0):
        if not self.loaded: return None
        self.set_render_params(size, blur)
        with self._state_lock: self._elapsed = elapsed
        with self._buf_lock:
            if self._new_frame and self._back is not None:
                self._front, self._back = self._back, self._front
                self._new_frame = False
        return self._front

    def get_frame_direct(self, elapsed, size, blur=0):
        if not self.loaded: return None
        import cv2
        total = max(1, self._frame_count)
        fi = int(elapsed * self._fps) % total
        cap_pos = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES))
        if abs(cap_pos - fi) > 1: self._cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = self._cap.read()
        if not ok:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0); ok, frame = self._cap.read()
        if not ok: return self._front
        h, w = frame.shape[:2]
        if (w,h) != size: frame = cv2.resize(frame, size, interpolation=cv2.INTER_LINEAR)
        if blur > 0: k=blur*2+1; frame = cv2.GaussianBlur(frame,(k,k),0)
        return pygame.surfarray.make_surface(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB).swapaxes(0,1))

    def _decode_loop(self):
        import cv2, time as _t
        cap=self._cap; fps=self._fps; total=max(1,self._frame_count)
        frame_dur=1.0/fps; fi=0; last_wall=_t.perf_counter()
        while not self._stop_evt.is_set():
            with self._state_lock: elapsed=self._elapsed; playing=self._playing
            with self._params_lock: tgt=self._target_size; blur=self._blur
            if not playing: self._stop_evt.wait(timeout=0.05); continue
            target_fi = int(elapsed*fps) % total
            drift = target_fi - fi
            if drift < -(total//2): drift += total
            if abs(drift) > int(fps*0.5):
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_fi); fi=target_fi
                last_wall=_t.perf_counter()
            ok, frame = cap.read()
            if not ok: cap.set(cv2.CAP_PROP_POS_FRAMES,0); fi=0; last_wall=_t.perf_counter(); continue
            if tgt:
                h,w=frame.shape[:2]
                if (w,h)!=tgt: frame=cv2.resize(frame,tgt,interpolation=cv2.INTER_LINEAR)
            if blur>0: k=blur*2+1; frame=cv2.GaussianBlur(frame,(k,k),0)
            surf=pygame.surfarray.make_surface(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB).swapaxes(0,1))
            with self._buf_lock: self._back=surf; self._new_frame=True
            fi += 1
            now=_t.perf_counter(); sleep_t=last_wall+frame_dur-now
            if sleep_t>0.001: self._stop_evt.wait(timeout=sleep_t)
            last_wall=max(now, last_wall+frame_dur)


# ══════════════════════════════════════════════════════════════════════════════
#  RENDERER  (pygame — unchanged from original, runs on a hidden surface)
# ══════════════════════════════════════════════════════════════════════════════
_font_cache: Dict = {}

def make_font(path, size):
    size = max(6, int(size))   # guard: pygame font size must be > 0
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = (pygame.font.Font(path, size)
                            if path and os.path.exists(path)
                            else pygame.font.SysFont("arial", size))
    return _font_cache[key]

class GallopsStudioRenderer:
    """pygame-based renderer — identical logic to original, just extracted."""
    def __init__(self, settings: Settings, video_bg: VideoBackground = None):
        self.settings  = settings
        self.video_bg  = video_bg
        self.export_mode = False
        self._bg_surf  = None; self._bg_key = None
        self._bg_pil_raw = None; self._bg_raw_key = None
        self._bg_pulse_level = 0.0
        self.last_elapsed = 0.0
        self.slot_top_line_index    = 0
        self.slot_bottom_line_index = 1
        self._top_replaced_for_line    = -1
        self._bottom_replaced_for_line = -1
        self._top_pending_next    = -1
        self._bottom_pending_next = -1
        self._top_alpha    = 255.0; self._bottom_alpha    = 255.0
        self._top_fade_timer    = 0.0; self._bottom_fade_timer    = 0.0
        self._top_hold_timer    = 0.0; self._bottom_hold_timer    = 0.0
        self._has_reset = False
        self._snowflakes = []; self._snow_surface = None; self._snow_surf_size=(0,0)
        self._hearts = []; self._hearts_surface = None; self._hearts_surf_size=(0,0)
        self._lights = []; self._lights_surface = None; self._lights_surf_size=(0,0)
        self._lights_bass_level = 0.0; self._lights_beat_level = 0.0
        self._lights_beat_prev  = 0.0
        self._lights_t = 0.0
        self.pcm_bands = None
        self._raw_bass_energy    = 0.0
        self._pulse_spectrum     = None
        self._pulse_spectrum_bins= 1
        self._pulse_spectrum_rate= 44100
        self._pulse_peak         = 1e-6

    def reset(self):
        self.slot_top_line_index = 0; self.slot_bottom_line_index = 1
        self._top_replaced_for_line = -1; self._bottom_replaced_for_line = -1
        self._top_pending_next = -1;      self._bottom_pending_next = -1
        self._top_alpha = 0.0;            self._bottom_alpha = 0.0
        self._top_fade_timer = 0.0;       self._bottom_fade_timer = 0.0
        self._top_hold_timer = 0.0;       self._bottom_hold_timer = 0.0
        self._has_reset = True
        self._bg_pulse_level = 0.0; self.pcm_bands = None

    def invalidate(self):
        _font_cache.clear(); self._bg_surf=None; self._bg_key=None
        self._bg_pil_raw=None; self._bg_raw_key=None

    def invalidate_font(self): _font_cache.clear()

    def invalidate_bg(self): self._bg_surf=None; self._bg_key=None

    def get_bg(self, size):
        p = self.settings.bg_image_path; b = self.settings.bg_blur
        if not p or not os.path.exists(p): self._bg_surf=None; self._bg_key=None; return None
        raw_key = (p, size)
        if raw_key != self._bg_raw_key:
            self._bg_pil_raw = Image.open(p).convert("RGB").resize(size, Image.BICUBIC)
            self._bg_raw_key = raw_key; self._bg_key = None
        full_key = (p, b, size)
        if full_key != self._bg_key:
            pil = self._bg_pil_raw.filter(ImageFilter.GaussianBlur(b*3)) if b>0 else self._bg_pil_raw
            self._bg_surf = pygame.image.fromstring(pil.tobytes(), size, "RGB")
            self._bg_key  = full_key
        return self._bg_surf

    # ── The full render method and all helpers are copied verbatim from
    #    the original file.  They are pygame-only and have zero Qt dependency.
    # ─────────────────────────────────────────────────────────────────────────

    def _lerp_color(self, c1, c2, t):
        return tuple(int(c1[i]+(c2[i]-c1[i])*t) for i in range(3))

    def update_slots(self, all_lines, elapsed):
        if not all_lines: return
        if elapsed < 0.01 and not self._has_reset: self.reset(); return
        if elapsed > 0.1: self._has_reset = False
        if elapsed > all_lines[-1].end + 2.0: return
        def _get(idx):
            return all_lines[idx] if 0<=idx<len(all_lines) else None
        top_line    = _get(self.slot_top_line_index)
        bottom_line = _get(self.slot_bottom_line_index)
        if top_line and elapsed > top_line.end:
            if self._top_pending_next==-1 and self._top_replaced_for_line!=self.slot_top_line_index:
                nx = self.slot_top_line_index+2
                self._top_pending_next = nx if nx < len(all_lines) else -2
        if bottom_line and elapsed > bottom_line.end:
            if self._bottom_pending_next==-1 and self._bottom_replaced_for_line!=self.slot_bottom_line_index:
                nx = self.slot_bottom_line_index+2
                self._bottom_pending_next = nx if nx < len(all_lines) else -2
        bottom_line = _get(self.slot_bottom_line_index)
        if self._top_pending_next>=0 and bottom_line:
            if elapsed>=bottom_line.start and elapsed>0.05:
                self._top_replaced_for_line = self.slot_top_line_index
                self.slot_top_line_index = self._top_pending_next
                self._top_pending_next = -1
                self._top_alpha=0.0; self._top_fade_timer=0.0; self._top_hold_timer=0.0
        top_line = _get(self.slot_top_line_index)
        if self._bottom_pending_next>=0 and top_line:
            if elapsed>=top_line.start and elapsed>0.05:
                self._bottom_replaced_for_line = self.slot_bottom_line_index
                self.slot_bottom_line_index = self._bottom_pending_next
                self._bottom_pending_next = -1
                self._bottom_alpha=0.0; self._bottom_fade_timer=0.0; self._bottom_hold_timer=0.0
        top_line    = _get(self.slot_top_line_index)
        bottom_line = _get(self.slot_bottom_line_index)
        if top_line    and elapsed<=top_line.end:
            self._top_replaced_for_line=-1;    self._top_pending_next=-1
        if bottom_line and elapsed<=bottom_line.end:
            self._bottom_replaced_for_line=-1; self._bottom_pending_next=-1

    def update_syllable_progress(self, line, elapsed, dt):
        syls = line.syllables; n = len(syls)
        for idx, syl in enumerate(syls):
            if elapsed >= syl.time:
                next_t = syls[idx+1].time if idx+1<n else line.end
                if syl.time <= elapsed < next_t:
                    dur = next_t - syl.time
                    syl.target_progress = min(1.0,(elapsed-syl.time)/dur) if dur>0 else 1.0
                else:
                    syl.target_progress = 1.0
            else:
                syl.target_progress = 0.0
            syl.progress += (syl.target_progress-syl.progress)*min(1.0,dt*ANIMATION_SPEED)
            syl.progress = max(0.0,min(1.0,syl.progress))


    def _draw_solid_bg(self, surf, pill_rect, alpha):
        """Draw the solid color lyric background (original behavior)."""
        base_opacity = getattr(self.settings, "lyric_bg_opacity", 140)
        pill_alpha = int(base_opacity * alpha / 255)
        if pill_alpha <= 0:
            return
        bg_col = getattr(self.settings, "lyric_bg_color", (0, 0, 0))
        raw_radius = getattr(self.settings, "lyric_bg_radius", -1)
        corner_r = (pill_rect.height // 2) if raw_radius < 0 else max(0, raw_radius)
        ps = pygame.Surface((pill_rect.width, pill_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(ps, (*bg_col[:3], pill_alpha), ps.get_rect(), border_radius=corner_r)
        surf.blit(ps, pill_rect.topleft)


    def _blit_bg_with_pulse(self, surf, bg_surf, size, dt=0.016):
        s = self.settings
        if not getattr(s,"bg_pulse_enabled",False):
            surf.blit(bg_surf,(0,0)); return
        freq_low    = max(1,int(getattr(s,"bg_pulse_freq_low",20)))
        freq_high   = max(freq_low+1,int(getattr(s,"bg_pulse_freq_high",200)))
        threshold   = max(0,min(100,int(getattr(s,"bg_pulse_threshold",10))))/100.0
        oscillation = max(0,min(100,int(getattr(s,"bg_pulse_oscillation",40))))/100.0
        initial_zoom= max(0,min(30, int(getattr(s,"bg_pulse_initial_zoom",0))))/100.0
        zoom_level  = max(0,min(60, int(getattr(s,"bg_pulse_zoom_level",20))))/100.0
        spectrum = getattr(self,"_pulse_spectrum",None)
        rate     = getattr(self,"_pulse_spectrum_rate",44100)
        n_bins   = getattr(self,"_pulse_spectrum_bins",1)
        if spectrum is not None and n_bins>1:
            bin_lo=max(0,int(freq_low*2*(n_bins-1)/rate))
            bin_hi=min(n_bins-1,int(freq_high*2*(n_bins-1)/rate))
            if bin_hi<=bin_lo: bin_hi=min(n_bins-1,bin_lo+1)
            raw_energy=float(spectrum[bin_lo:bin_hi+1].mean()) if bin_hi>=bin_lo else 0.0
        else:
            raw_energy=getattr(self,"_raw_bass_energy",0.0)
        if raw_energy<=0.0:
            self._bg_pulse_level=0.0; self._pulse_peak=1e-6
            zoom=1.0+initial_zoom
            if zoom<=1.001: surf.blit(bg_surf,(0,0)); return
            sw,sh=size; bw=max(sw,int(sw*zoom)); bh=max(sh,int(sh*zoom))
            sc=pygame.transform.smoothscale(bg_surf,(bw,bh))
            surf.blit(sc,(0,0),area=pygame.Rect((bw-sw)//2,(bh-sh)//2,sw,sh)); return
        pulse_peak=getattr(self,"_pulse_peak",raw_energy)
        if raw_energy>pulse_peak: pulse_peak=raw_energy
        else: pulse_peak*=math.exp(-dt/4.0)
        self._pulse_peak=max(pulse_peak,1e-6)
        raw_level=min(1.0,raw_energy/self._pulse_peak)
        gated_level=0.0 if raw_level<threshold else (raw_level-threshold)/max(1e-6,1.0-threshold)
        attack_tc=0.030; release_tc=0.06+oscillation*0.74
        ab=1.0-math.exp(-dt/attack_tc); rb=1.0-math.exp(-dt/release_tc)
        if gated_level>=self._bg_pulse_level: self._bg_pulse_level+=(gated_level-self._bg_pulse_level)*ab
        else: self._bg_pulse_level+=(gated_level-self._bg_pulse_level)*rb
        self._bg_pulse_level=max(0.0,min(1.0,self._bg_pulse_level))
        if self._bg_pulse_level<0.01: self._bg_pulse_level=0.0
        zoom=1.0+initial_zoom+zoom_level*self._bg_pulse_level
        sw,sh=size
        if zoom<=1.001: surf.blit(bg_surf,(0,0)); return
        bw=max(sw,int(sw*zoom)); bh=max(sh,int(sh*zoom))
        sc=pygame.transform.smoothscale(bg_surf,(bw,bh))
        surf.blit(sc,(0,0),area=pygame.Rect((bw-sw)//2,(bh-sh)//2,sw,sh))

    def _draw_snow(self, surf, dt):
        import random as _r
        s=self.settings
        count=max(0,min(2000,getattr(s,"snow_count",120)))
        speed=max(1,min(100,getattr(s,"snow_speed",40)))/100.0
        radius=max(1,min(20,getattr(s,"snow_size",4)))
        opacity=max(0,min(255,getattr(s,"snow_opacity",180)))
        wind=max(-50,min(50,getattr(s,"snow_wind",0)))/100.0
        sw,sh=surf.get_size()
        cur=len(self._snowflakes)
        if cur<count:
            for _ in range(count-cur):
                self._snowflakes.append([_r.uniform(0,sw),_r.uniform(-sh,sh),
                                         _r.uniform(0.7,1.4),_r.uniform(0,math.tau),_r.uniform(0.3,1.2)])
        elif cur>count: self._snowflakes=self._snowflakes[:count]
        if self._snow_surf_size!=(sw,sh) or self._snow_surface is None:
            self._snow_surface=pygame.Surface((sw,sh),pygame.SRCALPHA)
            self._snow_surf_size=(sw,sh)
            for f in self._snowflakes: f[0]=_r.uniform(0,sw); f[1]=_r.uniform(0,sh)
        snow_surf=self._snow_surface; snow_surf.fill((0,0,0,0))
        base=sh*0.12*speed
        for f in self._snowflakes:
            fx,fy,sp,wp,wa=f
            fy+=base*sp*dt; wp+=dt*1.4*sp; fx+=math.sin(wp)*wa*dt*60+wind*base*dt*0.3
            if fy>sh+radius: fy=-radius; fx=_r.uniform(0,sw); wp=_r.uniform(0,math.tau)
            if fx<-radius: fx=sw+radius
            elif fx>sw+radius: fx=-radius
            f[0]=fx; f[1]=fy; f[3]=wp
            ix,iy=int(fx),int(fy)
            if -radius<=ix<=sw+radius and -radius<=iy<=sh+radius:
                pygame.draw.circle(snow_surf,(255,255,255,opacity//3),(ix,iy),radius)
                pygame.draw.circle(snow_surf,(255,255,255,opacity),(ix,iy),max(1,radius-1))
        surf.blit(snow_surf,(0,0))

    def _get_heart_shape(self):
        """Cached normalized heart-outline points (FontAwesome-style curve),
        centered at origin, point facing down."""
        if getattr(self, "_heart_curve_pts", None) is None:
            pts = []
            N = 48
            for i in range(N):
                t = (i / N) * math.tau
                x = 16 * math.sin(t) ** 3
                y = 13*math.cos(t) - 5*math.cos(2*t) - 2*math.cos(3*t) - math.cos(4*t)
                pts.append((x, y))
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            minx, maxx = min(xs), max(xs); miny, maxy = min(ys), max(ys)
            w = maxx - minx; h = maxy - miny
            self._heart_curve_pts = [((x-minx)/w - 0.5, -((y-miny)/h - 0.5)) for x, y in pts]
        return self._heart_curve_pts


    def _load_heart_svg_template(self, path):
        """Rasterize an SVG once into a high-res pygame surface — keeps BOTH
        the original RGBA (SVG's own colors) and a white+alpha stencil (for
        tinting), so callers can pick either without re-rasterizing."""
        if getattr(self, "_heart_svg_cache_path", None) == path:
            return getattr(self, "_heart_svg_template", None)
        self._heart_svg_cache_path = path
        self._heart_svg_template  = None   # white+alpha stencil (for tinting)
        self._heart_svg_original  = None   # SVG's native colors, alpha intact
        if not path or not os.path.exists(path):
            return None
        try:
            from PyQt6.QtSvg import QSvgRenderer
            from PyQt6.QtGui import QImage, QPainter
            base = 256   # render resolution; downscaled per-heart later
            img = QImage(base, base, QImage.Format.Format_RGBA8888)
            img.fill(0)
            renderer = QSvgRenderer(path)
            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            renderer.render(painter)
            painter.end()
            buf = img.constBits()
            buf.setsize(img.sizeInBytes())
            arr = np.frombuffer(bytes(buf), dtype=np.uint8).reshape((base, base, 4)).copy()

            # ── native-color version (unmodified RGBA straight from the SVG) ──
            orig = pygame.Surface((base, base), pygame.SRCALPHA)
            opx = pygame.surfarray.pixels3d(orig)
            opx[:, :, :] = arr[:, :, :3].swapaxes(0, 1)
            del opx
            opa = pygame.surfarray.pixels_alpha(orig)
            opa[:, :] = arr[:, :, 3].swapaxes(0, 1)
            del opa
            self._heart_svg_original = orig

            # ── white+alpha stencil version (for color-overlay tinting) ──────
            stencil = pygame.Surface((base, base), pygame.SRCALPHA)
            spx = pygame.surfarray.pixels3d(stencil)
            spx[:, :, :] = 255
            del spx
            spa = pygame.surfarray.pixels_alpha(stencil)
            spa[:, :] = arr[:, :, 3].swapaxes(0, 1)
            del spa
            self._heart_svg_template = stencil

            self._heart_svg_error = None
        except Exception as e:
            self._heart_svg_error = f"{path}: {e}"
            print(f"[Hearts] SVG load failed ({path}): {e}")
        return self._heart_svg_template

    def _tinted_heart_template(self, path, color, overlay=True):
        """Return the heart template to draw with. If overlay is True, recolor
        the white stencil to `color` (cached per color). If False, return the
        SVG's own native colors untouched — useful for comparing whether the
        color-overlay step is degrading a multi-color / gradient SVG."""
        self._load_heart_svg_template(path)   # ensures both caches are populated
        if not overlay:
            return getattr(self, "_heart_svg_original", None)
        template = self._heart_svg_template
        if template is None:
            return None
        key = (path, color)
        if getattr(self, "_heart_tint_key", None) == key:
            return self._heart_tinted
        tinted = template.copy()
        px = pygame.surfarray.pixels3d(tinted)
        px[:, :, 0] = color[0]; px[:, :, 1] = color[1]; px[:, :, 2] = color[2]
        del px
        self._heart_tinted = tinted
        self._heart_tint_key = key
        return tinted

    def _draw_hearts(self, surf, dt):
        import random as _r
        s=self.settings
        count=max(0,min(500,getattr(s,"hearts_count",40)))
        speed=max(1,min(100,getattr(s,"hearts_speed",35)))/100.0
        mn=max(4,min(80,getattr(s,"hearts_min_size",12)))
        mx=max(4,min(80,getattr(s,"hearts_max_size",32)))
        if mx<mn: mx=mn
        opacity=max(0,min(255,getattr(s,"hearts_opacity",200)))
        hr=getattr(s,"hearts_color_r",255); hg=getattr(s,"hearts_color_g",80); hb=getattr(s,"hearts_color_b",120)
        sw,sh=surf.get_size(); base=sh*0.10*speed
        GROW_TIME = 1.2

        svg_path = getattr(s, "hearts_svg_path", None)
        overlay  = getattr(s, "hearts_color_overlay", True)
        heart_template = self._tinted_heart_template(svg_path, (hr, hg, hb), overlay) if svg_path else None

        cur=len(self._hearts)
        if cur<count:
            for _ in range(count-cur):
                self._hearts.append([_r.uniform(0,sw),_r.uniform(-sh,sh),
                                    _r.uniform(mn,mx),_r.uniform(0.7,1.3),
                                    _r.uniform(0,math.tau),_r.uniform(8,25),
                                    _r.uniform(-0.3,0.3),_r.uniform(0,math.tau),
                                    0.0, _r.uniform(0,math.tau), _r.uniform(0.5,1.6)])
        elif cur>count: self._hearts=self._hearts[:count]
        if self._hearts_surf_size!=(sw,sh) or self._hearts_surface is None:
            self._hearts_surface=pygame.Surface((sw,sh),pygame.SRCALPHA)
            self._hearts_surf_size=(sw,sh)
            for h in self._hearts: h[0]=_r.uniform(0,sw); h[1]=_r.uniform(0,sh)
        hsurf=self._hearts_surface; hsurf.fill((0,0,0,0))

        def _heart_outline(surface,cx,cy,r,color):
            # fallback shape if no SVG is set — outline only, not filled
            if r<2: pygame.draw.circle(surface,color,(int(cx),int(cy)),max(1,int(r))); return
            hr2=r*0.5; ly=cy-hr2*0.5
            pygame.draw.circle(surface,color,(int(cx-hr2),int(ly)),int(hr2+0.5),width=2)
            pygame.draw.circle(surface,color,(int(cx+hr2),int(ly)),int(hr2+0.5),width=2)
            pygame.draw.polygon(surface,color,
                [(int(cx-r),int(ly+hr2*0.3)),(int(cx+r),int(ly+hr2*0.3)),(int(cx),int(cy+r*0.95))],width=2)

        for h in self._hearts:
            hx,hy,sz,sp,swp,swa,spd,ang,age,fph,fsp = h
            hy+=base*sp*dt; swp+=dt*1.2*sp; hx+=math.sin(swp)*swa*dt; ang+=spd*dt
            age += dt
            if hy>sh+sz:
                hy=-sz; hx=_r.uniform(0,sw); swp=_r.uniform(0,math.tau)
                sz=_r.uniform(mn,mx); age=0.0
                fph=_r.uniform(0,math.tau); fsp=_r.uniform(0.5,1.6)
            if hx<-sz: hx=sw+sz
            elif hx>sw+sz: hx=-sz
            h[0]=hx; h[1]=hy; h[2]=sz; h[4]=swp; h[7]=ang%math.tau
            h[8]=age; h[9]=fph; h[10]=fsp

            grow_t = min(1.0, age/GROW_TIME); grow_t = 1.0-(1.0-grow_t)**3
            cur_size = sz*grow_t
            if cur_size < 1: continue

            fade_wave = 0.4 + 0.6*(0.5+0.5*math.sin(age*fsp+fph))
            alpha_here = max(0, min(255, int(opacity*fade_wave*grow_t)))
            if alpha_here <= 2: continue

            ix,iy=int(hx),int(hy)
            if not (-sz*2<=ix<=sw+sz*2 and -sz*2<=iy<=sh+sz*2): continue
            d=int(cur_size*2.4)
            if d<3: continue

            if heart_template is not None:
                # rotozoom scales+rotates in one smoothly-filtered pass straight
                # from the high-res template — avoids the jagged/aliased edges
                # that pygame.transform.rotate() leaves when applied after a
                # separate (unfiltered-on-output) scale step.
                template_size = heart_template.get_width()
                zoom = d / template_size
                rot = pygame.transform.rotozoom(heart_template, math.degrees(ang), zoom)
                rot.set_alpha(alpha_here)
            else:
                tmp=pygame.Surface((d,d),pygame.SRCALPHA)
                _heart_outline(tmp,d//2,d//2,cur_size,(hr,hg,hb,alpha_here))
                rot=pygame.transform.rotozoom(tmp,math.degrees(ang),1.0)

            rw,rh=rot.get_size(); hsurf.blit(rot,(ix-rw//2,iy-rh//2))
        surf.blit(hsurf,(0,0))
    
    def _beam_angle(self, idx, n, t, base_omega, max_angle, pattern):
        """Return a coordinated angle for organized movement patterns, or
        None to signal the caller should fall back to the independent
        per-beam random-bounce behavior."""
        if pattern == "sync":
            # All beams swing together like one big searchlight.
            return max_angle * math.sin(t * base_omega)
        elif pattern == "wave":
            # Phase-offset by beam index -> a wave rolls across the row.
            phase = (idx / max(1, n)) * math.tau
            return max_angle * math.sin(t * base_omega + phase)
        elif pattern == "alternate":
            # Even/odd beams mirror each other -> criss-cross fan.
            sign = 1 if idx % 2 == 0 else -1
            return sign * max_angle * math.sin(t * base_omega)
        elif pattern == "converge":
            # Phase driven by distance-from-center -> ripples in/out from
            # the middle of the row (breathing fan effect).
            center_dist = abs(idx - (n - 1) / 2) / max(1.0, (n - 1) / 2)
            phase = center_dist * math.pi
            return max_angle * math.sin(t * base_omega + phase)
        elif pattern == "chase":
            # Only a moving window of beams is "active" (swinging); the
            # rest sit near center, giving a chasing marquee look.
            window = max(1, n // 4)
            pos = (t * base_omega * 1.2) % math.tau
            beam_pos = (idx / max(1, n)) * math.tau
            d = (beam_pos - pos) % math.tau
            if d > math.pi: d = math.tau - d
            active = max(0.0, 1.0 - d / (math.pi / max(1, (n / max(1, window)))))
            return max_angle * active * math.sin(t * base_omega * 1.2)
        elif pattern == "spiral":
            # Higher spatial frequency than "wave" -> several crests ripple
            # across the row at once, like a twisting spiral sweep.
            phase = (idx / max(1, n)) * math.tau * 3
            return max_angle * math.sin(t * base_omega * 1.4 + phase)
        elif pattern == "figure8":
            # Two combined frequencies per beam -> a wandering, looping
            # figure-eight-style sweep instead of a plain back-and-forth.
            return max_angle * (0.6 * math.sin(t * base_omega) +
                                 0.4 * math.sin(2 * t * base_omega + idx * 0.35))
        elif pattern == "pulse":
            # Snap to a new pseudo-random angle at a fixed interval, giving
            # a strobe-like jump-cut positioning rather than smooth motion.
            speed_norm = base_omega / math.radians(25)
            period = max(0.15, 0.6 / max(0.2, speed_norm))
            step = int(t / period)
            seed = (idx * 97 + step * 131) * 12.9898
            rnd = (math.sin(seed) * 43758.5453) % 1.0
            return max_angle * (rnd * 2.0 - 1.0)
        return None  # "random" (or unrecognized) -> caller keeps old behavior

    def _advance_lights_shuffle(self, dt):
        """Cycle through the coordinated patterns on a timer for the
        'shuffle' preset, so the light show keeps changing on its own."""
        import random as _r
        self._lights_shuffle_timer = getattr(self, "_lights_shuffle_timer", 0.0) + dt
        interval = getattr(self, "_lights_shuffle_interval", 0.0)
        current = getattr(self, "_lights_shuffle_current", None)
        if current is None or self._lights_shuffle_timer >= interval:
            self._lights_shuffle_timer = 0.0
            self._lights_shuffle_interval = _r.uniform(5.0, 10.0)
            choices = [p for p in LIGHTS_PATTERNS if p != "shuffle"]
            new_choice = _r.choice(choices)
            tries = 0
            while new_choice == current and tries < 5:
                new_choice = _r.choice(choices); tries += 1
            self._lights_shuffle_current = new_choice
            current = new_choice
        return current

    def _draw_lights(self, surf, dt):
        import random as _r
        s=self.settings
        count=max(1,min(30,getattr(s,"lights_count",6)))
        speed=max(1,min(200,getattr(s,"lights_speed",40)))/100.0
        opacity=max(0,min(255,getattr(s,"lights_opacity",80)))
        width_deg=max(1,min(60,getattr(s,"lights_width",40)))
        length_p=max(10,min(150,getattr(s,"lights_length",80)))/100.0
        rainbow=getattr(s,"lights_rainbow",True); reactive=getattr(s,"lights_reactive",True)
        sw,sh=surf.get_size()
        bands=getattr(self,"pcm_bands",None); raw_bass=0.0
        if bands:
            cutoff=max(1,len(bands)//6); raw_bass=sum(bands[:cutoff])/cutoff
        if reactive:
            if raw_bass>=self._lights_bass_level:
                self._lights_bass_level+=(raw_bass-self._lights_bass_level)*(1.0-math.exp(-dt/0.05))
            else:
                self._lights_bass_level+=(raw_bass-self._lights_bass_level)*(1.0-math.exp(-dt/0.40))
            self._lights_bass_level=max(0.0,min(1.0,self._lights_bass_level))
        else: self._lights_bass_level=0.0
        do_pulse=getattr(s,"lights_pulse",True)
        pulse_sens=max(0,min(100,getattr(s,"lights_pulse_sens",60)))/100.0
        raw_energy=getattr(self,"_raw_bass_energy",0.0)
        env_a=1.0-math.exp(-dt/0.08); env_r=1.0-math.exp(-dt/0.60)
        if raw_energy>self._lights_beat_prev: self._lights_beat_prev+=(raw_energy-self._lights_beat_prev)*env_a
        else: self._lights_beat_prev+=(raw_energy-self._lights_beat_prev)*env_r
        envelope=max(self._lights_beat_prev,1e-6)
        if do_pulse and raw_energy>0:
            ratio_needed=1.80-pulse_sens*0.65
            if raw_energy>envelope*ratio_needed: self._lights_beat_level=1.0
        self._lights_beat_level*=math.exp(-dt/0.050)
        self._lights_beat_level=max(0.0,self._lights_beat_level)
        bass=self._lights_bass_level; beat=self._lights_beat_level
        pattern=getattr(s,"lights_pattern","random")
        if pattern == "shuffle":
            pattern = self._advance_lights_shuffle(dt)
        self._lights_t += dt
        cur=len(self._lights)
        if cur<count:
            for i in range(count-cur):
                self._lights.append([0.0, _r.uniform(-math.pi*0.28,math.pi*0.28),
                                    _r.choice([-1,1]), _r.uniform(0.5,1.5),
                                    _r.uniform(0.0,1.0), _r.uniform(0.03,0.12)])
        elif cur>count:
            self._lights=self._lights[:count]

        # Redistribute ALL anchor x-positions evenly whenever count/width changes
        if getattr(self, "_lights_last_count", None) != count or getattr(self, "_lights_last_sw", None) != sw:
            n = len(self._lights)
            for idx, beam in enumerate(self._lights):
                ax = sw * (idx + 0.5 + _r.uniform(-0.15, 0.15)) / max(1, n)
                beam[0] = max(0, min(sw, ax))
            self._lights_last_count = count
            self._lights_last_sw = sw
        if self._lights_surf_size!=(sw,sh) or self._lights_surface is None:
            self._lights_surface=pygame.Surface((sw,sh),pygame.SRCALPHA)
            self._lights_surf_size=(sw,sh)
        lsurf=self._lights_surface; lsurf.fill((0,0,0,0))
        max_angle=math.radians(70); base_omega=math.radians(25)*speed
        beam_length=sh*length_p
        NEON=getattr(s,"lights_neon_glow",True)
        SEGMENTS = 24 if NEON else 6   # more segments = smoother continuous falloff
        n_beams=len(self._lights)
        for idx,beam in enumerate(self._lights):
            ax,angle,direction,sp_mult,hue,hue_spd=beam
            coordinated=self._beam_angle(idx,n_beams,self._lights_t,base_omega,max_angle,pattern)
            if coordinated is not None:
                angle=coordinated
            else:
                noise=_r.uniform(-0.08,0.08)*math.radians(3)*max(dt*60,0.0)
                angle+=direction*base_omega*sp_mult*dt+noise
                if angle>max_angle: angle=max_angle; direction=-1
                elif angle<-max_angle: angle=-max_angle; direction=1
            if rainbow: hue=(hue+hue_spd*dt)%1.0
            beam[1]=angle; beam[2]=direction; beam[4]=hue
            if rainbow:
                r_f,g_f,b_f=colorsys.hsv_to_rgb(hue,0.85,1.0)
                br,bg,bb=int(r_f*255),int(g_f*255),int(b_f*255)
            else: br,bg,bb=255,255,200
            strobe_mult=(1.0+beat*4.0) if do_pulse else 1.0
            base_glow=(0.30+bass*0.40) if reactive else 0.50
            reactive_boost=base_glow*strobe_mult
            width_factor=(1.0+bass*0.35) if reactive else 1.0
            sin_a=math.sin(angle); cos_a=math.cos(angle)
            tip_x=ax+beam_length*sin_a; tip_y=sh-beam_length*cos_a
            tip_hw=sw*(width_deg/180.0)*width_factor; anchor_hw=tip_hw*0.04
            perp_x=cos_a; perp_y=sin_a
            for li in range(SEGMENTS,0,-1):
                t0=(SEGMENTS-li)/SEGMENTS; t1=(SEGMENTS-li+1)/SEGMENTS
                la=int(opacity*reactive_boost*(1.0-t0**0.5)); la=max(0,min(255,la))
                if la==0: continue
                hw_near=anchor_hw+(tip_hw-anchor_hw)*t0; hw_far=anchor_hw+(tip_hw-anchor_hw)*t1
                nx=ax+beam_length*sin_a*t0; ny=sh-beam_length*cos_a*t0
                fx2=ax+beam_length*sin_a*t1; fy2=sh-beam_length*cos_a*t1
                strip=[(int(nx+perp_x*hw_near),int(ny+perp_y*hw_near)),
                    (int(nx-perp_x*hw_near),int(ny-perp_y*hw_near)),
                    (int(fx2-perp_x*hw_far),int(fy2-perp_y*hw_far)),
                    (int(fx2+perp_x*hw_far),int(fy2+perp_y*hw_far))]
                pygame.draw.polygon(lsurf,(br,bg,bb,la),strip)
            spot_a=min(255,int(opacity*reactive_boost*2.0))
            pygame.draw.circle(lsurf,(br,bg,bb,spot_a),(int(ax),sh),3)

        if NEON:
            glow_r = max(0, int(round(getattr(s,"lights_glow_radius",8))))
            if glow_r > 0:
                try:
                    from PIL import Image, ImageFilter
                    # Blurring the full-res canvas with PIL every frame is the
                    # actual cause of the sluggish/laggy beam motion — it's a
                    # heavy per-pixel operation running at 60fps. Downscaling
                    # before the blur (and scaling the blurred result back up)
                    # cuts that cost roughly by the square of the scale factor
                    # while looking nearly identical, since blur output is
                    # already soft/low-frequency.
                    DS = 0.35
                    dw = max(1, int(sw * DS)); dh = max(1, int(sh * DS))
                    small = pygame.transform.smoothscale(lsurf, (dw, dh))
                    pil_img = Image.frombytes("RGBA", (dw, dh), pygame.image.tostring(small, "RGBA"))
                    blur_radius = max(1.0, glow_r * DS)
                    blurred = pil_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
                    glow_small = pygame.image.fromstring(blurred.tobytes(), blurred.size, "RGBA")
                    glow_surf = pygame.transform.smoothscale(glow_small, (sw, sh))
                    # Soft halo underneath, additive for that neon "bloom"
                    surf.blit(glow_surf, (0,0), special_flags=pygame.BLEND_RGBA_ADD)
                except Exception as e:
                    print(f"[Lights] glow blur error: {e}")
            # Crisp core on top
            surf.blit(lsurf,(0,0))
        else:
            surf.blit(lsurf,(0,0))

    def _draw_visualizer(self, surf, scale):
        bands=getattr(self,"pcm_bands",None)
        if not bands: return
        s=self.settings; sw,sh=surf.get_size()
        max_h=max(10,int(getattr(s,"visualizer_height",120)*scale))
        opacity=int(getattr(s,"visualizer_opacity",200))
        color=getattr(s,"visualizer_color",(80,200,255))
        style=getattr(s,"visualizer_style","bars"); n=len(bands)
        viz=pygame.Surface((sw,max_h),pygame.SRCALPHA)
        if style=="wave":
            pts=[(int(i/max(1,n-1)*sw),max_h-int(v*max_h)) for i,v in enumerate(bands)]
            if len(pts)>=2:
                pygame.draw.polygon(viz,(*color[:3],int(opacity*0.35)),pts+[(sw,max_h),(0,max_h)])
                pygame.draw.lines(viz,(*color[:3],opacity),False,pts,max(2,int(3*scale)))
        else:
            gap=max(1,int(2*scale)); bar_w=max(1,(sw-gap*(n-1))/n); mirror=(style=="mirror_bars")
            for i,v in enumerate(bands):
                bar_h=max(2,int(v*max_h)); x=int(i*(bar_w+gap))
                rect=pygame.Rect(x,(max_h//2-bar_h//2) if mirror else (max_h-bar_h),int(bar_w),bar_h)
                pygame.draw.rect(viz,(*color[:3],opacity),rect,border_radius=max(1,int(bar_w*0.3)))
        surf.blit(viz,(0,sh-max_h))

    def _draw_startup_info(self, surf, elapsed, scale):
        s=self.settings
        duration=getattr(s,"startup_info_duration",4.0)
        if duration>20: duration/=10.0
        delay_raw=getattr(s,"startup_info_delay",0); delay=delay_raw/10.0 if delay_raw>0 else 0.0
        eff=elapsed-delay
        if eff<0: return
        SLIDE_IN=0.45; SLIDE_OUT=0.45; fade_out=min(0.8,duration*0.2)
        if eff>duration: return
        if eff<SLIDE_IN: alpha=int(255*(eff/SLIDE_IN))
        elif eff<duration-fade_out: alpha=255
        else: alpha=max(0,int(255*(1.0-(eff-(duration-fade_out))/max(fade_out,0.001))))
        if alpha<=0: return
        sw,sh=surf.get_size()
        ox=int(getattr(s,"startup_info_offset_x",0)*scale)
        oy=int(getattr(s,"startup_info_offset_y",0)*scale)
        title =(getattr(s,"startup_info_title","") or getattr(s,"_lrc_meta_title","") or "").strip()
        artist=(getattr(s,"startup_info_artist","") or getattr(s,"_lrc_meta_artist","") or "").strip()
        if not title and not artist: return
        tfs=max(12,int(48*scale)); afs=max(10,int(32*scale))
        tf=make_font(s.font_path,tfs); af=make_font(s.font_path,afs)
        ph=int(32*scale); pv=int(24*scale); gap=int(12*scale)
        ts=tf.render(title,True,(255,255,255)) if title else None
        as2=af.render(artist,True,(200,200,220)) if artist else None
        tw=max((ts.get_width() if ts else 0),(as2.get_width() if as2 else 0))
        th=((ts.get_height() if ts else 0)+(as2.get_height() if as2 else 0)+(gap if ts and as2 else 0))
        cw=tw+ph*2; ch=th+pv*2
        cx=sw//2+ox; cy_c=sh//2+oy
        direction=getattr(s,"startup_info_direction","top")
        def _ease(t2): return 1.0-(1.0-t2)**3
        t_in=_ease(eff/SLIDE_IN) if eff<SLIDE_IN else 1.0
        t_out=_ease((eff-(duration-SLIDE_OUT))/SLIDE_OUT) if eff>duration-SLIDE_OUT else 0.0
        if direction=="top":
            travel=cy_c-ch//2+ch; sx=0; sy=int(-travel*(1.0-t_in)+travel*t_out)
        elif direction=="bottom":
            travel=sh-(cy_c-ch//2); sx=0; sy=int(travel*(1.0-t_in)-travel*t_out)
        elif direction=="left":
            travel=cx-cw//2+cw; sx=int(-travel*(1.0-t_in)+travel*t_out); sy=0
        else:
            travel=sw-(cx-cw//2); sx=int(travel*(1.0-t_in)-travel*t_out); sy=0
        card_rect=pygame.Rect(cx-cw//2+sx,cy_c-ch//2+sy,cw,ch)
        card=pygame.Surface((cw,ch),pygame.SRCALPHA)
        radius=int(16*scale)
        pygame.draw.rect(card,(0,0,0,200),card.get_rect(),border_radius=radius)
        ty2=pv
        if ts: card.blit(ts,(cw//2-ts.get_width()//2,ty2)); ty2+=ts.get_height()+gap
        if as2: card.blit(as2,(cw//2-as2.get_width()//2,ty2))
        if getattr(s,"startup_info_neon_enabled",True):
            nc=getattr(s,"startup_info_neon_color",(0,200,255))
            nw=max(1,int(getattr(s,"startup_info_neon_width",3)*scale))
            hue_s=(elapsed*0.3)%1.0
            bh,bs,bv=colorsys.rgb_to_hsv(nc[0]/255,nc[1]/255,nc[2]/255)
            nr2,ng2,nb2=colorsys.hsv_to_rgb((bh+hue_s*0.15)%1.0,bs,bv)
            neon=(int(nr2*255),int(ng2*255),int(nb2*255))
            pulse=0.8+0.2*math.sin(elapsed*math.pi*2.5)
            na=max(0,min(255,int(alpha*pulse)))
            for layer in range(3,0,-1):
                la=int(na*(layer/3)**1.5); lw=nw+(3-layer)*2
                bs2=pygame.Surface((cw+lw*2,ch+lw*2),pygame.SRCALPHA)
                pygame.draw.rect(bs2,(*neon,la),bs2.get_rect(),border_radius=radius+lw,width=lw)
                surf.blit(bs2,(card_rect.x-lw,card_rect.y-lw))
        card.set_alpha(alpha); surf.blit(card,card_rect.topleft)

    def _draw_line_with_animation(self, surf, line, font, sw, y,
                                color_sung, color_next,
                                cx_offset=0, alpha=255, is_active=True, scale=1.0):
        syls = line.syllables
        if not syls:
            return
        parts = [(s.time, s.text, s.progress) for s in syls]
        total_w = sum(font.size(t)[0] for _, t, _ in parts)
        cx = sw // 2 + cx_offset
        x = cx - total_w // 2
        pad = max(8, int(20 * scale)) + getattr(self.settings, "lyric_bg_pad_extra", 0)
        ph = font.get_linesize() + max(6, int(12 * scale)) + getattr(self.settings, "lyric_bg_height_extra", 0)
        pill_rect = pygame.Rect(x - pad, y - int(5 * scale), total_w + pad * 2, ph)

        # ─── Lyric BG Image ──────────────────────────────────────────────────
        bg_img_path = getattr(self.settings, "lyric_bg_image_path", None)
        if bg_img_path and os.path.exists(bg_img_path):
            try:
                from PIL import Image
                # Cache key includes path and dimensions
                cache_key = (bg_img_path, pill_rect.width, pill_rect.height)
                if not hasattr(self, "_lyric_bg_cache"):
                    self._lyric_bg_cache = {}
                if cache_key not in self._lyric_bg_cache:
                    img = Image.open(bg_img_path).convert("RGBA")
                    mode = getattr(self.settings, "lyric_bg_image_mode", "tile")
                    if mode == "stretch":
                        img = img.resize((pill_rect.width, pill_rect.height), Image.BICUBIC)
                    elif mode == "fit":
                        # Fit preserving aspect ratio
                        img.thumbnail((pill_rect.width, pill_rect.height), Image.BICUBIC)
                        # Center it
                        new_img = Image.new("RGBA", (pill_rect.width, pill_rect.height), (0, 0, 0, 0))
                        offset_x = (pill_rect.width - img.width) // 2
                        offset_y = (pill_rect.height - img.height) // 2
                        new_img.paste(img, (offset_x, offset_y))
                        img = new_img
                    # tile mode: keep original size, will tile below
                    self._lyric_bg_cache[cache_key] = img
                else:
                    img = self._lyric_bg_cache[cache_key]

                # Create pygame surface from PIL image
                mode = getattr(self.settings, "lyric_bg_image_mode", "tile")
                if mode == "tile":
                    # Tile the image across the pill rect
                    tw, th = img.size
                    bg_surf = pygame.Surface((pill_rect.width, pill_rect.height), pygame.SRCALPHA)
                    for tx in range(0, pill_rect.width, tw):
                        for ty in range(0, pill_rect.height, th):
                            tile = pygame.image.fromstring(img.tobytes(), img.size, "RGBA")
                            bg_surf.blit(tile, (tx, ty))
                else:
                    bg_surf = pygame.image.fromstring(img.tobytes(), img.size, "RGBA")
                    if bg_surf.get_size() != (pill_rect.width, pill_rect.height):
                        bg_surf = pygame.transform.smoothscale(bg_surf, (pill_rect.width, pill_rect.height))

                # Apply opacity
                opacity = getattr(self.settings, "lyric_bg_image_opacity", 180)
                bg_surf.set_alpha(int(opacity * alpha / 255))
                
                # Mask to pill shape (rounded rect)
                raw_radius = getattr(self.settings, "lyric_bg_radius", -1)
                corner_r = (pill_rect.height // 2) if raw_radius < 0 else max(0, raw_radius)
                mask = pygame.Surface((pill_rect.width, pill_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=corner_r)
                bg_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                surf.blit(bg_surf, pill_rect.topleft)
            except Exception as e:
                print(f"[Lyric BG] Error: {e}")
                # Fall back to solid color
                self._draw_solid_bg(surf, pill_rect, alpha)
        else:
            # ─── Solid color background ──────────────────────────────────────
            self._draw_solid_bg(surf, pill_rect, alpha)

        # ─── Render lyrics ──────────────────────────────────────────────────
        line_surf = pygame.Surface((total_w + pad * 2, ph), pygame.SRCALPHA)
        lx = pad
        style = getattr(self.settings, "lyric_style", "filled")
        stroke_w = max(0, int(round(getattr(self.settings, "stroke_width", 0) * scale)))
        shadow_off = max(0, int(round(getattr(self.settings, "shadow_offset", 2) * scale)))
        ty3 = max(2, int(5 * scale))

        def _shadow(tsurf, text, bx, by):
            if shadow_off <= 0:
                return
            sh2 = font.render(text, True, (0, 0, 0))
            sh2.set_alpha(160)
            tsurf.blit(sh2, (bx + shadow_off, by + shadow_off))

        def _stroke(tsurf, text, bx, by):
            if stroke_w <= 0:
                return
            sc2 = font.render(text, True, getattr(self.settings, "stroke_color", (0, 0, 0)))
            for sx in range(-stroke_w, stroke_w + 1):
                for sy2 in range(-stroke_w, stroke_w + 1):
                    if sx == 0 and sy2 == 0:
                        continue
                    if abs(sx) + abs(sy2) > stroke_w + max(1, stroke_w // 2):
                        continue
                    tsurf.blit(sc2, (bx + sx, by + sy2))

        for _, text, progress in parts:
            base_color = self._lerp_color(color_sung, color_next, progress) if is_active else color_next
            
            if style == "filled":
                _shadow(line_surf, text, lx, ty3)
                _stroke(line_surf, text, lx, ty3)
                line_surf.blit(font.render(text, True, base_color), (lx, ty3))
            elif style == "outline":
                _shadow(line_surf, text, lx, ty3)
                for ox2, oy2 in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
                    line_surf.blit(font.render(text, True, base_color), (lx + ox2 + 2, ty3 + oy2))
                line_surf.blit(font.render(text, True, (0, 0, 0, 0)), (lx + 2, ty3))
            elif style == "glow":
                _shadow(line_surf, text, lx, ty3)
                gc = tuple(min(255, int(c * 1.3)) for c in base_color)
                for ox2, oy2 in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, -2), (-2, 2), (2, 2)]:
                    g = font.render(text, True, (*gc[:3], 60))
                    line_surf.blit(g, (lx + ox2 + 2, ty3 + oy2))
                _stroke(line_surf, text, lx, ty3)
                core = font.render(text, True, (255, 255, 255))
                line_surf.blit(core, (lx + 2, ty3))
                tint = font.render(text, True, base_color)
                tint.set_alpha(160)
                line_surf.blit(tint, (lx + 2, ty3))
            elif style == "gradient":
                tc = tuple(min(255, int(c * 1.25)) for c in base_color)
                bc = tuple(max(0, int(c * 0.55)) for c in base_color)
                fh = font.get_linesize()
                half = fh // 2
                _shadow(line_surf, text, lx, ty3)
                _stroke(line_surf, text, lx, ty3)
                ts2 = font.render(text, True, tc)
                line_surf.blit(ts2, (lx, ty3), area=(0, 0, ts2.get_width(), half))
                bs3 = font.render(text, True, bc)
                line_surf.blit(bs3, (lx, ty3 + half), area=(0, half, bs3.get_width(), fh - half))
            lx += font.size(text)[0]

        # ─── GLOW EFFECT (smooth Gaussian blur) ──────────────────────────────
        glow_r = max(0, int(round(getattr(self.settings, "glow_radius", 0) * scale)))
        if glow_r > 0:
            # Get brightness and intensity multipliers
            brightness_factor = getattr(self.settings, "glow_brightness", 150) / 100.0
            intensity_factor = getattr(self.settings, "glow_intensity", 100) / 100.0

            # Determine glow color
            custom_glow = getattr(self.settings, "glow_color", None)
            if custom_glow and custom_glow != (0, 0, 0):
                glow_col = custom_glow
            else:
                mp = parts[len(parts) // 2][2] if parts else 0.0
                glow_col = tuple(min(255, int(c * 1.2)) for c in (self._lerp_color(color_sung, color_next, mp) if is_active else color_next))

            # Boost brightness
            glow_col_boosted = tuple(min(255, int(c * brightness_factor)) for c in glow_col)

            # Create a surface with only the text in boosted glow color
            glow_surf = pygame.Surface((total_w + pad * 2, ph), pygame.SRCALPHA)
            lx = pad
            for _, text, _ in parts:
                part_surf = font.render(text, True, glow_col_boosted)
                glow_surf.blit(part_surf, (lx, ty3))
                lx += font.size(text)[0]

            # Blur the glow using PIL
            try:
                from PIL import Image, ImageFilter
                pil_img = Image.frombytes("RGBA", glow_surf.get_size(), pygame.image.tostring(glow_surf, "RGBA"))
                glow_dist = max(1, getattr(self.settings, "glow_distance", 2))
                blur_radius = glow_r * 0.5 * glow_dist
                blurred = pil_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
                blurred_surf = pygame.image.fromstring(blurred.tobytes(), blurred.size, "RGBA")

                # Combine opacity and intensity (clamp to 0–255)
                base_opacity = self.settings.glow_opacity / 255.0
                glow_alpha = int(alpha * base_opacity * intensity_factor)
                glow_alpha = min(255, max(0, glow_alpha))
                blurred_surf.set_alpha(glow_alpha)

                surf.blit(blurred_surf, (x - pad, y - ty3))
            except Exception as e:
                print(f"[Glow] PIL blur error: {e}")

        # ─── Blit the main lyric surface on top ──────────────────────────
        line_surf.set_alpha(alpha)
        surf.blit(line_surf, (x - pad, y - ty3))

    def _draw_wipe_highlight(self, surf, line, font, sw, y, elapsed, alpha, scale, cx_offset=0):
        syls=line.syllables
        if not syls or elapsed<syls[0].time: return
        widths=[font.size(s.text)[0] for s in syls]; total_w=sum(widths)
        pad=max(8,int(20*scale)); cx=sw//2+cx_offset; x_left=cx-total_w//2
        ph=font.get_linesize()+max(6,int(12*scale)); y_pill=y-int(5*scale)
        pixel_offset=0.0
        for i,(syl,w) in enumerate(zip(syls,widths)):
            next_t=syls[i+1].time if i+1<len(syls) else line.end
            if elapsed>=next_t: pixel_offset+=w
            elif elapsed>=syl.time:
                dur=max(0.001,next_t-syl.time); pixel_offset+=w*min(1.0,(elapsed-syl.time)/dur); break
            else: break
        if pixel_offset<=0: return
        wipe_x=x_left+int(pixel_offset); wc=getattr(self.settings,"wipe_color",(255,255,255))
        wipe_alpha=int(alpha*0.55)
        if wipe_alpha<4: return
        beam_w=max(8,int(total_w*0.14))
        beam_surf=pygame.Surface((beam_w,ph),pygame.SRCALPHA)
        try:
            frac=np.linspace(0.0,1.0,beam_w,dtype=np.float32)
            alphas=(wipe_alpha*(frac**1.6)).astype(np.uint8)
            pixels=pygame.surfarray.pixels3d(beam_surf)
            pixels[:,:,0]=wc[0]; pixels[:,:,1]=wc[1]; pixels[:,:,2]=wc[2]; del pixels
            ap=pygame.surfarray.pixels_alpha(beam_surf)
            ap[:]=alphas[:,np.newaxis]; del ap
        except Exception:
            for bx in range(beam_w):
                a=int(wipe_alpha*(bx/beam_w)**1.6)
                pygame.draw.line(beam_surf,(*wc,a),(bx,0),(bx,ph-1))
        surf.blit(beam_surf,(wipe_x-beam_w,y_pill))
        es=pygame.Surface((3,ph),pygame.SRCALPHA); es.fill((*wc,min(255,int(alpha*0.92))))
        surf.blit(es,(wipe_x-1,y_pill))

    def _draw_countdown_bar(self, surf, line, font, sw, y, elapsed, alpha, scale, cx_offset=0, window_start=3.0):
        syls=line.syllables
        if not syls: return
        line_start=syls[0].time; bar_start=line_start-window_start
        if elapsed<bar_start or elapsed>=line_start: return
        t=(elapsed-bar_start)/window_start
        parts=[s.text for s in syls]; total_w=sum(font.size(txt)[0] for txt in parts)
        pad=max(8,int(20*scale)); cx=sw//2+cx_offset
        x_left=cx-total_w//2-pad; bar_w=total_w+pad*2
        bar_h=max(3,int(getattr(self.settings,"countdown_bar_height",5)*scale))
        bar_y=y-int(5*scale)-bar_h-max(2,int(4*scale))

        cs=getattr(self.settings,"countdown_bar_color_start",(255,80,80))
        ce=getattr(self.settings,"countdown_bar_color_end",(80,200,255))

        # ── Cache the full-width gradient surface; only rebuild it when the
        #    line, width, height, or colors actually change ──────────────
        cache_key = (line.start, bar_w, bar_h, tuple(cs), tuple(ce))
        if not hasattr(self, "_countdown_cache"):
            self._countdown_cache = {}
        cached = self._countdown_cache.get(cache_key)
        if cached is None:
            grad_surf = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
            try:
                frac=np.linspace(0.0,1.0,max(1,bar_w),dtype=np.float32)
                r_a=(cs[0]+(ce[0]-cs[0])*frac).clip(0,255).astype(np.uint8)
                g_a=(cs[1]+(ce[1]-cs[1])*frac).clip(0,255).astype(np.uint8)
                b_a=(cs[2]+(ce[2]-cs[2])*frac).clip(0,255).astype(np.uint8)
                pixels=pygame.surfarray.pixels3d(grad_surf)
                pixels[:,:,0]=r_a[:,np.newaxis]; pixels[:,:,1]=g_a[:,np.newaxis]; pixels[:,:,2]=b_a[:,np.newaxis]; del pixels
                ap=pygame.surfarray.pixels_alpha(grad_surf)
                ap[:]=255; del ap
            except Exception:
                for col in range(bar_w):
                    gf=col/max(1,bar_w)
                    pygame.draw.line(grad_surf,(int(cs[0]+(ce[0]-cs[0])*gf),int(cs[1]+(ce[1]-cs[1])*gf),int(cs[2]+(ce[2]-cs[2])*gf),255),(col,0),(col,bar_h-1))
            # cap the leading edge with rounded corners once, baked into the cache
            cap_s=pygame.Surface((bar_w,bar_h),pygame.SRCALPHA)
            pygame.draw.rect(cap_s,(255,255,255,255),cap_s.get_rect(),
                            border_top_left_radius=bar_h//2,border_bottom_left_radius=bar_h//2)
            grad_surf.blit(cap_s,(0,0),special_flags=pygame.BLEND_RGBA_MIN)
            self._countdown_cache.clear()   # only ever keep the most recent line's bar cached
            self._countdown_cache[cache_key] = grad_surf
            cached = grad_surf

        # Track (background) — cheap, fine to draw every frame
        track=pygame.Surface((bar_w,bar_h),pygame.SRCALPHA)
        pygame.draw.rect(track,(180,180,220,int(alpha*0.35)),track.get_rect(),border_radius=bar_h//2)
        surf.blit(track,(x_left,bar_y))

        # ── Stroke / outline ──────────────────────────────────────────────
        stroke_w = max(0, int(round(getattr(self.settings,"countdown_bar_stroke_width",0)*scale)))
        if stroke_w > 0:
            stroke_col = getattr(self.settings,"countdown_bar_stroke_color",(255,255,255))
            outline = pygame.Surface((bar_w+stroke_w*2, bar_h+stroke_w*2), pygame.SRCALPHA)
            pygame.draw.rect(
                outline, (*stroke_col[:3], min(255,int(alpha*0.95))),
                outline.get_rect(), width=stroke_w,
                border_radius=bar_h//2 + stroke_w
            )
            surf.blit(outline, (x_left-stroke_w, bar_y-stroke_w))

        remain=1.0-t; fill_w=max(1,int(bar_w*remain)); fill_alpha=int(alpha*(0.6+0.4*remain))
        fill_view = cached.subsurface((0,0,fill_w,bar_h)).copy()
        fill_view.set_alpha(fill_alpha)
        surf.blit(fill_view,(x_left,bar_y))

        ef=fill_w/max(1,bar_w)
        kc=(int(cs[0]+(ce[0]-cs[0])*ef),int(cs[1]+(ce[1]-cs[1])*ef),int(cs[2]+(ce[2]-cs[2])*ef))
        pygame.draw.circle(surf,(*kc,min(255,int(alpha*0.95))),(x_left+fill_w,bar_y+bar_h//2),max(2,bar_h))

    def render(self, surf, lines, elapsed, dt=0.016, playing=True):
        sw, sh = surf.get_size()
        vbg = self.video_bg
        if vbg and vbg.loaded and getattr(self.settings,"bg_video_path",None):
            frame = vbg.get_frame_direct(elapsed,(sw,sh),self.settings.bg_blur) if self.export_mode \
                    else vbg.get_frame(elapsed,(sw,sh),self.settings.bg_blur)
            if frame: self._blit_bg_with_pulse(surf,frame,(sw,sh),dt)
            else: surf.fill(C_BG)
        else:
            bg=self.get_bg((sw,sh))
            if bg: self._blit_bg_with_pulse(surf,bg,(sw,sh),dt)
            else: surf.fill(C_BG)
        scale_x=sw/DEFAULT_WIN_W; scale_y=sh/DEFAULT_WIN_H; scale=(scale_x+scale_y)/2

        eff_dt = dt if playing else 0.0   # freeze particle motion when not playing

        if getattr(self.settings,"lights_enabled",False): self._draw_lights(surf,eff_dt)
        if getattr(self.settings,"snow_enabled",False):   self._draw_snow(surf,eff_dt)
        if getattr(self.settings,"hearts_enabled",False): self._draw_hearts(surf,eff_dt)
        if getattr(self.settings,"startup_info_enabled",True): self._draw_startup_info(surf,elapsed,scale)
        if getattr(self.settings,"visualizer_enabled",False): self._draw_visualizer(surf,scale)
        if not lines: return
        self.update_slots(lines,elapsed)
        def _get(idx): return lines[idx] if 0<=idx<len(lines) else None
        top_line=_get(self.slot_top_line_index); bottom_line=_get(self.slot_bottom_line_index)
        fs=max(8,int(round(self.settings.font_size*scale_y)))
        font=make_font(self.settings.font_path,fs)
        ox=int(round(self.settings.offset_x*scale_x)); oy=int(round(self.settings.offset_y*scale_y))
        line_height=font.get_linesize(); spacing=max(0,int(round(getattr(self.settings,"line_spacing",50)*scale_y)))
        total_h=line_height*2+spacing; y_top=int(sh*0.55)+oy-(total_h//2); y_bottom=y_top+line_height+spacing
        PREVIEW=3.0; FI=0.5; FO=0.8; FOH=0.4
        FADE_FLOOR=float(getattr(self.settings,"fade_out_floor",0))
        top_pending=self._top_pending_next!=-1
        if self._top_alpha<255.0 and not top_pending:
            self._top_fade_timer=min(self._top_fade_timer+dt,FI)
            self._top_alpha=min(255.0,(self._top_fade_timer/FI)*255.0)
        elif top_pending:
            self._top_hold_timer+=dt
            if self._top_hold_timer>=FOH:
                fe=self._top_hold_timer-FOH; self._top_fade_timer=min(fe,FO)
                self._top_alpha=max(FADE_FLOOR,255.0-(255.0-FADE_FLOOR)*(self._top_fade_timer/FO))
        else: self._top_hold_timer=0.0
        bottom_pending=self._bottom_pending_next!=-1
        if self._bottom_alpha<255.0 and not bottom_pending:
            self._bottom_fade_timer=min(self._bottom_fade_timer+dt,FI)
            self._bottom_alpha=min(255.0,(self._bottom_fade_timer/FI)*255.0)
        elif bottom_pending:
            self._bottom_hold_timer+=dt
            if self._bottom_hold_timer>=FOH:
                fe=self._bottom_hold_timer-FOH; self._bottom_fade_timer=min(fe,FO)
                self._bottom_alpha=max(FADE_FLOOR,255.0-(255.0-FADE_FLOOR)*(self._bottom_fade_timer/FO))
        else: self._bottom_hold_timer=0.0
        if top_line and elapsed>=top_line.start-PREVIEW:
            self.update_syllable_progress(top_line,elapsed,dt)
            self._draw_line_with_animation(surf,top_line,font,sw,y_top,
                self.settings.color_sung,self.settings.color_next,ox,int(self._top_alpha),True,scale)
            if getattr(self.settings,"wipe_highlight",True):
                self._draw_wipe_highlight(surf,top_line,font,sw,y_top,elapsed,int(self._top_alpha),scale,ox)
            if getattr(self.settings,"countdown_bar",True):
                self._draw_countdown_bar(surf,top_line,font,sw,y_top,elapsed,int(self._top_alpha),scale,ox,PREVIEW)
        if bottom_line and elapsed>=bottom_line.start-PREVIEW:
            self.update_syllable_progress(bottom_line,elapsed,dt)
            self._draw_line_with_animation(surf,bottom_line,font,sw,y_bottom,
                self.settings.color_sung,self.settings.color_next,ox,int(self._bottom_alpha),True,scale)
            if getattr(self.settings,"wipe_highlight",True):
                self._draw_wipe_highlight(surf,bottom_line,font,sw,y_bottom,elapsed,int(self._bottom_alpha),scale,ox)
            if getattr(self.settings,"countdown_bar",True):
                self._draw_countdown_bar(surf,bottom_line,font,sw,y_bottom,elapsed,int(self._bottom_alpha),scale,ox,PREVIEW)


# ══════════════════════════════════════════════════════════════════════════════
#  PLAYER  (unchanged from original)
# ══════════════════════════════════════════════════════════════════════════════
class Player:
    def __init__(self):
        self.lines: List[LrcLine] = []
        self.playing = False; self.paused = False
        self._start_wall = 0.0; self._pause_elapsed = 0.0
        self.audio_loaded = False
        self.settings: Optional[Settings] = None
        self.renderer: Optional[GallopsStudioRenderer] = None
        self._pcm_samples = None; self._pcm_rate = 44100
        self._tmp_audio_path = None
        self._viz_peak = 1.0; self._raw_bass_energy = 0.0
        self._pulse_spectrum = None; self._pulse_spectrum_bins = 1
        self._pulse_spectrum_rate = 44100
        self._current_source = None   # logical path currently loaded (audio OR video-with-audio)

    def set_renderer(self, r): self.renderer = r

    def _desired_audio_source(self) -> Optional[str]:
        """Which file SHOULD currently be feeding the audio track, based on
        the 'Mute video (use imported audio)' setting: the background video's
        own audio when unmuted, otherwise the separately imported audio."""
        s = self.settings
        if not s: return None
        if (not getattr(s, "bg_video_muted", True) and s.bg_video_path
                and os.path.exists(s.bg_video_path)):
            return s.bg_video_path
        if s.audio_path and os.path.exists(s.audio_path):
            return s.audio_path
        return None

    def sync_audio_source(self):
        """Make sure the actually-loaded audio track matches what
        `_desired_audio_source` says it should be (imported audio vs. the
        background video's own audio), reloading only when it's out of date.
        Safe to call after any settings change — no-ops when nothing relevant
        changed."""
        desired = self._desired_audio_source()
        if desired is None:
            return
        if desired == self._current_source and self.audio_loaded:
            return
        was_playing = self.playing
        pos = self.get_elapsed()
        try:
            self.load_audio(desired)
            self.seek_to(pos)
            if was_playing:
                self.play()
        except Exception as e:
            print(f"[Player] audio source sync failed: {e}")

    def load_audio(self, path: str):
        VIDEO_EXTS={".mp4",".mkv",".mov",".avi",".webm",".flv",".wmv",".m4v"}
        ext=os.path.splitext(path)[1].lower()
        prev=self._tmp_audio_path
        if prev and os.path.exists(prev):
            try: os.remove(prev)
            except: pass
        if ext in VIDEO_EXTS:
            tmp=tempfile.NamedTemporaryFile(suffix=".wav",delete=False); tmp.close()
            self._tmp_audio_path=tmp.name
            r=subprocess.run([FFMPEG_BIN,"-y","-i",path,"-vn","-acodec","pcm_s16le","-ar","44100","-ac","2",tmp.name],
                             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL, creationflags=_subprocess_flags())
            if r.returncode!=0: raise RuntimeError("ffmpeg could not extract audio.")
            load_path=tmp.name
        else:
            self._tmp_audio_path=None; load_path=path
        pygame.mixer.music.load(load_path)
        self.audio_loaded=True; self.playing=False; self.paused=False; self._pause_elapsed=0.0
        self._pcm_samples=None
        try:
            proc=subprocess.run([FFMPEG_BIN,"-y","-i",path,"-vn","-ac","1","-ar","44100","-f","s16le","-"],
                                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL, creationflags=_subprocess_flags())
            if proc.returncode==0 and proc.stdout:
                self._pcm_samples=np.frombuffer(proc.stdout,dtype=np.int16)
        except: pass
        self._current_source = path   # remember the logical source we just loaded
        if self.renderer: self.renderer.reset()

    def load_lrc(self, path: str):
        self.lines=parse_lrc(path)
        if self.renderer: self.renderer.reset()

    def _music_seek(self, pos: float):
        try:
            pygame.mixer.music.play()
            if pos>0.0:
                try: pygame.mixer.music.set_pos(pos)
                except: pass
        except: pass

    def play(self):
        if not self.audio_loaded: return
        try: self._music_seek(self._pause_elapsed)
        except pygame.error:
            src=None
            if self.settings:
                if not getattr(self.settings,"bg_video_muted",True) and getattr(self.settings,"bg_video_path",None):
                    src=self.settings.bg_video_path
                elif getattr(self.settings,"audio_path",None): src=self.settings.audio_path
            if src and os.path.exists(src):
                try: self.load_audio(src); self._music_seek(self._pause_elapsed)
                except: return
            else: return
        self._start_wall=time.time()-self._pause_elapsed
        self.playing=True; self.paused=False

    def pause(self):
        if self.playing:
            elapsed = self.get_elapsed()      # capture elapsed WHILE still playing/busy
            pygame.mixer.music.pause()        # now pause the actual audio
            self._pause_elapsed = elapsed
            self.playing=False; self.paused=True

    def resume(self):
        if self.paused:
            pygame.mixer.music.unpause()
            self._start_wall=time.time()-self._pause_elapsed
            self.playing=True; self.paused=False

    def stop(self):
        pygame.mixer.music.stop()
        self.playing=False; self.paused=False; self._pause_elapsed=0.0
        if self._tmp_audio_path and os.path.exists(self._tmp_audio_path):
            try: pygame.mixer.music.unload(); os.remove(self._tmp_audio_path)
            except: pass
            self._tmp_audio_path=None; self.audio_loaded=False
            src=None
            if self.settings:
                if not getattr(self.settings,"bg_video_muted",True) and getattr(self.settings,"bg_video_path",None):
                    src=self.settings.bg_video_path
                elif getattr(self.settings,"audio_path",None): src=self.settings.audio_path
            if src and os.path.exists(src):
                try: self.load_audio(src)
                except: pass
        if self.renderer: self.renderer.reset()

    def seek(self, delta: float):
        self.seek_to(max(0.0,self.get_elapsed()+delta))

    def seek_to(self, pos: float):
        pos=max(0.0,pos); self._pause_elapsed=pos
        if self.playing: self._music_seek(pos); self._start_wall=time.time()-pos
        if self.renderer: self.renderer.reset()

    def get_elapsed(self) -> float:
        if self.paused:
            return self._pause_elapsed
        if self.playing:
            we=time.time()-self._start_wall
            if pygame.mixer.music.get_busy():
                ms=pygame.mixer.music.get_pos()
                if ms>=0:
                    me=self._pause_elapsed+(ms/1000.0); drift=we-me
                    if abs(drift)>0.05: self._start_wall+=drift*0.25; we=time.time()-self._start_wall
            else:
                if we>0.2:
                    self.playing=False; self.paused=False
                    dur=self.get_duration()
                    self._pause_elapsed=dur if dur else we; return self._pause_elapsed
            return we
        return self._pause_elapsed

    def get_duration(self) -> Optional[float]:
        if self.settings and self.settings.audio_path:
            return get_audio_duration(self.settings.audio_path)
        return None

    def update(self):
        if not self.playing: return
        e=self.get_elapsed()
        while (len(self.lines)>0 and
               self.lines[min(len(self.lines)-1,0)].start<=e): break

    def get_visualizer_bands(self, t: float, num_bands: int = 32) -> Optional[list]:
        samples=self._pcm_samples
        if samples is None or len(samples)==0: return None
        try:
            rate=self._pcm_rate; window_sec=0.08
            ci=int(t*rate); hw=int(window_sec*rate/2)
            si=max(0,ci-hw); ei=min(len(samples),ci+hw)
            if ei-si<64: self._raw_bass_energy=0.0; return [0.0]*num_bands
            window=samples[si:ei].astype(np.float32)/32768.0
            window=window*np.hanning(len(window))
            spectrum=np.abs(np.fft.rfft(window))
            if len(spectrum)<2: self._raw_bass_energy=0.0; return [0.0]*num_bands
            n_bins=len(spectrum); bass_hi=max(2,n_bins//10)
            self._raw_bass_energy=float(np.mean(spectrum[:bass_hi]))
            self._pulse_spectrum=spectrum; self._pulse_spectrum_bins=n_bins; self._pulse_spectrum_rate=rate
            log_edges=np.geomspace(1,n_bins,num_bands+1).astype(int); log_edges=np.clip(log_edges,0,n_bins)
            bands=[]
            for i in range(num_bands):
                lo,hi=log_edges[i],max(log_edges[i]+1,log_edges[i+1]); hi=min(hi,n_bins)
                bands.append(float(np.mean(spectrum[lo:hi])) if hi>lo else 0.0)
            peak=self._viz_peak; cm=max(bands) if bands else 0.0
            if cm>peak: peak=cm
            else: peak=peak*0.98+cm*0.02
            self._viz_peak=max(peak,0.001)
            return [min(1.0,b/self._viz_peak) for b in bands]
        except: self._raw_bass_energy=0.0; return None


# ══════════════════════════════════════════════════════════════════════════════
#  EXPORT WORKER  (QThread wrapper around export_video_streaming)
# ══════════════════════════════════════════════════════════════════════════════
class ExportWorker(QThread):
    progress = pyqtSignal(float)
    log      = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, player, renderer, settings, video_bg,
                 out_path, fps, start_time=0.0, duration=None):
        super().__init__()
        self.player=player; self.renderer=renderer; self.settings=settings
        self.video_bg=video_bg; self.out_path=out_path; self.fps=fps
        self.start_time=start_time; self.duration=duration
        self.cancel_event=threading.Event()

    def run(self):
        ok, msg = export_video_streaming(
            self.player, self.renderer, self.out_path,
            log_cb=lambda m: self.log.emit(m),
            fps=self.fps,
            progress_cb=lambda p: self.progress.emit(p),
            settings=self.settings,
            start_time=self.start_time,
            duration=self.duration,
            cancel_event=self.cancel_event,
            video_bg=self.video_bg)
        self.finished.emit(ok, msg)

    def cancel(self): self.cancel_event.set()


# ══════════════════════════════════════════════════════════════════════════════
#  EXPORT FUNCTION  (copied verbatim, no Qt dependency)
# ══════════════════════════════════════════════════════════════════════════════
def export_video_streaming(player, renderer, out_path,
                           log_cb=None, fps=30, progress_cb=None,
                           settings=None, start_time=0.0, duration=None,
                           cancel_event=None, video_bg=None):
    def log(msg):
        if log_cb: log_cb(msg)
        print(f"[EXPORT] {msg}")
    if not player.audio_loaded: return False,"No audio loaded."
    if settings and settings.use_custom_settings:
        crf=settings.custom_crf; preset=settings.custom_preset
        codec=getattr(settings,"custom_codec","libx264"); tune=getattr(settings,"custom_tune","none")
        profile=getattr(settings,"custom_profile","high")
        two_pass=getattr(settings,"custom_two_pass",False); target_size_mb=getattr(settings,"custom_target_size_mb",0)
        abi=int(settings.custom_audio_bitrate) if not isinstance(settings.custom_audio_bitrate,str) else 3
        audio_bitrate=AUDIO_BITRATES[abi] if abi<len(AUDIO_BITRATES) else "192k"
        resolution_name=settings.video_resolution
    else:
        pc=VIDEO_PRESETS.get(settings.video_preset,VIDEO_PRESETS["Standard/720p"])
        crf=pc["crf"]; preset=pc["preset"]; codec="libx264"; tune="none"; profile="high"
        two_pass=False; target_size_mb=0; audio_bitrate=pc["audio_bitrate"]
        resolution_name=settings.video_resolution
    resolution=RESOLUTIONS.get(resolution_name,RESOLUTIONS["720p (HD)"])
    width,height=resolution
    audio_dur=get_audio_duration(settings.audio_path) if settings and settings.audio_path else None
    lyrics_end=(player.lines[-1].end+1.0) if player.lines else 0.0
    full_dur=audio_dur if (audio_dur and (not player.lines or audio_dur>lyrics_end)) else lyrics_end
    start_time=max(0.0,start_time)
    end_time=min(full_dur,start_time+duration) if duration else full_dur
    clip_dur=end_time-start_time
    if clip_dur<=0: return False,"Invalid time range."
    frame_count=int(clip_dur*fps)
    log(f"Export: {start_time:.1f}s→{end_time:.1f}s  {width}x{height}  {frame_count}f@{fps}fps")
    ffmpeg_cmd=[FFMPEG_BIN,"-y","-loglevel","warning","-f","rawvideo","-vcodec","rawvideo",
                "-s",f"{width}x{height}","-pix_fmt","rgb24","-r",str(fps),"-i","-"]
    bg_video_path=getattr(settings,"bg_video_path",None)
    bg_video_muted=getattr(settings,"bg_video_muted",True)
    use_vid_audio=(bg_video_path and os.path.exists(bg_video_path) and not bg_video_muted)
    audio_source=bg_video_path if use_vid_audio else (settings.audio_path if settings else None)
    if audio_source and os.path.exists(audio_source):
        ffmpeg_cmd.extend(["-ss",str(start_time),"-i",audio_source,"-c:a","aac","-b:a",audio_bitrate,"-shortest"])
    has_motion=getattr(settings,"bg_pulse_enabled",False) or getattr(settings,"visualizer_enabled",False)
    is_vp9=(codec=="libvpx-vp9"); is_h265=(codec=="libx265")
    eff_tune=tune
    if eff_tune=="none" and has_motion and not is_vp9: eff_tune="animation"
    if is_vp9:
        vp9_crf=max(15,min(63,crf*2))
        ffmpeg_cmd.extend(["-c:v","libvpx-vp9","-b:v","0","-crf",str(vp9_crf),"-deadline","good","-cpu-used","2","-pix_fmt","yuv420p","-row-mt","1"])
    elif is_h265:
        x265p=[f"crf={crf}"]
        if eff_tune!="none": x265p.append(f"tune={eff_tune}")
        if has_motion: x265p.extend(["keyint=250","bframes=4"])
        ffmpeg_cmd.extend(["-c:v","libx265","-preset",preset,"-pix_fmt","yuv420p","-x265-params",":".join(x265p),
                           "-color_primaries","bt709","-color_trc","bt709","-colorspace","bt709"])
    else:
        ffmpeg_cmd.extend(["-c:v","libx264","-preset",preset,"-profile:v",profile,"-level","4.1","-pix_fmt","yuv420p","-crf",str(crf),"-color_primaries","bt709","-color_trc","bt709","-colorspace","bt709"])
        if eff_tune!="none": ffmpeg_cmd.extend(["-tune",eff_tune])
        if has_motion: ffmpeg_cmd.extend(["-g",str(fps*10),"-bf","2"])
    if not is_vp9 and not two_pass:
        maxrate="20M" if crf<=17 else ("12M" if crf<=19 else ("8M" if crf<=21 else "5M"))
        bufsize="40M" if crf<=17 else ("24M" if crf<=19 else ("16M" if crf<=21 else "10M"))
        ffmpeg_cmd.extend(["-maxrate",maxrate,"-bufsize",bufsize])
    ffmpeg_cmd.append(out_path)
    process=None
    try:
        log("Starting FFmpeg…")
        process=subprocess.Popen(ffmpeg_cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE, creationflags=_subprocess_flags())
        surf=pygame.Surface((width,height))
        tmp_p=Player(); tmp_p.lines=player.lines; tmp_p.settings=settings
        export_renderer=GallopsStudioRenderer(settings,video_bg)
        export_renderer.export_mode=True
        if video_bg and video_bg.loaded:
            video_bg._stop_evt.set()
            if video_bg._thread: video_bg._thread.join(timeout=2.0); video_bg._thread=None
            import cv2 as _cv2
            fi=int(start_time*video_bg._fps)%max(1,video_bg._frame_count)
            video_bg._cap.set(_cv2.CAP_PROP_POS_FRAMES,fi)
        import queue as _q
        pipe_q=_q.Queue(maxsize=4); SENTINEL=None
        def _writer():
            while True:
                chunk=pipe_q.get()
                if chunk is SENTINEL: break
                try: process.stdin.write(chunk)
                except: break
        wt=threading.Thread(target=_writer,daemon=True); wt.start()
        dt=1.0/fps; last_prog=-1
        for fi in range(frame_count):
            t=start_time+fi*dt; tmp_p._pause_elapsed=t
            surf.fill(C_BG)
            if getattr(settings,"visualizer_enabled",False) or getattr(settings,"bg_pulse_enabled",False):
                export_renderer.pcm_bands=player.get_visualizer_bands(t,getattr(settings,"visualizer_bands",32))
                export_renderer._raw_bass_energy=getattr(player,"_raw_bass_energy",0.0)
                export_renderer._pulse_spectrum=getattr(player,"_pulse_spectrum",None)
                export_renderer._pulse_spectrum_bins=getattr(player,"_pulse_spectrum_bins",1)
                export_renderer._pulse_spectrum_rate=getattr(player,"_pulse_spectrum_rate",44100)
            export_renderer.render(surf,tmp_p.lines,t,dt)
            pipe_q.put(pygame.image.tostring(surf,"RGB"))
            prog=fi/frame_count
            if progress_cb and int(prog*100)!=last_prog:
                last_prog=int(prog*100); progress_cb(prog)
            if cancel_event and cancel_event.is_set():
                log("Cancelled."); break
        pipe_q.put(SENTINEL); wt.join()
        process.stdin.close(); rc=process.wait()
        if cancel_event and cancel_event.is_set():
            try:
                if os.path.exists(out_path): os.remove(out_path)
            except: pass
            return False,"Export cancelled."
        if rc!=0:
            err=process.stderr.read().decode("utf-8",errors="ignore")
            return False,f"FFmpeg error (code {rc}): {err[-500:]}"
        if progress_cb: progress_cb(1.0)
        log(f"Done: {out_path}")
        return True,out_path
    except FileNotFoundError: return False,"FFmpeg not found."
    except Exception as e:
        import traceback; log(traceback.format_exc())
        return False,str(e)
    finally:
        if process and process.poll() is None: process.terminate(); process.wait()
        if video_bg and video_bg.loaded and video_bg._thread is None:
            video_bg._stop_evt.clear(); video_bg._playing=False
            video_bg._thread=threading.Thread(target=video_bg._decode_loop,daemon=True)
            video_bg._thread.start()


# ══════════════════════════════════════════════════════════════════════════════
#  Qt PREVIEW WIDGET  — renders pygame surface into a QLabel every frame
# ══════════════════════════════════════════════════════════════════════════════
class PreviewWidget(QWidget):
    """Video preview widget."""
    seeked = pyqtSignal(float)   # You can keep this or remove it – it's not used anymore

    def __init__(self):
        super().__init__()
        self.setMinimumSize(320, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self._pixmap: Optional[QPixmap] = None

    def display_surface(self, surf: pygame.Surface):
        w, h = surf.get_size()
        raw = pygame.image.tostring(surf, "RGB")
        img = QImage(raw, w, h, w * 3, QImage.Format.Format_RGB888)
        self._pixmap = QPixmap.fromImage(img)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        if self._pixmap is None:
            return
        pw, ph = self._pixmap.width(), self._pixmap.height()
        ww, wh = self.width(), self.height()
        if pw == 0 or ph == 0:
            return
        scale = min(ww / pw, wh / ph)
        dw = int(pw * scale); dh = int(ph * scale)
        dx = (ww - dw) // 2;  dy = (wh - dh) // 2
        mode = (Qt.TransformationMode.SmoothTransformation if scale < 1.0
                else Qt.TransformationMode.FastTransformation)
        painter.drawPixmap(dx, dy, self._pixmap.scaled(
            dw, dh, Qt.AspectRatioMode.IgnoreAspectRatio, mode))


# ══════════════════════════════════════════════════════════════════════════════
#  SETTINGS PANEL  (PyQt6 scrollable form — replaces all manual pygame widgets)
# ══════════════════════════════════════════════════════════════════════════════
class SettingsPanel(QScrollArea):
    changed = pyqtSignal()   # emitted whenever any setting changes

    def __init__(self, settings: Settings, renderer: GallopsStudioRenderer,
                 parent=None):
        super().__init__(parent)
        self.settings = settings
        self.renderer = renderer
        self._suppress = False   # suppress change signals while loading
        self._widgets: Dict[str, QWidget] = {}
        self._val_labels: Dict[str, QLabel] = {}
        self._rgb_btns = []
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setContentsMargins(0, 0, 0, 0)
        container = QWidget()
        container.setMinimumWidth(280)
        self._layout = QVBoxLayout(container)
        self._layout.setSpacing(4)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._build()
        self._layout.addStretch()
        self.setWidget(container)
        # ── Install event filter so mouse-wheel always scrolls the panel,
        #    never accidentally changes a slider or combo underneath ────────
        self.viewport().installEventFilter(self)

    # ── public ────────────────────────────────────────────────────────────
    def refresh(self):
        """Reload all widget values from settings (call after undo/profile load)."""
        self._suppress = True
        self._sync_all()
        self._suppress = False

    # ── Wheel event interception ─────────────────────────────────────────
    def eventFilter(self, obj, event):
        """Redirect wheel events from any child widget to the panel scrollbar.

        Without this, QSlider and QComboBox consume wheel events to change
        their value, which causes accidental edits when the user just wants
        to scroll the settings panel.  We intercept at the viewport level
        and forward the wheel delta to the vertical scrollbar instead.
        """
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.Wheel:
            # Forward the wheel event to the scroll area's own scrollbar
            self.verticalScrollBar().event(event)
            return True   # consumed — child widget never sees it
        return super().eventFilter(obj, event)

    def wheelEvent(self, event):
        """Also handle wheel events that land directly on the scroll area."""
        self.verticalScrollBar().event(event)

    # ── helpers ───────────────────────────────────────────────────────────
    def _group(self, title) -> QVBoxLayout:
        gb = QGroupBox(title)
        inner = QVBoxLayout(gb)
        inner.setSpacing(3)
        inner.setContentsMargins(6, 14, 6, 6)   # top=14 clears the group box title
        self._layout.addWidget(gb)
        return inner

    def _slider_row(self, layout, label, key, mn, mx, step=1):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setFixedWidth(130)
        lbl.setWordWrap(True)
        sl  = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(mn, mx)
        sl.setSingleStep(step); sl.setPageStep(step * 5)
        sl.setMinimumWidth(80)
        # NoFocus = never receives wheel events (wheel always goes to scroll area)
        sl.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        sl.wheelEvent = lambda e: e.ignore()   # always ignore wheel on sliders
        val = QLabel(str(getattr(self.settings, key)))
        val.setFixedWidth(38)
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        sl.setValue(int(getattr(self.settings, key)))
        def _on(v, k=key, vl=val):
            if not self._suppress:
                setattr(self.settings, k, v); vl.setText(str(v))
                if k == "bg_blur":   self.renderer.invalidate_bg()
                elif k == "font_size": self.renderer.invalidate_font()
                self.changed.emit()
        sl.valueChanged.connect(_on)
        row.addWidget(lbl); row.addWidget(sl); row.addWidget(val)
        layout.addLayout(row)
        self._widgets[key] = sl
        self._val_labels[key] = val

    def _combo_row(self, layout, label, key, options):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setFixedWidth(130)
        lbl.setWordWrap(True)
        cb  = QComboBox(); cb.addItems(options)
        cb.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        cb.wheelEvent = lambda e: e.ignore()   # always ignore wheel on combos
        cur = getattr(self.settings, key, options[0])
        idx = options.index(cur) if cur in options else 0
        cb.setCurrentIndex(idx)
        def _on(i, k=key, opts=options):
            if not self._suppress:
                setattr(self.settings, k, opts[i]); self.changed.emit()
        cb.currentIndexChanged.connect(_on)
        row.addWidget(lbl); row.addWidget(cb)
        layout.addLayout(row)
        self._widgets[key] = cb

    def _check_row(self, layout, label, key):
        cb = QCheckBox(label)
        cb.setChecked(bool(getattr(self.settings, key, False)))
        def _on(state, k=key):
            if not self._suppress:
                setattr(self.settings, k, bool(state)); self.changed.emit()
        cb.stateChanged.connect(_on)
        layout.addWidget(cb)
        self._widgets[key] = cb

    def _text_row(self, layout, label, key):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setFixedWidth(130)
        lbl.setWordWrap(True)
        edit = QLineEdit()
        edit.setText(str(getattr(self.settings, key, "")))
        edit.textChanged.connect(lambda text, k=key: self._on_text_changed(k, text))
        row.addWidget(lbl)
        row.addWidget(edit)
        layout.addLayout(row)
        self._widgets[key] = edit

    def _on_text_changed(self, key, text):
        if not self._suppress:
            setattr(self.settings, key, text)
            self.changed.emit()

    def _color_row(self, layout, label, key):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setFixedWidth(130)
        lbl.setWordWrap(True)
        btn = QPushButton()
        btn.setFixedWidth(60)
        col = getattr(self.settings, key, (255,255,255))
        btn.setStyleSheet(f"background:rgb{col};border-radius:4px;")
        def _pick(*args, k=key, b=btn):
            cur = getattr(self.settings, k, (255,255,255))
            qc  = QColorDialog.getColor(QColor(*cur), self, f"Choose {k}")
            if qc.isValid():
                t = (qc.red(), qc.green(), qc.blue())
                setattr(self.settings, k, t)
                b.setStyleSheet(f"background:rgb{t};border-radius:4px;")
                self.changed.emit()
        btn.clicked.connect(_pick)
        row.addWidget(lbl); row.addWidget(btn); row.addStretch()
        layout.addLayout(row)
        self._widgets[key] = btn

    def _rgb_color_row(self, layout, label, key_r, key_g, key_b):
        """Color picker for settings stored as three separate int fields (r, g, b)."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setFixedWidth(130)
        lbl.setWordWrap(True)
        r = int(getattr(self.settings, key_r, 255))
        g = int(getattr(self.settings, key_g, 128))
        b = int(getattr(self.settings, key_b, 128))
        btn = QPushButton()
        btn.setFixedWidth(60)
        btn.setStyleSheet(f"background:rgb({r},{g},{b});border-radius:4px;")
        def _pick(*args, kr=key_r, kg=key_g, kb=key_b, b2=btn):
            rv = int(getattr(self.settings, kr, 255))
            gv = int(getattr(self.settings, kg, 128))
            bv = int(getattr(self.settings, kb, 128))
            qc = QColorDialog.getColor(QColor(rv, gv, bv), self,
                                       f"Choose {label}")
            if qc.isValid():
                setattr(self.settings, kr, qc.red())
                setattr(self.settings, kg, qc.green())
                setattr(self.settings, kb, qc.blue())
                b2.setStyleSheet(
                    f"background:rgb({qc.red()},{qc.green()},{qc.blue()});border-radius:4px;")
                # Sync the individual RGB sliders
                for k, v in [(kr, qc.red()), (kg, qc.green()), (kb, qc.blue())]:
                    if k in self._widgets:
                        self._widgets[k].setValue(v)
                    if k in self._val_labels:
                        self._val_labels[k].setText(str(v))
                self.changed.emit()
        btn.clicked.connect(_pick)
        row.addWidget(lbl); row.addWidget(btn); row.addStretch()
        layout.addLayout(row)
        # Store button under a composite key so _sync_all can update it
        self._widgets[f"{key_r}__rgb_btn"] = btn
        self._rgb_btns.append((btn, key_r, key_g, key_b))

    def _file_row(self, layout, label, key, exts=""):
        """Create a file selection row with browse and clear buttons."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        
        # Label
        lbl = QLabel(label)
        lbl.setFixedWidth(80)
        lbl.setStyleSheet("font-size:12px;")
        
        # Display path (shortened)
        disp = QLabel(self._short(getattr(self.settings, key, "")))
        disp.setMinimumWidth(60)
        disp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        disp.setStyleSheet("color:#80a0c0;font-size:10px;")
        disp.setWordWrap(True)
        
        # Browse button
        btn = QPushButton("Browse…")
        btn.setFixedWidth(65)
        
        # Clear button
        clr = QPushButton("✕")
        clr.setFixedWidth(24)
        clr.setProperty("class", "danger")
        
        # Store the display label (with _disp suffix so _sync_all ignores it)
        disp_key = f"{key}_disp"
        self._widgets[disp_key] = disp
        
        def _browse():
            path, _ = QFileDialog.getOpenFileName(self, f"Select {label}", "", exts)
            if path:
                setattr(self.settings, key, path)
                disp.setText(self._short(path))
                # The video background is a stateful VideoBackground object
                # (owned by MainWindow, referenced by the renderer) that has
                # to be explicitly (re)loaded — just storing the path here
                # does NOT make the renderer pick up the new video.
                if key == "bg_video_path":
                    try:
                        self.renderer.video_bg.load(path)
                    except Exception as e:
                        print(f"[Background Video] load failed: {e}")
                self.changed.emit()
        
        def _clear():
            setattr(self.settings, key, None)
            disp.setText("—")
            if key == "bg_video_path":
                try:
                    self.renderer.video_bg.close()
                except Exception as e:
                    print(f"[Background Video] close failed: {e}")
            self.changed.emit()
        
        btn.clicked.connect(_browse)
        clr.clicked.connect(_clear)
        
        row.addWidget(lbl)
        row.addWidget(disp)
        row.addWidget(btn)
        row.addWidget(clr)
        layout.addLayout(row)

    @staticmethod
    def _short(path):
        return os.path.basename(path)[:20] if path else "—"

    def _build(self):
        self._widgets:    Dict[str, QWidget] = {}
        self._val_labels: Dict[str, QLabel]  = {}

        # ── Font & Text ──────────────────────────────────────────────────
        g = self._group("Font & Text")
        self._combo_row(g, "Font", "font_name", list(FONT_OPTIONS.keys()))
        self._slider_row(g, "Font Size", "font_size", 28, 90)
        self._slider_row(g, "Horizontal Offset", "offset_x", -400, 400, 5)
        self._slider_row(g, "Vertical Offset",   "offset_y", -200, 200, 5)
        self._slider_row(g, "Slot Spacing",       "line_spacing", 10, 160, 5)

        # ── Colors ───────────────────────────────────────────────────────
        g = self._group("Colors")
        self._color_row(g, "Highlight (sung)", "color_sung")
        self._color_row(g, "Dim (upcoming)",   "color_next")

        # ── Background ──────────────────────────────────────────────────
        g = self._group("Background")
        self._file_row(g, "Image", "bg_image_path",
                       "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        self._slider_row(g, "BG Blur", "bg_blur", 0, 10)
        self._file_row(g, "Video", "bg_video_path",
                       "Video (*.mp4 *.mkv *.mov *.avi *.webm)")
        self._check_row(g, "Mute video (use imported audio)", "bg_video_muted")

        # ── Lyric Style ──────────────────────────────────────────────────
        g = self._group("Lyric Style")
        self._combo_row(g, "Style", "lyric_style", LYRIC_STYLES)
        self._slider_row(g, "BG Opacity (0=off)", "lyric_bg_opacity", 0, 255, 5)
        self._color_row(g,  "BG Color",             "lyric_bg_color")
        self._slider_row(g, "Corner Radius (-1=pill)","lyric_bg_radius", -1, 60)
        self._slider_row(g, "Fade Out Floor",         "fade_out_floor",   0, 220, 5)
        self._slider_row(g, "Outer Glow Radius",      "glow_radius",       0, 12)
        self._slider_row(g, "Glow Opacity", "glow_opacity", 0, 255, 5)
        self._slider_row(g, "Glow Brightness %", "glow_brightness", 50, 300, 5)
        self._slider_row(g, "Glow Intensity %", "glow_intensity", 0, 200, 5)
        self._color_row(g,  "Glow Color",             "glow_color")
        self._slider_row(g, "Glow Distance",          "glow_distance",     1, 5)
        self._slider_row(g, "Stroke Width",           "stroke_width",      0, 8)
        self._color_row(g,  "Stroke Color",           "stroke_color")
        self._slider_row(g, "Shadow Offset",          "shadow_offset",     0, 12)

        # ── Lyric BG Image ───────────────────────────────────────────────
        g = self._group("Lyric BG Image")
        self._file_row(g, "Image", "lyric_bg_image_path",
                       "Images (*.png *.jpg *.jpeg *.bmp)")
        self._slider_row(g, "Image Opacity",  "lyric_bg_image_opacity", 0, 255, 5)
        self._combo_row(g,  "Fit Mode",       "lyric_bg_image_mode",    ["tile","stretch","fit"])
        self._slider_row(g, "Extra Width",    "lyric_bg_pad_extra",    0, 200, 4)
        self._slider_row(g, "Extra Height",   "lyric_bg_height_extra", 0, 100, 2)

        # ── Singing Guide ────────────────────────────────────────────────
        g = self._group("Singing Guide")
        self._check_row(g, "Wipe Highlight",  "wipe_highlight")
        self._color_row(g,  "Wipe Color",     "wipe_color")
        self._check_row(g, "Countdown Bar",   "countdown_bar")
        self._slider_row(g, "Bar Height",     "countdown_bar_height", 2, 20)
        self._slider_row(g, "Bar Stroke Width","countdown_bar_stroke_width", 0, 6)
        self._color_row(g,  "Bar Stroke Color","countdown_bar_stroke_color")
        self._color_row(g,  "Bar Start Color","countdown_bar_color_start")
        self._color_row(g,  "Bar End Color",  "countdown_bar_color_end")
        

        # ── Startup Info ─────────────────────────────────────────────────
        g = self._group("Startup Info Card")
        self._check_row(g, "Enabled",         "startup_info_enabled")
        self._combo_row(g,  "Slide Direction","startup_info_direction",
                        ["top","bottom","left","right"])
        self._text_row(g, "Title (empty = from LRC)", "startup_info_title")
        self._text_row(g, "Artist (empty = from LRC)", "startup_info_artist")
        self._slider_row(g, "Duration (s×10)","startup_info_duration", 10,200, 5)
        self._slider_row(g, "Delay (s×10)",   "startup_info_delay",     0,100, 5)
        self._slider_row(g, "Offset X",       "startup_info_offset_x",-600,600,10)
        self._slider_row(g, "Offset Y",       "startup_info_offset_y",-400,400,10)
        self._check_row(g, "Neon Border",     "startup_info_neon_enabled")
        self._slider_row(g, "Neon Width",     "startup_info_neon_width", 1, 12)
        self._color_row(g,  "Neon Color",     "startup_info_neon_color")

        # ── Audio Visualizer ─────────────────────────────────────────────
        g = self._group("Audio Visualizer")
        self._check_row(g, "Enabled",        "visualizer_enabled")
        self._combo_row(g,  "Style",         "visualizer_style",
                        ["bars","mirror_bars","wave"])
        self._color_row(g,  "Bar Color",     "visualizer_color")
        self._slider_row(g, "Height (px)",   "visualizer_height",  20,300,10)
        self._slider_row(g, "Bands",         "visualizer_bands",    8, 96, 4)
        self._slider_row(g, "Opacity",       "visualizer_opacity",  0,255, 5)

        # ── BG Pulse ────────────────────────────────────────────────────
        g = self._group("BG Pulse (audio-reactive zoom)")
        self._check_row(g, "Enabled",           "bg_pulse_enabled")
        self._slider_row(g, "Low Freq (Hz)",    "bg_pulse_freq_low",    1, 500, 5)
        self._slider_row(g, "High Freq (Hz)",   "bg_pulse_freq_high",   5,2000,10)
        self._slider_row(g, "Threshold (%)",    "bg_pulse_threshold",   0,  80, 2)
        self._slider_row(g, "Oscillation",      "bg_pulse_oscillation", 0, 100, 5)
        self._slider_row(g, "Initial Zoom (%)", "bg_pulse_initial_zoom",0,  30)
        self._slider_row(g, "Zoom Level (%)",   "bg_pulse_zoom_level",  0,  60, 2)

        # ── Snow ────────────────────────────────────────────────────────
        g = self._group("Snow Effect")
        self._check_row(g, "Enabled",      "snow_enabled")
        self._slider_row(g, "Count",       "snow_count",    10, 600,10)
        self._slider_row(g, "Speed",       "snow_speed",     1, 100, 5)
        self._slider_row(g, "Size",        "snow_size",      1,  20)
        self._slider_row(g, "Opacity",     "snow_opacity",   0, 255, 5)
        self._slider_row(g, "Wind",        "snow_wind",    -50,  50, 5)

        # ── Hearts ──────────────────────────────────────────────────────
        g = self._group("Falling Hearts")
        self._check_row(g, "Enabled",      "hearts_enabled")
        self._file_row(g, "SVG Icon", "hearts_svg_path", "SVG (*.svg)")
        self._check_row(g, "Color Overlay (off = SVG's own colors)", "hearts_color_overlay")
        self._slider_row(g, "Count",       "hearts_count",    5,300, 5)
        self._slider_row(g, "Speed",       "hearts_speed",    1,100, 5)
        self._slider_row(g, "Min Size",    "hearts_min_size", 4, 60, 2)
        self._slider_row(g, "Max Size",    "hearts_max_size", 4, 80, 2)
        self._slider_row(g, "Opacity",     "hearts_opacity",  0,255, 5)
        self._rgb_color_row(g, "Heart Color",
                            "hearts_color_r", "hearts_color_g", "hearts_color_b")
        self._slider_row(g, "Color Red",   "hearts_color_r",   0,255, 5)
        self._slider_row(g, "Color Green", "hearts_color_g",   0,255, 5)
        self._slider_row(g, "Color Blue",  "hearts_color_b",   0,255, 5)

        # ── Dancing Lights ──────────────────────────────────────────────
        g = self._group("Dancing Lights")
        self._check_row(g, "Enabled",          "lights_enabled")
        self._combo_row(g,  "Movement Pattern","lights_pattern", LIGHTS_PATTERNS)
        self._check_row(g, "Rainbow Mode",     "lights_rainbow")
        self._check_row(g, "Beat Reactive",    "lights_reactive")
        self._check_row(g, "Beat Blink",       "lights_pulse")
        self._slider_row(g, "Blink Sensitivity","lights_pulse_sens", 0,100, 5)
        self._slider_row(g, "Beam Count",      "lights_count",   1, 30)
        self._slider_row(g, "Sweep Speed",     "lights_speed",   1,200, 5)
        self._slider_row(g, "Opacity",         "lights_opacity", 0,255, 5)
        self._slider_row(g, "Beam Width (°)",  "lights_width",   1, 60)
        self._slider_row(g, "Beam Length (%)", "lights_length", 10,150, 5)
        self._check_row(g, "Neon Glow",        "lights_neon_glow")
        self._slider_row(g, "Glow Radius",     "lights_glow_radius", 0, 30)

        # ── Export ──────────────────────────────────────────────────────
        g = self._group("Video Export")
        self._combo_row(g, "Quality Preset",  "video_preset",    list(VIDEO_PRESETS.keys()))
        self._combo_row(g, "Resolution",      "video_resolution",list(RESOLUTIONS.keys()))
        self._slider_row(g, "Export FPS",     "export_fps",      10, 60, 5)
        self._check_row(g, "Use Custom Settings", "use_custom_settings")
        self._slider_row(g, "Custom CRF",     "custom_crf",      15, 30)
        self._combo_row(g, "Encoding Preset", "custom_preset",   ENCODING_PRESETS)
        self._combo_row(g, "Codec",           "custom_codec",    EXPORT_CODECS)
        self._combo_row(g, "Tune",            "custom_tune",     EXPORT_TUNES_264)
        self._combo_row(g, "H.264 Profile",   "custom_profile",  EXPORT_PROFILES)
        self._check_row(g, "Two-Pass",        "custom_two_pass")
        self._slider_row(g, "Target Size MB (0=CRF)", "custom_target_size_mb", 0,2000,50)
        # audio bitrate uses index
        self._slider_row(g, "Audio Bitrate (index)", "custom_audio_bitrate", 0,
                         len(AUDIO_BITRATES)-1)

    def _sync_all(self):
        """Push all settings values back into their widgets."""
        for key, widget in self._widgets.items():
            # Skip composite rgb-button keys (handled separately below)
            if key.endswith("__rgb_btn"):
                continue
            val = getattr(self.settings, key, None)
            if val is None: continue
            if isinstance(widget, QSlider):
                widget.setValue(int(val))
                if key in self._val_labels:
                    self._val_labels[key].setText(str(int(val)))
            elif isinstance(widget, QComboBox):
                opts = [widget.itemText(i) for i in range(widget.count())]
                if str(val) in opts:
                    widget.setCurrentIndex(opts.index(str(val)))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(val))
            elif isinstance(widget, QPushButton) and isinstance(val, tuple):
                widget.setStyleSheet(f"background:rgb{val};border-radius:4px;")
            elif isinstance(widget, QLineEdit):
                widget.setText(str(val) if val is not None else "")
            elif isinstance(widget, QLabel):
                widget.setText(self._short(val) if isinstance(val,str) else str(val))
        # Refresh composite RGB color buttons
        for btn, kr, kg, kb in self._rgb_btns:
            r = int(getattr(self.settings, kr, 255))
            g = int(getattr(self.settings, kg, 128))
            b = int(getattr(self.settings, kb, 128))
            btn.setStyleSheet(f"background:rgb({r},{g},{b});border-radius:4px;")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gallops Studio")
        self.resize(1400, 820)

        # ── Core objects ─────────────────────────────────────────────────
        self.settings   = Settings()
        self.settings.load()
        self.video_bg   = VideoBackground()
        self.renderer   = GallopsStudioRenderer(self.settings, self.video_bg)
        self.player     = Player()
        self.player.settings = self.settings
        self.player.set_renderer(self.renderer)

        # Undo/redo stacks
        self._undo: List[dict] = []
        self._redo: List[dict] = []

        # Recent projects
        self._projects = self._load_projects()

        # ── pygame offscreen surface ──────────────────────────────────────
        # pygame.init() and mixer.init() are called in main() BEFORE this
        # constructor, ensuring SDL_VIDEODRIVER=dummy is set first.
        # Sized to match the aspect ratio of the currently selected export
        # resolution (e.g. 16:9 landscape or the 9:16 vertical option) so the
        # live preview always reflects the real output shape, capped to a
        # pixel budget so vertical/4K choices don't slow the preview down.
        self._pg_surf = pygame.Surface(self._compute_preview_size())

        # Reload last session files
        self._restore_session()

        # ── Build UI ─────────────────────────────────────────────────────
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()

        # ── Render timer (60 fps) ─────────────────────────────────────────
        self._last_t = time.time()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)   # ~60 fps

        # Tick-loop caches (avoid expensive calls every frame)
        self._dur_cache: Optional[float] = None      # ffprobe result, cached
        self._last_time_str: str = ""                # avoid redundant setText
        self._last_player_state: str = "stopped"     # avoid redundant setStyleSheet

        # Export worker reference
        self._export_worker: Optional[ExportWorker] = None

    # ── Preview sizing ────────────────────────────────────────────────────
    def _compute_preview_size(self) -> Tuple[int, int]:
        """Return the offscreen preview-surface size, matching the aspect
        ratio of the currently selected export resolution (16:9 landscape,
        9:16 vertical, etc.) but capped to roughly the same pixel budget as
        the original fixed 1280x720 canvas so the live preview stays smooth
        regardless of how large/tall the chosen export resolution is."""
        res_name = getattr(self.settings, "video_resolution", "720p (HD)")
        rw, rh = RESOLUTIONS.get(res_name, RESOLUTIONS["720p (HD)"])
        budget = DEFAULT_WIN_W * DEFAULT_WIN_H
        cur = rw * rh
        if cur > budget:
            scale = math.sqrt(budget / cur)
            pw = max(16, int(round(rw * scale)))
            ph = max(16, int(round(rh * scale)))
        else:
            pw, ph = rw, rh
        return pw, ph

    # ── Session restore ───────────────────────────────────────────────────
    def _restore_session(self):
        s = self.settings
        if s.audio_path and os.path.exists(s.audio_path):
            try: self.player.load_audio(s.audio_path)
            except: pass
        if s.lrc_path and os.path.exists(s.lrc_path):
            try:
                self.player.load_lrc(s.lrc_path)
                meta = extract_lrc_metadata(s.lrc_path)
                s._lrc_meta_title  = meta.get("title","")
                s._lrc_meta_artist = meta.get("artist","")
            except: pass
        if s.bg_video_path and os.path.exists(s.bg_video_path):
            self.video_bg.load(s.bg_video_path)
        # Whichever audio track (imported file vs. the video's own audio)
        # "Mute video (use imported audio)" currently points to.
        self.player.sync_audio_source()

    # ── Toolbar ───────────────────────────────────────────────────────────
    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        
        # Set background color
        tb.setStyleSheet("""
            QToolBar {
                background: #1a1840;
                border-bottom: 2px solid #3a3860;
            }
            QToolBar QToolButton {
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px 6px;
                color: #e0e0f0;
            }
            QToolBar QToolButton:hover {
                background: #3a3870;
            }
            QToolBar QToolButton:pressed {
                background: #6050c0;
            }
        """)
        
        tb.setMovable(False)
        tb.setIconSize(QSize(24, 24))

        def _act(icon_name: str, label: str, slot, shortcut=None, tip=None):
            """Create a toolbar action with an SVG icon."""
            icon = create_toolbar_icon(icon_name)
            a = QAction(icon, label, self)
            a.triggered.connect(slot)
            if shortcut: a.setShortcut(QKeySequence(shortcut))
            if tip: a.setToolTip(tip)
            tb.addAction(a)
            return a

        # File group
        _act("audio.svg", "Audio", self._load_audio, tip="Load audio file")
        _act("audio-clear.svg", "Clear Audio", self._clear_audio, tip="Clear audio")
        _act("lrc.svg", "LRC", self._load_lrc, tip="Load LRC lyrics")
        _act("lrc-clear.svg", "Clear LRC", self._clear_lrc, tip="Clear LRC")
        _act("bg.svg", "BG", self._load_bg, tip="Load background image")
        _act("bg-clear.svg", "Clear BG", self._clear_bg, tip="Clear background")
        tb.addSeparator()

        # Transport
        self._play_action = _act("play.svg", "Play", self._play_pause, "Space", "Play / Pause")
        _act("stop.svg", "Stop", self._stop, tip="Stop")
        _act("seek-back.svg", "-5s", lambda: self.player.seek(-5), "Left", "Seek back 5s")
        _act("seek-forward.svg", "+5s", lambda: self.player.seek(+5), "Right", "Seek forward 5s")
        tb.addSeparator()

        # Settings persistence
        _act("save.svg", "Save", self._save_settings, "Ctrl+S", "Save settings")
        _act("load.svg", "Load", self._load_settings, tip="Load settings")
        tb.addSeparator()

        # Undo/redo
        _act("undo.svg", "Undo", self._undo_action, "Ctrl+Z")
        _act("redo.svg", "Redo", self._redo_action, "Ctrl+Y")
        tb.addSeparator()

        # Export
        _act("export.svg", "Export", self._export, tip="Export full video")
        _act("export-preview.svg", "Preview Export", self._export_preview, tip="Export 30s clip")
        tb.addSeparator()

        # About
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        tb.addAction(about_action)

        # Playback state label (right-aligned)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)
        self._state_label = QLabel("● STOPPED")
        self._state_label.setStyleSheet("color:#cc4444;padding-right:12px;font-weight:bold;")
        tb.addWidget(self._state_label)

    # ── Central widget ────────────────────────────────────────────────────
    def _build_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_h = QHBoxLayout(central)
        main_h.setSpacing(4); main_h.setContentsMargins(4,4,4,4)

        # ── Horizontal splitter: left panel | right preview ─────────────
        h_split = QSplitter(Qt.Orientation.Horizontal)
        h_split.setChildrenCollapsible(False)

        # ── LEFT: Settings tabs ───────────────────────────────────────────
        self._left_tabs = QTabWidget()
        self._left_tabs.setMinimumWidth(300)
        self._left_tabs.setMaximumWidth(420)

        # Tab 1: Style settings
        self._settings_panel = SettingsPanel(self.settings, self.renderer)
        self._settings_panel.changed.connect(self._on_setting_changed)
        self._left_tabs.addTab(self._settings_panel, "Style")

        # Tab 2: Files & Projects
        self._left_tabs.addTab(self._build_files_tab(), "Files")

        # Tab 3: Export
        self._left_tabs.addTab(self._build_export_tab(), "Export")

        h_split.addWidget(self._left_tabs)

        # ── RIGHT: vertical splitter — preview on top, seek+log below ────
        right_split = QSplitter(Qt.Orientation.Vertical)
        right_split.setChildrenCollapsible(False)

        # Preview canvas
        self._preview = PreviewWidget()
        # self._preview.seeked.connect(self._on_seek_click)
        right_split.addWidget(self._preview)

        # Bottom strip: seek bar + time label + log
        bottom_w = QWidget()
        bottom_w.setMaximumHeight(220)
        bottom_v = QVBoxLayout(bottom_w)
        bottom_v.setSpacing(4)
        bottom_v.setContentsMargins(4, 4, 4, 4)

        # Seek bar row
        seek_row = QHBoxLayout()
        self._seek_bar = QSlider(Qt.Orientation.Horizontal)
        self._seek_bar.setRange(0, 10000)          # higher resolution = smoother scrubbing
        self._seek_bar.sliderPressed.connect(lambda: setattr(self, "_seeking", True))
        self._seek_bar.sliderReleased.connect(self._on_seek_released)
        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setStyleSheet("color:#8090a0;font-size:11px;")
        self._time_label.setFixedWidth(90)
        seek_row.addWidget(self._seek_bar)
        seek_row.addWidget(self._time_label)
        bottom_v.addLayout(seek_row)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(60)
        bottom_v.addWidget(self._log)

        right_split.addWidget(bottom_w)
        right_split.setStretchFactor(0, 10)   # preview gets almost all space
        right_split.setStretchFactor(1, 1)

        h_split.addWidget(right_split)

        # Default split: left panel ~360px, rest to preview
        h_split.setSizes([360, 900])

        main_h.addWidget(h_split)
        self._seeking = False

    def _build_files_tab(self) -> QWidget:
        # Wrap everything in a scroll area so long project lists don't overflow
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setContentsMargins(0, 0, 0, 0)
        w = QWidget()
        w.setMinimumWidth(280)
        v = QVBoxLayout(w); v.setSpacing(6); v.setContentsMargins(6, 6, 6, 6)

        def _section(title):
            gb = QGroupBox(title)
            inner = QVBoxLayout(gb)
            inner.setContentsMargins(6, 14, 6, 6)
            v.addWidget(gb); return inner

        # Recent audio
        g = _section("Recent Audio")
        self._recent_audio_list = self._recent_list_widget(
            g, self.settings.recent_audio, self._load_audio_path)

        # Recent LRC
        g = _section("Recent LRC")
        self._recent_lrc_list = self._recent_list_widget(
            g, self.settings.recent_lrc, self._load_lrc_path)

        # Recent BG
        g = _section("Recent Backgrounds")
        self._recent_bg_list = self._recent_list_widget(
            g, self.settings.recent_bg, self._load_bg_path)

        # Settings Presets
        g = _section("Settings Presets")
        self._preset_combo = QComboBox()
        self._preset_combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._preset_combo.wheelEvent = lambda e: e.ignore()
        g.addWidget(self._preset_combo)
        preset_btn_row = QHBoxLayout()
        load_preset_btn = QPushButton("📂 Load")
        load_preset_btn.clicked.connect(self._load_preset_selected)
        save_preset_btn = QPushButton("💾 Save As…")
        save_preset_btn.setProperty("class", "action")
        save_preset_btn.clicked.connect(self._save_preset)
        del_preset_btn = QPushButton("✕")
        del_preset_btn.setFixedWidth(28)
        del_preset_btn.setProperty("class", "danger")
        del_preset_btn.clicked.connect(self._delete_preset_selected)
        preset_btn_row.addWidget(load_preset_btn)
        preset_btn_row.addWidget(save_preset_btn)
        preset_btn_row.addWidget(del_preset_btn)
        g.addLayout(preset_btn_row)
        self._refresh_presets_ui()

        # Projects
        g = _section("Recent Projects")
        save_btn = QPushButton("💾 Save Current as Project")
        save_btn.clicked.connect(self._save_project)
        g.addWidget(save_btn)
        self._proj_layout = g
        self._refresh_projects_ui()

        v.addStretch()
        scroll.setWidget(w)
        return scroll

    def _recent_list_widget(self, layout, paths, load_fn) -> QVBoxLayout:
        """Create a vertical list of recent-file buttons inside layout."""
        inner = QVBoxLayout()
        inner.setSpacing(2)
        valid = [x for x in paths if os.path.exists(x)]
        if not valid:
            lbl = QLabel("  (none)")
            lbl.setStyleSheet("color:#606080;font-size:10px;")
            inner.addWidget(lbl)
        for p in valid:
            name = os.path.basename(p)
            if len(name) > 32: name = name[:29] + "…"
            btn = QPushButton(name)
            btn.setToolTip(p)
            btn.setStyleSheet("text-align:left;padding-left:6px;font-size:11px;")
            btn.clicked.connect(lambda _, path=p: load_fn(path))
            inner.addWidget(btn)
        layout.addLayout(inner)
        return inner

    def _build_export_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w); v.setSpacing(8); v.setContentsMargins(8,8,8,8)

        self._export_progress = QProgressBar()
        self._export_progress.setRange(0,100); self._export_progress.setValue(0)
        self._export_progress.setVisible(False)
        v.addWidget(self._export_progress)

        self._export_log = QTextEdit()
        self._export_log.setReadOnly(True)
        v.addWidget(self._export_log)

        btn_row = QHBoxLayout()
        export_btn = QPushButton("🎬 Export Full Video")
        export_btn.setProperty("class","action")
        export_btn.clicked.connect(self._export)
        preview_btn = QPushButton("🎞 Export Preview (30s)")
        preview_btn.clicked.connect(self._export_preview)
        cancel_btn  = QPushButton("✕ Cancel")
        cancel_btn.setProperty("class","danger")
        cancel_btn.clicked.connect(self._cancel_export)
        self._cancel_btn = cancel_btn
        cancel_btn.setVisible(False)
        btn_row.addWidget(export_btn); btn_row.addWidget(preview_btn); btn_row.addWidget(cancel_btn)
        v.addLayout(btn_row)
        return w

    # ── Status bar ────────────────────────────────────────────────────────
    def _build_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_lbl = QLabel("Ready")
        sb.addPermanentWidget(self._status_lbl)

    def _status(self, msg: str):
        self._status_lbl.setText(msg)

    # ── Render tick ───────────────────────────────────────────────────────
    def _tick(self):
        now = time.time(); dt = min(0.05, now - self._last_t); self._last_t = now
        elapsed = self.player.get_elapsed()

        # Throttle to ~30 fps when idle to reduce CPU; full 60 fps when playing
        if not self.player.playing:
            self._idle_skip = getattr(self, "_idle_skip", 0) + 1
            if self._idle_skip < 2:
                return
            self._idle_skip = 0
        else:
            self._idle_skip = 0


        # ── PCM / visualizer data (only when needed) ──────────────────────
        s = self.settings
        need_pcm = (getattr(s,"visualizer_enabled",False) or
                    getattr(s,"bg_pulse_enabled",False) or
                    getattr(s,"lights_enabled",False))
        if need_pcm and self.player.playing:
            bands = self.player.get_visualizer_bands(
                elapsed, getattr(s,"visualizer_bands",32))
            self.renderer.pcm_bands            = bands
            self.renderer._raw_bass_energy     = getattr(self.player,"_raw_bass_energy",0.0)
            self.renderer._pulse_spectrum      = getattr(self.player,"_pulse_spectrum",None)
            self.renderer._pulse_spectrum_bins = getattr(self.player,"_pulse_spectrum_bins",1)
            self.renderer._pulse_spectrum_rate = getattr(self.player,"_pulse_spectrum_rate",44100)
        else:
            self.renderer.pcm_bands = None
            self.renderer._raw_bass_energy = 0.0

        # ── Keep the preview surface's aspect ratio in sync with whichever
        #    export resolution (16:9, 9:16 vertical, etc.) is selected ─────
        pv_size = self._compute_preview_size()
        if self._pg_surf.get_size() != pv_size:
            self._pg_surf = pygame.Surface(pv_size)
            self.renderer.invalidate_bg()   # background needs to be re-fit to the new canvas size

        # ── Video background thread sync ──────────────────────────────────
        self.video_bg.set_render_params(pv_size, s.bg_blur)
        self.video_bg.notify_elapsed(elapsed, self.player.playing)

        # ── Render frame into offscreen pygame surface ────────────────────
        self._pg_surf.fill(C_BG)
        self.renderer.render(self._pg_surf, self.player.lines, elapsed, dt, self.player.playing)

        self._preview.display_surface(self._pg_surf)


        # ── Seek bar + time label ─────────────────────────────────────────
        # Cache duration — get_audio_duration() spawns ffprobe, never call it every tick
        if not self._seeking:
            if self._dur_cache is None and s.audio_path:
                self._dur_cache = get_audio_duration(s.audio_path)
            dur = self._dur_cache
            if dur and dur > 0:
                new_val = int(elapsed / dur * 10000)
                if abs(new_val - self._seek_bar.value()) > 1:
                    self._seek_bar.setValue(new_val)
            m, sec = divmod(int(elapsed), 60)
            dm, ds  = divmod(int(dur or 0), 60)
            new_time = f"{m}:{sec:02d} / {dm}:{ds:02d}"
            if new_time != self._last_time_str:
                self._time_label.setText(new_time)
                self._last_time_str = new_time

        # ── State pill — setStyleSheet is expensive; only call on change ──
        if self.player.playing:   new_state = "playing"
        elif self.player.paused:  new_state = "paused"
        else:                     new_state = "stopped"
        if new_state != self._last_player_state:
            self._last_player_state = new_state
            if new_state == "playing":
                self._state_label.setText("● PLAYING")
                self._state_label.setStyleSheet(
                    "color:#44cc44;padding-right:12px;font-weight:bold;")
                # Update play/pause icon
                self._play_action.setIcon(create_toolbar_icon("pause.svg"))
            elif new_state == "paused":
                self._state_label.setText("● PAUSED")
                self._state_label.setStyleSheet(
                    "color:#ccaa00;padding-right:12px;font-weight:bold;")
                self._play_action.setIcon(create_toolbar_icon("play.svg"))
            else:
                self._state_label.setText("● STOPPED")
                self._state_label.setStyleSheet(
                    "color:#cc4444;padding-right:12px;font-weight:bold;")
                self._play_action.setIcon(create_toolbar_icon("play.svg"))

    # ── File actions ──────────────────────────────────────────────────────
    def _load_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio", "",
            "Audio (*.mp3 *.wav *.ogg *.flac *.aac *.m4a *.mp4 *.mkv *.mov)")
        if path: self._load_audio_path(path)

    def _load_audio_path(self, path: str):
        try:
            self.player.load_audio(path)
            self.settings.audio_path = path
            self.settings.push_recent_audio(path)
            self.settings.save()
            self._dur_cache = None          # force re-probe on next tick
            self._last_time_str = ""
            self._status(f"Audio: {os.path.basename(path)}")
            self._log_msg(f"Loaded audio: {os.path.basename(path)}")
        except Exception as e:
            self._status(f"Error: {e}")

    def _clear_audio(self):
        self.player.stop(); pygame.mixer.music.unload()
        self.player.audio_loaded = False
        self.settings.audio_path = None; self.settings.save()
        self._dur_cache = None
        self._last_time_str = ""
        self._status("Audio cleared.")

    def _load_lrc(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select LRC", "", "LRC (*.lrc)")
        if path: self._load_lrc_path(path)

    def _load_lrc_path(self, path: str):
        try:
            self.player.load_lrc(path)
            self.settings.lrc_path = path
            self.settings.push_recent_lrc(path)
            meta = extract_lrc_metadata(path)
            self.settings._lrc_meta_title  = meta.get("title","")
            self.settings._lrc_meta_artist = meta.get("artist","")
            self.settings.save()
            self._status(f"LRC: {os.path.basename(path)}")
            self._log_msg(f"Loaded lyrics: {os.path.basename(path)}")
        except Exception as e:
            self._status(f"Error: {e}")

    def _clear_lrc(self):
        self.player.lines = []; self.player.stop()
        self.settings.lrc_path = None; self.settings.save()
        self._status("LRC cleared.")

    def _load_bg(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Background", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path: self._load_bg_path(path)

    def _load_bg_path(self, path: str):
        self.settings.bg_image_path = path
        self.settings.push_recent_bg(path)
        self.settings.save()
        self.renderer.invalidate()
        self._status(f"BG: {os.path.basename(path)}")

    def _clear_bg(self):
        self.settings.bg_image_path = None; self.settings.save()
        self.renderer.invalidate_bg()
        self._status("Background cleared.")

    # ── Transport ─────────────────────────────────────────────────────────
    def _play_pause(self):
        if self.player.playing:
            self.player.pause()
            self._log_msg("Paused.")
            self._play_action.setIcon(create_toolbar_icon("play.svg"))
        elif self.player.paused:
            self.player.resume()
            self._log_msg("Resumed.")
            self._play_action.setIcon(create_toolbar_icon("pause.svg"))
        else:
            self.player.play()
            self._log_msg("Playing.")
            self._play_action.setIcon(create_toolbar_icon("pause.svg"))

    def _stop(self):
        self.player.stop()
        self._log_msg("Stopped.")
        self._play_action.setIcon(create_toolbar_icon("play.svg"))

    # ── Seek bar interaction ──────────────────────────────────────────────
    # def _on_seek_click(self, pct: float):
    #     dur = self._dur_cache or self.player.get_duration()
    #     if dur: self.player.seek_to(pct * dur)

    def _on_seek_released(self):
        self._seeking = False
        pct = self._seek_bar.value() / 10000.0
        dur = self._dur_cache or self.player.get_duration()
        if dur: self.player.seek_to(pct * dur)

    # ── Settings persistence ──────────────────────────────────────────────
    def _on_setting_changed(self):
        self.settings.save()
        # Cheap no-op unless the effective audio source (imported file vs.
        # video's own audio) actually changed — covers toggling "Mute video"
        # and picking/clearing a background video mid-session.
        self.player.sync_audio_source()

    def _save_settings(self):
        self.settings.save()
        self._status("Settings saved.")

    def _load_settings(self):
        self.settings.load()
        self._settings_panel.refresh()
        self.renderer.invalidate()
        self._status("Settings loaded.")

    # ── Undo / Redo ───────────────────────────────────────────────────────
    def _snapshot(self) -> dict:
        return json.loads(json.dumps(self.settings.save_dict()))

    def push_undo(self):
        snap = self._snapshot()
        if self._undo and self._undo[-1] == snap: return
        self._undo.append(snap)
        if len(self._undo) > UNDO_MAX: self._undo.pop(0)
        self._redo.clear()

    def _undo_action(self):
        if not self._undo: self._status("Nothing to undo."); return
        self._redo.append(self._snapshot())
        self.settings.load_dict(self._undo.pop())
        self._settings_panel.refresh(); self.renderer.invalidate()
        self._status("Undo.")

    def _redo_action(self):
        if not self._redo: self._status("Nothing to redo."); return
        self._undo.append(self._snapshot())
        self.settings.load_dict(self._redo.pop())
        self._settings_panel.refresh(); self.renderer.invalidate()
        self._status("Redo.")

    # ── Settings Profiles ─────────────────────────────────────────────────
    def _profile_path(self, name: str) -> str:
        os.makedirs(PROFILES_DIR, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in " -_()" else "_" for c in name).strip()
        return os.path.join(PROFILES_DIR, safe+".json")

    def _list_profiles(self) -> List[str]:
        os.makedirs(PROFILES_DIR, exist_ok=True)
        return sorted(os.path.splitext(f)[0]
                      for f in os.listdir(PROFILES_DIR) if f.endswith(".json"))

    def _refresh_presets_ui(self):
        """Repopulate the preset combo box from disk."""
        self._preset_combo.clear()
        profiles = self._list_profiles()
        if not profiles:
            self._preset_combo.addItem("(no presets saved)")
            self._preset_combo.setEnabled(False)
        else:
            self._preset_combo.setEnabled(True)
            self._preset_combo.addItems(profiles)

    def _save_preset(self):
        """Save the current settings as a named preset."""
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        path = self._profile_path(name)
        try:
            data = {k: v for k, v in self.settings.save_dict().items()
                     if k not in PRESET_EXCLUDED_KEYS}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._refresh_presets_ui()
            idx = self._preset_combo.findText(name)
            if idx >= 0:
                self._preset_combo.setCurrentIndex(idx)
            self._status(f"Preset saved: {name}")
            self._log_msg(f"Saved preset: {name}")
        except Exception as e:
            self._status(f"Error saving preset: {e}")

    def _load_preset_selected(self):
        if not self._preset_combo.isEnabled():
            return
        name = self._preset_combo.currentText()
        if name:
            self._load_preset(name)

    def _load_preset(self, name: str):
        """Load a named preset, replacing the current settings."""
        path = self._profile_path(name)
        if not os.path.exists(path):
            self._status(f"Preset not found: {name}")
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data = {k: v for k, v in data.items() if k not in PRESET_EXCLUDED_KEYS}
            self.push_undo()   # allow undoing a preset load
            self.settings.load_dict(data)
            self._settings_panel.refresh()
            self.renderer.invalidate()
            self.settings.save()
            self._status(f"Preset loaded: {name}")
            self._log_msg(f"Loaded preset: {name}")
        except Exception as e:
            self._status(f"Error loading preset: {e}")

    def _delete_preset_selected(self):
        if not self._preset_combo.isEnabled():
            return
        name = self._preset_combo.currentText()
        if not name:
            return
        reply = QMessageBox.question(
            self, "Delete Preset", f"Delete preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        path = self._profile_path(name)
        try:
            if os.path.exists(path):
                os.remove(path)
            self._refresh_presets_ui()
            self._status(f"Preset deleted: {name}")
            self._log_msg(f"Deleted preset: {name}")
        except Exception as e:
            self._status(f"Error deleting preset: {e}")

    # ── Recent Projects ───────────────────────────────────────────────────
    def _load_projects(self) -> list:
        if not os.path.exists(PROJECTS_PATH): return []
        try:
            with open(PROJECTS_PATH,"r") as f: return json.load(f)
        except: return []

    def _save_projects(self):
        with open(PROJECTS_PATH,"w") as f: json.dump(self._projects,f,indent=2)

    def _save_project(self):
        audio = self.settings.audio_path
        if not audio: self._status("Load audio first."); return
        name = os.path.splitext(os.path.basename(audio))[0]
        entry={"name":name,"audio":audio,"lrc":self.settings.lrc_path,
               "bg":self.settings.bg_image_path}
        self._projects=[p for p in self._projects if p.get("audio")!=audio]
        self._projects.insert(0,entry)
        if len(self._projects)>PROJECTS_MAX: self._projects=self._projects[:PROJECTS_MAX]
        self._save_projects()
        self._refresh_projects_ui()
        self._status(f"Project saved: {name}")

    def _open_project(self, entry: dict):
        if entry.get("audio") and os.path.exists(entry["audio"]):
            self._load_audio_path(entry["audio"])
        if entry.get("lrc") and os.path.exists(entry["lrc"]):
            self._load_lrc_path(entry["lrc"])
        if entry.get("bg") and os.path.exists(entry["bg"]):
            self._load_bg_path(entry["bg"])
        self._status(f"Opened: {entry.get('name','?')}")

    def _refresh_projects_ui(self):
        # Remove old project buttons (keep the "Save" button at index 0)
        while self._proj_layout.count() > 1:
            item = self._proj_layout.takeAt(1)
            if item.widget(): item.widget().deleteLater()
        for entry in self._projects:
            row = QHBoxLayout()
            name = entry.get("name","?")
            ob = QPushButton(f"▶ {name[:22]}")
            ob.clicked.connect(lambda _, e=entry: self._open_project(e))
            db = QPushButton("✕")
            db.setFixedWidth(28); db.setProperty("class","danger")
            db.clicked.connect(lambda _, e=entry: self._remove_project(e))
            row.addWidget(ob); row.addWidget(db)
            self._proj_layout.addLayout(row)

    def _remove_project(self, entry: dict):
        self._projects=[p for p in self._projects if p is not entry]
        self._save_projects(); self._refresh_projects_ui()

    # ── Export ────────────────────────────────────────────────────────────
    def _export(self):
        if not self.player.audio_loaded:
            self._status("Load audio first.")
            return
        
        # ─── Show confirmation dialog FIRST ──────────────────────────────────
        # Pass dummy path for now, will get real path after user confirms
        if not self._show_export_confirmation("(select location after confirmation)"):
            self._status("Export cancelled.")
            return
        
        # ─── Then show file picker ──────────────────────────────────────────
        audio = self.settings.audio_path or ""
        stem = os.path.splitext(os.path.basename(audio))[0] if audio else "gallops_studio"
        out, _ = QFileDialog.getSaveFileName(self, "Save Video", f"{stem}.mp4", "MP4 (*.mp4)")
        if not out:
            self._status("Export cancelled.")
            return
        
        self._start_export(out)

    def _export_preview(self):
        if not self.player.audio_loaded:
            self._status("Load audio first.")
            return
        
        pos = self.player.get_elapsed()
        dur = 30.0
        start = max(0.0, pos - dur/2)
        
        # ─── Show confirmation dialog FIRST ──────────────────────────────────
        if not self._show_export_confirmation("(select location after confirmation)", start_time=start, duration=dur):
            self._status("Export cancelled.")
            return
        
        # ─── Then show file picker ──────────────────────────────────────────
        audio = self.settings.audio_path or ""
        stem = os.path.splitext(os.path.basename(audio))[0] if audio else "gallops"
        out, _ = QFileDialog.getSaveFileName(
            self,
            "Save Preview",
            f"{stem}_preview_{int(start)}s.mp4",
            "MP4 (*.mp4)"
        )
        if not out:
            self._status("Export cancelled.")
            return
        
        self._start_export(out, start_time=start, duration=dur)

    def _start_export(self, out_path, start_time=0.0, duration=None):
        self._export_progress.setValue(0)
        self._export_progress.setVisible(True)
        self._cancel_btn.setVisible(True)
        self._left_tabs.setCurrentIndex(2)   # switch to Export tab
        self._export_log.clear()
        worker = ExportWorker(
            self.player, self.renderer, self.settings, self.video_bg,
            out_path, self.settings.export_fps, start_time, duration)
        worker.progress.connect(lambda p: self._export_progress.setValue(int(p*100)))
        worker.log.connect(self._export_log.append)
        worker.finished.connect(self._on_export_finished)
        self._export_worker = worker
        worker.start()
        self._status(f"Exporting → {os.path.basename(out_path)}")

    def _cancel_export(self):
        if self._export_worker: self._export_worker.cancel()

    def _on_export_finished(self, ok: bool, msg: str):
        self._export_progress.setVisible(False)
        self._cancel_btn.setVisible(False)
        self._export_worker = None
        if ok:
            self._status(f"✓ Export done: {os.path.basename(msg)}")
            self._log_msg(f"Export completed: {msg}")
        else:
            self._status(f"✗ Export failed: {msg}")
            self._log_msg(f"Export failed: {msg}")

    # ── About ─────────────────────────────────────────────────────────────
    def _show_about(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("About Gallops Studio")
        dlg.setMinimumWidth(400)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("<h2>Gallops Studio</h2>"))
        v.addWidget(QLabel("Karaoke Lyric Video Studio — PyQt6 Edition"))
        v.addWidget(QLabel("Version 1.0.0  ·  © 2026 Jay-ar Volante / Gallops Sound"))
        from PyQt6.QtWidgets import QDialogButtonBox
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bb.accepted.connect(dlg.accept)
        yt = QPushButton("▶ YouTube: @GallopsSound")
        yt.clicked.connect(lambda: __import__("webbrowser").open("https://www.youtube.com/@GallopsSound"))
        v.addWidget(yt); v.addWidget(bb)
        dlg.exec()

    # ── Helpers ───────────────────────────────────────────────────────────
    def _log_msg(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self._log.append(f"[{ts}] {msg}")

    def closeEvent(self, e):
        self.settings.save()
        self._timer.stop()
        if self._export_worker and self._export_worker.isRunning():
            self._export_worker.cancel()
            self._export_worker.wait(3000)
        self.video_bg.close()
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except Exception:
            pass
        e.accept()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Space:    self._play_pause()
        elif e.key() == Qt.Key.Key_Left:   self.player.seek(-5)
        elif e.key() == Qt.Key.Key_Right:  self.player.seek(+5)
        elif e.key() == Qt.Key.Key_S:      self._stop()
        else: super().keyPressEvent(e)

    def _show_export_confirmation(self, out_path: str, start_time: float = 0.0, duration: float = None) -> bool:
        """Show a confirmation dialog with song info before exporting."""
        
        # Gather song info
        title = getattr(self.settings, "startup_info_title", "").strip()
        artist = getattr(self.settings, "startup_info_artist", "").strip()
        
        # Fallback to LRC metadata if fields are empty
        if not title:
            title = getattr(self.settings, "_lrc_meta_title", "").strip()
        if not artist:
            artist = getattr(self.settings, "_lrc_meta_artist", "").strip()
        
        # If still empty, try to get from filename
        if not title and self.settings.audio_path:
            title = os.path.splitext(os.path.basename(self.settings.audio_path))[0]
        
        # Get duration info
        dur = self._dur_cache or self.player.get_duration()
        dur_str = f"{int(dur // 60)}:{int(dur % 60):02d}" if dur else "Unknown"
        
        # Get export settings
        if self.settings.use_custom_settings:
            preset = f"Custom (CRF {self.settings.custom_crf}, {self.settings.custom_preset})"
        else:
            preset = self.settings.video_preset
        
        resolution = self.settings.video_resolution
        fps = self.settings.export_fps
        
        # Build the confirmation dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Confirm Export")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(380)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # ─── Header ──────────────────────────────────────────────────────────
        header_text = "🎬 Export Full Video" if not duration else "🎞 Export Preview (30s)"
        header = QLabel(header_text)
        header.setStyleSheet("font-size:18px; font-weight:bold; color:#a090ff;")
        layout.addWidget(header)
        
        layout.addWidget(QLabel("─" * 50))
        
        # ─── Song Info Section ──────────────────────────────────────────────
        info_group = QGroupBox("Song Information")
        info_group.setStyleSheet("QGroupBox { font-weight:bold; }")
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(12, 18, 12, 12)
        
        # Title row with edit button
        title_layout = QHBoxLayout()
        title_label = QLabel(title if title else "⚠️ No title set")
        title_label.setStyleSheet("color:#80c0ff; font-size:13px; font-weight:bold;" if title else "color:#ff6666; font-size:13px; font-weight:bold;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        edit_title_btn = QPushButton("✏️ Edit")
        edit_title_btn.setFixedWidth(60)
        edit_title_btn.clicked.connect(lambda: self._edit_title_dialog(dialog, title_label))
        title_layout.addWidget(edit_title_btn)
        info_layout.addRow("🎵 Title:", title_layout)
        
        # Artist row with edit button
        artist_layout = QHBoxLayout()
        artist_label = QLabel(artist if artist else "⚠️ No artist set")
        artist_label.setStyleSheet("color:#80c0ff; font-size:13px; font-weight:bold;" if artist else "color:#ff6666; font-size:13px; font-weight:bold;")
        artist_layout.addWidget(artist_label)
        artist_layout.addStretch()
        edit_artist_btn = QPushButton("✏️ Edit")
        edit_artist_btn.setFixedWidth(60)
        edit_artist_btn.clicked.connect(lambda: self._edit_artist_dialog(dialog, artist_label))
        artist_layout.addWidget(edit_artist_btn)
        info_layout.addRow("👤 Artist:", artist_layout)
        
        if self.settings.lrc_path:
            info_layout.addRow("📄 LRC:", QLabel(os.path.basename(self.settings.lrc_path)))
        
        layout.addWidget(info_group)
        
        # ─── Export Settings ────────────────────────────────────────────────
        settings_group = QGroupBox("Export Settings")
        settings_group.setStyleSheet("QGroupBox { font-weight:bold; }")
        settings_layout = QFormLayout(settings_group)
        settings_layout.setSpacing(6)
        settings_layout.setContentsMargins(12, 18, 12, 12)
        
        # Show output filename if it's a real path (not the dummy placeholder)
        if out_path and not out_path.startswith("(select location"):
            settings_layout.addRow("📁 Output:", QLabel(os.path.basename(out_path)))
        else:
            settings_layout.addRow("📁 Output:", QLabel("📂 Will ask for location after confirmation"))
        
        settings_layout.addRow("⏱️ Duration:", QLabel(f"{dur_str}"))
        settings_layout.addRow("📐 Resolution:", QLabel(resolution))
        settings_layout.addRow("🎞️ FPS:", QLabel(str(fps)))
        settings_layout.addRow("⚙️ Preset:", QLabel(preset))
        
        if duration:
            settings_layout.addRow("⏳ Clip Length:", QLabel(f"{duration:.0f}s (preview)"))
        
        layout.addWidget(settings_group)
        
        # ─── Warning if no title/artist ────────────────────────────────────
        if not title or not artist:
            warn = QLabel("⚠️  Warning: Title or artist is missing!")
            warn.setStyleSheet("color:#ffaa00; font-weight:bold; padding:4px; background:#2a1a00; border-radius:4px;")
            layout.addWidget(warn)
        
        # ─── File size estimate ─────────────────────────────────────────────
        if dur and duration:
            estimated_dur = duration
        elif dur:
            estimated_dur = dur
        else:
            estimated_dur = 180  # 3 minutes default
        
        # Rough estimate: ~10MB per minute for 1080p at medium quality
        mb_per_min = 10 if "1080" in resolution else (6 if "720" in resolution else 15)
        if "4K" in resolution:
            mb_per_min = 40
        elif "1440" in resolution:
            mb_per_min = 25
        
        estimated_size = int((estimated_dur / 60) * mb_per_min)
        size_label = QLabel(f"💾 Estimated size: ~{estimated_size} MB")
        size_label.setStyleSheet("color:#8090a0; font-size:11px;")
        layout.addWidget(size_label)
        
        # ─── Hint about editing ─────────────────────────────────────────────
        hint = QLabel("💡 Tip: Click ✏️ Edit to update title/artist before exporting")
        hint.setStyleSheet("color:#607080; font-size:10px; font-style:italic;")
        layout.addWidget(hint)
        
        # ─── Buttons ────────────────────────────────────────────────────────
        button_box = QDialogButtonBox()
        cancel_btn = button_box.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        export_btn = button_box.addButton("✅ Proceed to Export", QDialogButtonBox.ButtonRole.AcceptRole)
        export_btn.setProperty("class", "action")
        export_btn.setStyleSheet("""
            QPushButton {
                background: #1a6a2a;
                border: 1px solid #338833;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #207030;
            }
        """)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        
        layout.addWidget(button_box)
        
        # ─── Execute ────────────────────────────────────────────────────────
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted


    def _edit_title_dialog(self, parent: QDialog, label: QLabel):
        """Edit the title in a mini dialog."""
        current = getattr(self.settings, "startup_info_title", "").strip()
        if not current:
            current = getattr(self.settings, "_lrc_meta_title", "").strip()
        
        text, ok = QInputDialog.getText(
            parent,
            "Edit Title",
            "Enter song title:",
            QLineEdit.EchoMode.Normal,
            current
        )
        if ok and text:
            self.settings.startup_info_title = text
            label.setText(text)
            label.setStyleSheet("color:#80c0ff; font-size:13px; font-weight:bold;")
            self.settings.save()
            self._status(f"Title updated: {text}")

    def _edit_artist_dialog(self, parent: QDialog, label: QLabel):
        """Edit the artist in a mini dialog."""
        current = getattr(self.settings, "startup_info_artist", "").strip()
        if not current:
            current = getattr(self.settings, "_lrc_meta_artist", "").strip()
        
        text, ok = QInputDialog.getText(
            parent,
            "Edit Artist",
            "Enter artist name:",
            QLineEdit.EchoMode.Normal,
            current
        )
        if ok and text:
            self.settings.startup_info_artist = text
            label.setText(text)
            label.setStyleSheet("color:#80c0ff; font-size:13px; font-weight:bold;")
            self.settings.save()
            self._status(f"Artist updated: {text}")


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def main():
    # ── pygame: SDL_VIDEODRIVER=dummy MUST be set before pygame.init() ────
    # This prevents SDL from trying to open a real window (we render into
    # a QLabel via QImage instead).  The audio driver is left alone so
    # pygame.mixer produces real sound output on the system speakers.
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    # Do NOT set SDL_AUDIODRIVER — let pygame pick the best real driver
    # (DirectSound / WASAPI on Windows, PulseAudio / ALSA on Linux, etc.)

    pygame.init()
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    except Exception as e:
        print(f"[mixer] init warning: {e}")

    # ── Qt application ────────────────────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName("Gallops Studio")
    # The stylesheet below only sets pixel-based font-size (e.g. "font-size:11px"),
    # never a point size. Some Qt code paths (tooltips, native dialogs, HiDPI
    # scaling) still query QFont.pointSize() on the app's default font, and if
    # that font was never given an explicit point size, Qt logs:
    #   "QFont::setPointSize: Point size <= 0 (-1), must be greater than 0"
    # Giving the app a base font with a real point size up front avoids that.
    base_font = QFont("Segoe UI" if IS_WINDOWS else ("Helvetica Neue" if IS_MAC else "Sans Serif"))
    base_font.setPointSize(9)
    app.setFont(base_font)
    app.setStyleSheet(DARK_QSS)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()