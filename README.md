# Music Playlist Generator

Professional CLI tool for generating randomized music playlists, optionally locking one or more opening tracks, creating timestamped tracklists, and rendering a full MP3 mix with FFmpeg.

## Features

- Full Random mode: all tracks are randomized.
- Custom Fixed Tracks mode: choose track #1, #2, #3, and as many opening positions as needed; the rest remain random.
- Configurable playlist count and target duration.
- Supports MP3, WAV, FLAC, M4A, AAC, OGG, OPUS, and WMA inputs.
- Avoids reusing tracks until the current collection cycle is exhausted where possible.
- Avoids repeating an identical playlist sequence using persistent history.
- Generates `TRACKLIST.txt` with timestamps and `[FIXED]` labels.
- Creates `Playlist_x_FULL.mp3` with FFmpeg.
- Keeps the FULL MP3 inside each playlist folder and also copies it to the top-level `Full/` folder.
- Saves playlist history to `played_tracks.json`.
- Handles same-named files stored in different subfolders by tracking relative paths internally.

## Requirements

- Python 3.9+
- FFmpeg available in your system PATH
- Python package: mutagen

Install:

```bash
pip install -r requirements.txt
```

Verify FFmpeg:

```bash
ffmpeg -version
```

## Usage

1. Put audio files inside the `Music/` folder. Subfolders are supported.
2. Run `python music_playlist_generator.py`.
3. Choose:
   - `1` Default / Full Random
   - `2` Custom Fixed Tracks
4. Custom mode lets you lock track #1, #2, #3, and as many opening positions as needed.
5. Set playlist count, target duration, and MP3 bitrate.
6. Confirm the summary to generate the playlists.

Example:

```text
[1] Default / Full Random
[2] Custom Fixed Tracks
Pilih mode [1]: 2

Berapa lagu awal yang ingin ditentukan [1]: 3
Pilih nomor lagu untuk posisi #1: 8
Pilih nomor lagu untuk posisi #2: 2
Pilih nomor lagu untuk posisi #3: 11
```

The selected opening tracks stay in that exact order; remaining positions are randomized.

## Output

Each playlist keeps its own FULL mix:

```text
Playlists/Playlist_1/Playlist_1_FULL.mp3
```

A second copy is also stored centrally:

```text
Full/Playlist_1_FULL.mp3
```

The target duration is a minimum target. Tracks are not cut, so the final duration can be slightly longer.

Generated media and `played_tracks.json` are ignored by Git to avoid accidentally committing large files.
