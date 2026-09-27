# Music Playlist Generator

CLI playlist generator that scans **audio and video**, extracts audio from video automatically, optionally converts the whole library to a selected audio format, builds randomized/fixed-opening playlists, writes timestamped tracklists, and renders a combined FULL audio file.

## Features

- Detects media using **FFprobe audio streams**, not only filenames/extensions.
- Accepts common audio: MP3, WAV, FLAC, M4A, AAC, OGG, OPUS, WMA, AIFF, AC3 and other FFmpeg-readable media.
- Accepts common video: MP4, MKV, MOV, AVI, WebM, MPEG/MPG, M4V, TS/MTS/M2TS, WMV, FLV, 3GP, VOB, OGV and other FFmpeg-readable media with audio.
- Video with audio is automatically extracted/converted; video without a valid audio stream is skipped.
- Conversion choices: **MP3, FLAC, WAV, AAC, M4A, OGG, OPUS**.
- Choose whether existing audio keeps its original format or whether **all audio + video** is converted to the selected format.
- Converted files are cached in `Converted/`; source files are never overwritten or deleted.
- FULL playlist format is selected separately: MP3, FLAC, WAV, AAC, M4A, OGG or OPUS.
- Full Random mode or Custom Fixed Tracks for track #1, #2, #3, etc.; remaining tracks are random.
- Configurable playlist count and target duration.
- Persistent history reduces track reuse and identical playlist sequences where possible.
- `TRACKLIST.txt` contains timestamps and `[FIXED]` labels.
- FULL file is kept inside its playlist folder and copied to top-level `Full/`.

## Requirements

- Python 3.9+
- FFmpeg **and FFprobe** available in PATH

No third-party Python package is required in v3.0.0.

Verify:

```bash
ffmpeg -version
ffprobe -version
```

## Usage

1. Put audio and/or video files in `Music/` (subfolders supported).
2. Run `python music_playlist_generator.py`.
3. Choose conversion format: MP3, FLAC, WAV, AAC, M4A, OGG, or OPUS.
4. Choose whether to keep existing audio formats or convert **ALL audio + video**.
5. Choose Full Random or Custom Fixed Tracks.
6. Set playlist count, target duration, and a separate FULL output format.

## Output

```text
Music/                       # source media
Converted/                   # conversion cache
Playlists/
└── Playlist_1/
    ├── 01. song.mp3
    ├── 02. clip.mp3
    ├── TRACKLIST.txt
    └── Playlist_1_FULL.flac
Full/
└── Playlist_1_FULL.flac
played_tracks.json
```

The target duration is a minimum target: tracks are not cut, so the generated playlist can be slightly longer.

## Notes

FFmpeg codec availability can vary by build. The program reports a conversion/merge error if the selected encoder is unavailable. Generated media, conversion cache, and runtime history are ignored by Git.
