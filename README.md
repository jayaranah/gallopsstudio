# Gallops Studio 🎤🎬

**Gallops Studio** is a desktop karaoke lyric-video maker built with **PyQt6** (UI) and **pygame** (rendering engine). Load a song and a synced `.lrc` lyric file, customize the look with dozens of visual effects, preview it live, and export a finished MP4 with `ffmpeg`.

---

## ✨ Features

### Karaoke Engine
- **Word/syllable-level LRC parsing** — supports enhanced LRC format with `<mm:ss.xx>` syllable timestamps for precise word-by-word highlighting.
- **Two-line "teleprompter" display** — current line and the next line are shown together and slide/fade as the song progresses.
- **Wipe highlight** — a moving light sweep tracks the currently sung syllable.
- **Countdown bar** — a gradient progress bar above each line counts down to when it starts.
- **4 lyric render styles**: `filled`, `outline`, `glow`, `gradient`.
- Adjustable **outer glow** (radius, brightness, intensity, opacity, color, distance), **stroke/outline**, **drop shadow**, and **line spacing**.
- Custom **lyric background pill** — solid color or a tiled/stretched/fitted image, with adjustable opacity, corner radius, and padding.

### Backgrounds
- Static **image background** with adjustable Gaussian blur.
- **Video background** support (via OpenCV) with its own decode thread, including the option to use the video's original audio track instead of (or as well as) an imported audio file.
- **Audio-reactive background pulse/zoom** — the background subtly zooms in time with bass energy, with tunable frequency range, threshold, oscillation, and zoom amount.

### Visual Effects (all independently toggleable)
- **Audio visualizer** — bars, mirror-bars, or waveform, driven by a real FFT of the loaded audio.
- **Falling snow** — count, speed, size, opacity, and wind.
- **Falling hearts** — custom SVG icon support (with optional color-overlay tinting or the SVG's native colors), size range, speed, opacity, and count.
- **Dancing stage lights** — up to 30 beams with 10 movement patterns (`random`, `sync`, `wave`, `alternate`, `converge`, `chase`, `spiral`, `figure8`, `pulse`, `shuffle`), rainbow color cycling, beat-reactive brightness/blink, and optional neon glow.
- **Startup info card** — an animated title/artist card that slides in from any edge at the start of playback, with optional animated neon border, configurable delay/duration, and position offset.

### Playback & Editing
- Live preview rendered at up to 60 fps, matching the aspect ratio of your chosen export resolution (including vertical 9:16).
- Transport controls: play/pause, stop, ±5s seek, and a scrubbable seek bar with time display.
- **Undo/redo** for all settings changes (up to 50 steps).
- **Settings presets** — save/load a full "look" (excluding the currently loaded media files) as a named preset.
- **Recent projects** — remembers your last audio/LRC/background combos so you can reopen a song instantly.
- **Recent files** lists for audio, LRC, and background images.
- Session auto-restore — reopens your last-used audio, lyrics, and background on launch.

### Export
- Powered by `ffmpeg`, streamed frame-by-frame from the renderer (no intermediate frame files).
- **Quality presets**: Archive/Master, YouTube/1080p, Standard/720p, Social Media, Mobile/Quick — or full **custom settings** (CRF, encoder preset, codec, tune, H.264 profile, two-pass, target file size).
- **Codecs**: H.264 (`libx264`), H.265 (`libx265`), VP9 (`libvpx-vp9`).
- **Resolutions**: 480p, 720p, 1080p, 1440p, 4K, and 1080p Vertical (9:16).
- Configurable export FPS and audio bitrate.
- **Export confirmation dialog** — review title, artist, LRC file, resolution, FPS, preset, estimated duration, and estimated file size before exporting; edit title/artist inline if missing.
- **30-second preview export** centered on your current playback position — great for quickly test-rendering effects before committing to a full export.
- Live progress bar, exportable log, and cancel support.

### Fonts
- Auto-discovers system fonts (Windows/macOS/Linux) plus any custom `.ttf`/`.otf` files placed in a local `fonts/` folder next to the script.

---

## 📋 Requirements

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/) and `ffprobe` available on your system PATH (or placed next to the script as `ffmpeg`/`ffmpeg.exe`)
- Python packages:
  ```bash
  pip install PyQt6 pygame numpy Pillow opencv-python
  ```
  > `opencv-python` is only required if you want to use **video backgrounds**. Everything else works without it.

---

## 🚀 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/jayaranah/gallopsstudio.git
   cd gallops-studio
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python gallops_studio.py
   ```

### Optional folders

Place these next to `gallops_studio.py` to unlock extra assets (all optional — the app falls back gracefully if they're missing):

| Folder | Purpose |
|---|---|
| `fonts/` | Drop in `.ttf`/`.otf` files to make them selectable as lyric fonts |
| `hearts/heart.svg` | Default heart shape used by the Falling Hearts effect |
| `icons/` | Toolbar SVG icons (falls back to plain colored squares if missing) |

---

## 🕹️ Usage

1. **Load your files** — use the toolbar (or the **Files** tab) to load an audio file, a synced `.lrc` lyrics file, and optionally a background image or video.
2. **Style it** — open the **Style** tab and tweak fonts, colors, glow/outline, lyric background, singing-guide effects, the startup info card, the audio visualizer, background pulse, snow, hearts, and dancing lights.
3. **Preview** — hit `Space` (or the Play button) to watch your changes live in the preview pane. Seek with the seek bar or `←` / `→` (5s jumps).
4. **Save your look** — save the current settings as a named **preset** to reuse across other songs, or save the whole song as a **project** to reopen later.
5. **Export**:
   - **Export Preview (30s)** to quickly render a clip centered on your current playback position.
   - **Export Full Video** to render the entire song.
   - Review the confirmation dialog (title, artist, resolution, FPS, estimated size), then choose a save location. Progress and logs appear in the **Export** tab.

### LRC format

Standard LRC line timing is supported, plus optional **enhanced/word-level** timestamps for per-syllable highlighting:

```
[ti:Song Title]
[ar:Artist Name]
[00:12.30]<00:12.30>Hel<00:12.55>lo <00:12.80>world
```

### Keyboard Shortcuts

| Key | Action |
|---|---|
| `Space` | Play / Pause |
| `←` | Seek back 5s |
| `→` | Seek forward 5s |
| `S` | Stop |
| `Ctrl+S` | Save settings |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |

---

## 🗂️ Config & Data Locations

Settings, presets, and recent projects are stored in your home directory so they persist between sessions:

- `~/.gallops_studio_config.json` — current settings
- `~/.gallops_studio_profiles/` — saved presets
- `~/.gallops_studio_projects.json` — recent project list

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

---

## 🙌 Credits


Gallops Studio — © 2026 Jay-ar Volante / Gallops Sound / Gallops OPM

[FFmpeg](https://ffmpeg.org/)

[Youtube Channel: Gallops OPM](https://www.youtube.com/@GallopsOPM)

[Youtube Channel: Gallops Sound](https://www.youtube.com/@GallopsSound)

