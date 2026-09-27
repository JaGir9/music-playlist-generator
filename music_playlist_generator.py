#!/usr/bin/env python3
"""Music Playlist Generator - audio/video scanner, converter and playlist builder."""

import json, os, random, shutil, subprocess
from datetime import datetime

APP_NAME = "Music Playlist Generator"
VERSION = "3.0.0"
SOURCE_DIR = "Music"
CONVERTED_DIR = "Converted"
OUTPUT_DIR = "Playlists"
FULL_OUTPUT_DIR = "Full"
LOG_FILE = "played_tracks.json"
DEFAULT_TARGET_MINUTES = 60

AUDIO_EXT = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma", ".aiff", ".aif", ".ac3"}
VIDEO_EXT = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".mpeg", ".mpg", ".m4v", ".ts", ".mts", ".m2ts", ".wmv", ".flv", ".3gp", ".vob", ".ogv"}
FORMATS = {
    1: {"ext": "mp3", "label": "MP3", "codec": "libmp3lame", "args": ["-b:a", "320k"]},
    2: {"ext": "flac", "label": "FLAC", "codec": "flac", "args": []},
    3: {"ext": "wav", "label": "WAV", "codec": "pcm_s16le", "args": []},
    4: {"ext": "aac", "label": "AAC", "codec": "aac", "args": ["-b:a", "256k"]},
    5: {"ext": "m4a", "label": "M4A/AAC", "codec": "aac", "args": ["-b:a", "256k"]},
    6: {"ext": "ogg", "label": "OGG/Vorbis", "codec": "libvorbis", "args": ["-q:a", "6"]},
    7: {"ext": "opus", "label": "OPUS", "codec": "libopus", "args": ["-b:a", "192k"]},
}

def header(title=None):
    print("\n" + "=" * 68); print(f" {APP_NAME} v{VERSION}")
    if title: print(f" {title}")
    print("=" * 68)

def ask_int(prompt, default=None, minimum=1, maximum=None):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        value = input(f"{prompt}{suffix}: ").strip()
        if not value and default is not None: return default
        try:
            n = int(value)
            if n >= minimum and (maximum is None or n <= maximum): return n
        except ValueError: pass
        rng = f"{minimum}-{maximum}" if maximum is not None else f">= {minimum}"
        print(f"Input tidak valid. Masukkan angka {rng}.")

def require_ffmpeg():
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        print("[ERROR] FFmpeg/ffprobe tidak ditemukan di PATH.")
        print("Install FFmpeg terlebih dahulu lalu pastikan perintah ffmpeg dan ffprobe dapat dijalankan.")
        return None, None
    return ffmpeg, ffprobe

def probe_media(path, ffprobe):
    cmd = [ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_type:format=duration", "-of", "json", os.path.abspath(path)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(p.stdout or "{}")
        if not data.get("streams"): return None
        duration = float(data.get("format", {}).get("duration") or 0)
        return duration if duration > 0 else None
    except (subprocess.CalledProcessError, ValueError, json.JSONDecodeError, OSError): return None

def scan_media(directory, ffprobe):
    items, audio_count, video_count, skipped = {}, 0, 0, 0
    print(f"\nMemindai media di '{directory}'...")
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in {CONVERTED_DIR, OUTPUT_DIR, FULL_OUTPUT_DIR, ".git"}]
        for filename in sorted(files, key=str.lower):
            path = os.path.join(root, filename); ext = os.path.splitext(filename)[1].lower()
            kind = "audio" if ext in AUDIO_EXT else "video" if ext in VIDEO_EXT else "unknown"
            duration = probe_media(path, ffprobe)
            if duration is None:
                if kind != "unknown": print(f"[SKIP] Tidak ada audio stream valid: {os.path.relpath(path, directory)}"); skipped += 1
                continue
            if kind == "unknown": kind = "media"
            if kind == "video": video_count += 1
            else: audio_count += 1
            key = os.path.relpath(path, directory)
            items[key] = {"source_path": path, "path": path, "filename": filename, "duration": duration, "kind": kind, "converted": False}
    return items, audio_count, video_count, skipped

def format_time(seconds):
    sec = int(round(seconds)); h, rem = divmod(sec, 3600); m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def choose_format(title):
    header(title)
    for i, cfg in FORMATS.items(): print(f"[{i}] {cfg['label']}")
    return FORMATS[ask_int("Pilih format", default=1, minimum=1, maximum=len(FORMATS))]

def convert_one(source, destination, fmt, ffmpeg):
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", os.path.abspath(source), "-map", "0:a:0", "-vn", "-ar", "44100", "-ac", "2", "-c:a", fmt["codec"], *fmt["args"], os.path.abspath(destination)]
    try: subprocess.run(cmd, check=True); return True
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"[ERROR] Konversi gagal '{source}': {exc}")
        if os.path.exists(destination): os.remove(destination)
        return False

def prepare_media(items, conversion_format, convert_existing_audio, ffmpeg, ffprobe):
    os.makedirs(CONVERTED_DIR, exist_ok=True); prepared = {}
    print(f"\nMenyiapkan media -> {conversion_format['label']}...")
    for key, info in items.items():
        must_convert = info["kind"] == "video" or convert_existing_audio
        if not must_convert: prepared[key] = info.copy(); continue
        rel_no_ext = os.path.splitext(key)[0]; dest = os.path.join(CONVERTED_DIR, rel_no_ext + "." + conversion_format["ext"])
        cached = os.path.exists(dest) and os.path.getmtime(dest) >= os.path.getmtime(info["source_path"])
        if not cached:
            print(f"[CONVERT] {key} -> {os.path.relpath(dest)}")
            if not convert_one(info["source_path"], dest, conversion_format, ffmpeg): continue
        duration = probe_media(dest, ffprobe)
        if not duration: continue
        new = info.copy(); new.update({"path": dest, "filename": os.path.basename(dest), "duration": duration, "converted": True}); prepared[key] = new
    return prepared

def load_history():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f: data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("playlists"), list):
                data.setdefault("current_cycle_used", []); return data
        except (OSError, json.JSONDecodeError) as exc: print(f"[WARNING] Riwayat gagal dibaca: {exc}")
    return {"playlists": [], "current_cycle_used": []}

def save_history(data):
    tmp = LOG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp, LOG_FILE)

def display_tracks(tracks):
    keys = list(tracks); print("\nDaftar lagu/media:")
    for i, key in enumerate(keys, 1):
        info = tracks[key]; flag = "CONVERTED" if info["converted"] else info["kind"].upper()
        print(f" [{i:>3}] {key} ({format_time(info['duration'])}) [{flag}]")
    return keys

def choose_fixed_tracks(tracks):
    header("PENGATURAN URUTAN LAGU"); print("[1] Default / Full Random\n[2] Custom Fixed Tracks - tentukan posisi awal, sisanya random")
    mode = ask_int("Pilih mode", default=1, minimum=1, maximum=2)
    if mode == 1: return [], "default_random"
    keys = display_tracks(tracks); count = min(ask_int("Berapa lagu awal yang ingin ditentukan", default=1), len(keys)); selected = []
    for pos in range(1, count + 1):
        while True:
            choice = ask_int(f"Pilih nomor lagu untuk posisi #{pos}", minimum=1, maximum=len(keys)); key = keys[choice - 1]
            if key in selected: print("Lagu sudah dipilih. Pilih yang lain."); continue
            selected.append(key); print(f" Posisi #{pos}: {key}"); break
    return selected, "custom_fixed"

def build_selection(tracks, fixed, target, cycle_used):
    selected = list(fixed); selected_set = set(selected); cycle = set(cycle_used); cycle.update(fixed)
    duration = sum(tracks[k]["duration"] for k in selected)
    while duration < target:
        pool = [k for k in tracks if k not in cycle and k not in selected_set]
        if not pool: pool = [k for k in tracks if k not in selected_set]; cycle = set(fixed)
        if not pool: break
        k = random.choice(pool); selected.append(k); selected_set.add(k); cycle.add(k); duration += tracks[k]["duration"]
    return selected, duration, cycle

def merge_tracks(paths, output, fmt, ffmpeg):
    if not paths: return False
    filters = [f"[{i}:a:0]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[a{i}]" for i in range(len(paths))]
    filters.append("".join(f"[a{i}]" for i in range(len(paths))) + f"concat=n={len(paths)}:v=0:a=1[outa]")
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
    for p in paths: cmd += ["-i", os.path.abspath(p)]
    cmd += ["-filter_complex", ";".join(filters), "-map", "[outa]", "-c:a", fmt["codec"], *fmt["args"], os.path.abspath(output)]
    print(f"Menggabungkan {len(paths)} lagu -> {os.path.basename(output)}")
    try: subprocess.run(cmd, check=True); return True
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"[ERROR] Merge gagal: {exc}")
        if os.path.exists(output): os.remove(output)
        return False

def next_playlist_index():
    if not os.path.isdir(OUTPUT_DIR): return 1
    nums = [int(n.split("_",1)[1]) for n in os.listdir(OUTPUT_DIR) if n.startswith("Playlist_") and n.split("_",1)[1].isdigit()]
    return max(nums, default=0) + 1

def create_playlist(tracks, fixed, target, full_fmt, index, history, cycle, mode, ffmpeg):
    name = f"Playlist_{index}"; folder = os.path.join(OUTPUT_DIR, name); os.makedirs(folder, exist_ok=True)
    past = {tuple(x.get("tracks", [])) for x in history}
    for attempt in range(100):
        selected, duration, candidate_cycle = build_selection(tracks, fixed, target, cycle)
        if tuple(selected) not in past or attempt == 99: break
    lines = [f"===> {name}", f"Mode: {mode}", f"Target: {format_time(target)}", "", "TRACKLIST:"]; elapsed, ordered = 0.0, []
    for i, key in enumerate(selected, 1):
        src = tracks[key]["path"]; base, ext = os.path.splitext(os.path.basename(src)); dst = os.path.join(folder, f"{i:02d}. {base}{ext}")
        shutil.copy2(src, dst); ordered.append(dst); lines.append(f"{format_time(elapsed)} - {base}" + (" [FIXED]" if i <= len(fixed) else "")); elapsed += tracks[key]["duration"]
    with open(os.path.join(folder, "TRACKLIST.txt"), "w", encoding="utf-8") as f: f.write("\n".join(lines) + "\n")
    merged_name = f"{name}_FULL.{full_fmt['ext']}"; merged = os.path.join(folder, merged_name); ok = merge_tracks(ordered, merged, full_fmt, ffmpeg); full_copy = None
    if ok:
        os.makedirs(FULL_OUTPUT_DIR, exist_ok=True); full_copy = os.path.join(FULL_OUTPUT_DIR, merged_name); shutil.copy2(merged, full_copy)
        print(f"[OK] FULL: {merged}\n[OK] Salinan: {full_copy}")
    return {"playlist_name": name, "mode": mode, "fixed_tracks": fixed, "tracks": selected, "total_tracks": len(selected), "target_duration": target, "total_duration": round(duration,2), "formatted_duration": format_time(duration), "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "full_format": full_fmt["ext"], "merged_file": merged_name if ok else None, "full_copy": full_copy}, candidate_cycle

def main():
    header(); print("Deteksi audio/video + konversi otomatis + playlist random/fixed + FULL mix.")
    ffmpeg, ffprobe = require_ffmpeg()
    if not ffmpeg: return
    os.makedirs(SOURCE_DIR, exist_ok=True); raw, ac, vc, skipped = scan_media(SOURCE_DIR, ffprobe)
    if not raw: print(f"Tidak ada media dengan audio stream di '{SOURCE_DIR}'."); return
    print(f"[OK] Audio/media: {ac} | Video: {vc} | Total: {len(raw)} | Skip: {skipped}")
    conversion_fmt = choose_format("FORMAT KONVERSI MEDIA")
    header("FILE AUDIO YANG SUDAH ADA"); print("[1] Pertahankan format audio asli (video tetap dikonversi)\n[2] Convert SEMUA audio + video ke format yang dipilih")
    convert_all = ask_int("Pilih", default=1, minimum=1, maximum=2) == 2
    prepared = prepare_media(raw, conversion_fmt, convert_all, ffmpeg, ffprobe)
    if not prepared: print("Tidak ada media yang berhasil disiapkan."); return
    fixed, mode = choose_fixed_tracks(prepared); header("PENGATURAN PLAYLIST")
    count = ask_int("Mau buat berapa playlist", default=1); minutes = ask_int("Target durasi per playlist (menit)", default=DEFAULT_TARGET_MINUTES); target = minutes * 60
    full_fmt = choose_format("FORMAT FILE FULL PLAYLIST")
    header("RINGKASAN"); print(f"Media siap       : {len(prepared)}\nFormat konversi  : {conversion_fmt['label']}\nAudio asli       : {'ikut dikonversi' if convert_all else 'dipertahankan'}\nMode playlist    : {mode}\nFixed tracks     : {len(fixed)}\nJumlah playlist  : {count}\nTarget durasi    : {minutes} menit\nFormat FULL      : {full_fmt['label']}\nConverted        : {CONVERTED_DIR}/\nPlaylist         : {OUTPUT_DIR}/\nSalinan FULL     : {FULL_OUTPUT_DIR}/")
    if input("\nMulai proses? [Y/n]: ").strip().lower() not in ("", "y", "yes", "ya"): print("Dibatalkan."); return
    os.makedirs(OUTPUT_DIR, exist_ok=True); os.makedirs(FULL_OUTPUT_DIR, exist_ok=True)
    data = load_history(); history = data.get("playlists", []); cycle = set(data.get("current_cycle_used", [])); idx = next_playlist_index()
    for _ in range(count):
        header(f"MEMBUAT Playlist_{idx}"); entry, cycle = create_playlist(prepared, fixed, target, full_fmt, idx, history, cycle, mode, ffmpeg)
        history.append(entry); data["playlists"] = history; data["current_cycle_used"] = sorted(cycle); save_history(data)
        print(f"[DONE] {entry['playlist_name']} | {entry['formatted_duration']} | {entry['total_tracks']} lagu"); idx += 1
    header("SELESAI"); print(f"Converted : {CONVERTED_DIR}/\nPlaylists : {OUTPUT_DIR}/\nFull      : {FULL_OUTPUT_DIR}/\nRiwayat   : {LOG_FILE}")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\n\nProses dibatalkan oleh pengguna.")
