#!/usr/bin/env python3
"""Music Playlist Generator - interactive randomized playlist builder."""

import json
import os
import random
import shutil
import subprocess
from datetime import datetime
from mutagen import File

APP_NAME = "Music Playlist Generator"
VERSION = "2.0.0"
SOURCE_DIR = "Music"
OUTPUT_DIR = "Playlists"
FULL_OUTPUT_DIR = "Full"
LOG_FILE = "played_tracks.json"
DEFAULT_TARGET_MINUTES = 60
DEFAULT_MP3_BITRATE = "320k"
SUPPORTED_EXT = (".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma")


def header(title=None):
    print("\n" + "=" * 64)
    print(f" {APP_NAME} v{VERSION}")
    if title:
        print(f" {title}")
    print("=" * 64)


def ask_int(prompt, default=None, minimum=1):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        value = input(f"{prompt}{suffix}: ").strip()
        if not value and default is not None:
            return default
        try:
            number = int(value)
            if number >= minimum:
                return number
        except ValueError:
            pass
        print(f"Input harus berupa angka minimal {minimum}.")


def get_audio_duration(file_path):
    try:
        audio = File(file_path)
        if audio is not None and audio.info is not None:
            return float(audio.info.length)
    except Exception as exc:
        print(f"[WARNING] Gagal membaca durasi '{file_path}': {exc}")
    return 0.0


def scan_music_files(directory):
    tracks = {}
    print(f"\nMemindai folder '{directory}'...")
    for root, _, files in os.walk(directory):
        for filename in sorted(files, key=str.lower):
            if not filename.lower().endswith(SUPPORTED_EXT):
                continue
            path = os.path.join(root, filename)
            duration = get_audio_duration(path)
            if duration <= 0:
                continue
            key = os.path.relpath(path, directory)
            tracks[key] = {"path": path, "filename": filename, "duration": duration}
    return tracks


def format_time(seconds):
    total_ms = round(seconds * 1000)
    whole_seconds, milliseconds = divmod(total_ms, 1000)
    if milliseconds > 500:
        whole_seconds += 1
    minutes, sec = divmod(whole_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{sec:02d}"


def load_history():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict) and isinstance(data.get("playlists"), list):
                data.setdefault("current_cycle_used", [])
                return data
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[WARNING] Riwayat tidak dapat dibaca: {exc}")
    return {"playlists": [], "current_cycle_used": []}


def save_history(data):
    temp_path = LOG_FILE + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4, ensure_ascii=False)
    os.replace(temp_path, LOG_FILE)


def display_tracks(tracks):
    keys = list(tracks.keys())
    print("\nDaftar lagu:")
    for index, key in enumerate(keys, 1):
        info = tracks[key]
        print(f"  [{index:>3}] {key}  ({format_time(info['duration'])})")
    return keys


def choose_fixed_tracks(tracks):
    header("PENGATURAN URUTAN LAGU")
    print("[1] Default / Full Random")
    print("    Semua posisi lagu diacak otomatis.")
    print("[2] Custom Fixed Tracks")
    print("    Tentukan lagu posisi 1, 2, 3, dst.; sisanya tetap random.")
    mode = ask_int("Pilih mode", default=1, minimum=1)
    while mode not in (1, 2):
        print("Pilihan hanya 1 atau 2.")
        mode = ask_int("Pilih mode", default=1, minimum=1)

    if mode == 1:
        return [], "default_random"

    keys = display_tracks(tracks)
    count = ask_int("Berapa lagu awal yang ingin ditentukan", default=1, minimum=1)
    count = min(count, len(keys))
    selected = []
    for position in range(1, count + 1):
        while True:
            choice = ask_int(f"Pilih nomor lagu untuk posisi #{position}", minimum=1)
            if choice > len(keys):
                print("Nomor lagu tidak tersedia.")
                continue
            key = keys[choice - 1]
            if key in selected:
                print("Lagu tersebut sudah dipilih. Pilih lagu lain.")
                continue
            selected.append(key)
            print(f"  Posisi #{position}: {key}")
            break
    return selected, "custom_fixed"


def merge_tracks_to_mp3(track_paths, output_path, bitrate):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("[ERROR] FFmpeg tidak ditemukan di PATH. File FULL tidak dibuat.")
        return False
    if not track_paths:
        return False

    filters = []
    for index in range(len(track_paths)):
        filters.append(
            f"[{index}:a:0]aresample=44100,aformat=sample_fmts=fltp:"
            f"channel_layouts=stereo,asetpts=PTS-STARTPTS[a{index}]"
        )
    labels = "".join(f"[a{i}]" for i in range(len(track_paths)))
    filters.append(f"{labels}concat=n={len(track_paths)}:v=0:a=1[outa]")

    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
    for path in track_paths:
        command.extend(["-i", os.path.abspath(path)])
    command.extend([
        "-filter_complex", ";".join(filters), "-map", "[outa]",
        "-c:a", "libmp3lame", "-b:a", bitrate,
        "-id3v2_version", "3", "-f", "mp3", os.path.abspath(output_path),
    ])

    print(f"Menggabungkan {len(track_paths)} lagu -> {os.path.basename(output_path)}")
    try:
        subprocess.run(command, check=True)
        print(f"[OK] File FULL berhasil: {output_path}")
        return True
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"[ERROR] Gagal menjalankan FFmpeg: {exc}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return False


def next_playlist_index():
    if not os.path.isdir(OUTPUT_DIR):
        return 1
    numbers = []
    for name in os.listdir(OUTPUT_DIR):
        if name.startswith("Playlist_"):
            suffix = name.split("_", 1)[1]
            if suffix.isdigit():
                numbers.append(int(suffix))
    return max(numbers, default=0) + 1


def build_track_selection(all_tracks, fixed_tracks, target_seconds, cycle_used):
    selected = list(fixed_tracks)
    selected_set = set(selected)
    temp_cycle_used = set(cycle_used)
    current_duration = sum(all_tracks[name]["duration"] for name in selected)
    temp_cycle_used.update(selected)

    while current_duration < target_seconds:
        unplayed_pool = [
            name for name in all_tracks
            if name not in temp_cycle_used and name not in selected_set
        ]
        if unplayed_pool:
            chosen = random.choice(unplayed_pool)
        else:
            fallback_pool = [name for name in all_tracks if name not in selected_set]
            if not fallback_pool:
                break
            temp_cycle_used = set(fixed_tracks)
            chosen = random.choice(fallback_pool)

        selected.append(chosen)
        selected_set.add(chosen)
        temp_cycle_used.add(chosen)
        current_duration += all_tracks[chosen]["duration"]

    return selected, current_duration, temp_cycle_used


def create_playlist(all_tracks, fixed_tracks, target_seconds, bitrate,
                    playlist_index, history, cycle_used, mode_name):
    playlist_name = f"Playlist_{playlist_index}"
    playlist_folder = os.path.join(OUTPUT_DIR, playlist_name)
    os.makedirs(playlist_folder, exist_ok=True)

    past_signatures = {tuple(item.get("tracks", [])) for item in history}
    attempt = 0
    while True:
        attempt += 1
        selected, duration, candidate_cycle = build_track_selection(
            all_tracks, fixed_tracks, target_seconds, cycle_used
        )
        if tuple(selected) not in past_signatures or attempt >= 100:
            break

    tracklist = [
        f"===> {playlist_name}", f"Mode: {mode_name}",
        f"Target: {format_time(target_seconds)}", "", "TRACKLIST:",
    ]
    elapsed = 0.0
    ordered_paths = []

    for index, track_key in enumerate(selected, 1):
        source = all_tracks[track_key]["path"]
        filename = all_tracks[track_key]["filename"]
        base, ext = os.path.splitext(filename)
        destination = os.path.join(playlist_folder, f"{index:02d}. {base}{ext}")
        shutil.copy2(source, destination)
        ordered_paths.append(destination)
        fixed_label = " [FIXED]" if index <= len(fixed_tracks) else ""
        tracklist.append(f"{format_time(elapsed)} - {base}{fixed_label}")
        elapsed += all_tracks[track_key]["duration"]

    with open(os.path.join(playlist_folder, "TRACKLIST.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(tracklist) + "\n")

    merged_filename = f"{playlist_name}_FULL.mp3"
    merged_path = os.path.join(playlist_folder, merged_filename)
    merged_ok = merge_tracks_to_mp3(ordered_paths, merged_path, bitrate)

    full_copy = None
    if merged_ok:
        os.makedirs(FULL_OUTPUT_DIR, exist_ok=True)
        full_copy = os.path.join(FULL_OUTPUT_DIR, merged_filename)
        shutil.copy2(merged_path, full_copy)
        print(f"[OK] Salinan FULL: {full_copy}")

    entry = {
        "playlist_name": playlist_name, "mode": mode_name,
        "fixed_tracks": fixed_tracks, "tracks": selected,
        "total_tracks": len(selected), "target_duration": target_seconds,
        "total_duration": round(duration, 2),
        "formatted_duration": format_time(duration),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "merged_mp3": merged_filename if merged_ok else None,
        "full_copy": full_copy,
    }
    return entry, candidate_cycle


def main():
    header()
    print("Random playlist generator dengan fixed opening tracks + FFmpeg FULL mix.")

    if not os.path.isdir(SOURCE_DIR):
        os.makedirs(SOURCE_DIR, exist_ok=True)
        print(f"\nFolder '{SOURCE_DIR}' belum berisi koleksi musik.")
        print(f"Masukkan file audio ke folder '{SOURCE_DIR}', lalu jalankan kembali.")
        return

    all_tracks = scan_music_files(SOURCE_DIR)
    if not all_tracks:
        print("Tidak ada file audio valid yang ditemukan.")
        return
    print(f"[OK] Total lagu terdeteksi: {len(all_tracks)}")

    fixed_tracks, mode_name = choose_fixed_tracks(all_tracks)

    header("PENGATURAN PLAYLIST")
    num_playlists = ask_int("Mau buat berapa playlist", default=1)
    target_minutes = ask_int("Target durasi per playlist (menit)", default=DEFAULT_TARGET_MINUTES)
    target_seconds = target_minutes * 60

    print("\nKualitas MP3 FULL:")
    print("[1] 320 kbps (Default / Recommended)")
    print("[2] 256 kbps")
    print("[3] 192 kbps")
    quality = ask_int("Pilih kualitas", default=1)
    bitrate = {1: "320k", 2: "256k", 3: "192k"}.get(quality, DEFAULT_MP3_BITRATE)

    header("RINGKASAN")
    print(f"Mode            : {mode_name}")
    print(f"Fixed tracks    : {len(fixed_tracks)}")
    for idx, name in enumerate(fixed_tracks, 1):
        print(f"  #{idx:<2}           : {name}")
    print(f"Jumlah playlist : {num_playlists}")
    print(f"Target durasi   : {target_minutes} menit")
    print(f"MP3 bitrate     : {bitrate}")
    print(f"Output playlist : {OUTPUT_DIR}/Playlist_x/")
    print(f"Salinan FULL    : {FULL_OUTPUT_DIR}/")

    confirm = input("\nMulai proses? [Y/n]: ").strip().lower()
    if confirm not in ("", "y", "yes", "ya"):
        print("Dibatalkan.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(FULL_OUTPUT_DIR, exist_ok=True)
    history_data = load_history()
    history = history_data.get("playlists", [])
    cycle_used = set(history_data.get("current_cycle_used", []))
    index = next_playlist_index()

    for _ in range(num_playlists):
        header(f"MEMBUAT Playlist_{index}")
        entry, cycle_used = create_playlist(
            all_tracks, fixed_tracks, target_seconds, bitrate,
            index, history, cycle_used, mode_name
        )
        history.append(entry)
        history_data["playlists"] = history
        history_data["current_cycle_used"] = sorted(cycle_used)
        save_history(history_data)
        print(f"[DONE] {entry['playlist_name']} | {entry['formatted_duration']} | {entry['total_tracks']} lagu")
        index += 1

    header("SELESAI")
    print(f"Playlist lengkap : {OUTPUT_DIR}/")
    print(f"Salinan MP3 FULL : {FULL_OUTPUT_DIR}/")
    print(f"Riwayat          : {LOG_FILE}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProses dibatalkan oleh pengguna.")
