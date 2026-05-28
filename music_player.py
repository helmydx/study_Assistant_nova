# music_player.py
import os
import subprocess
import signal
import random

DEFAULT_MUSIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music")
os.makedirs(DEFAULT_MUSIC_DIR, exist_ok=True)

# Check standard system music directory
SYSTEM_MUSIC_DIR = os.path.expanduser("~/Music")

_current_process = None
_current_song = None
_is_paused = False

def get_music_dir() -> str:
    # If the system Music folder exists and has at least one audio file, use it
    if os.path.exists(SYSTEM_MUSIC_DIR):
        try:
            files = os.listdir(SYSTEM_MUSIC_DIR)
            if any(f.lower().endswith(('.mp3', '.wav', '.ogg')) for f in files):
                return SYSTEM_MUSIC_DIR
        except Exception:
            pass
    return DEFAULT_MUSIC_DIR

def get_songs() -> list:
    music_dir = get_music_dir()
    try:
        files = os.listdir(music_dir)
        songs = [f for f in files if f.lower().endswith(('.mp3', '.wav', '.ogg'))]
        return sorted(songs)
    except Exception:
        return []

def list_songs() -> str:
    songs = get_songs()
    music_dir = get_music_dir()
    if not songs:
        return f"Tidak ada file musik (.mp3, .wav, .ogg) di folder: {music_dir}"
    
    res = f"Folder musik ({music_dir}) berisi:\n"
    for i, s in enumerate(songs, 1):
        res += f"{i}. {s}\n"
    return res

def play_song(song_name: str) -> str:
    global _current_process, _current_song, _is_paused
    
    # Clean name
    song_name = song_name.strip()
    songs = get_songs()
    
    # If input is a number (index), parse it
    if song_name.isdigit():
        idx = int(song_name) - 1
        if 0 <= idx < len(songs):
            song_name = songs[idx]
        else:
            return f"Indeks musik {song_name} tidak valid. Ada {len(songs)} lagu."
    
    # Try fuzzy match if exact match not found
    if song_name not in songs:
        matched = [s for s in songs if song_name.lower() in s.lower()]
        if matched:
            song_name = matched[0]
        else:
            return f"Lagu '{song_name}' tidak ditemukan di folder musik."
            
    # Stop current play first
    stop_song()
    
    song_path = os.path.join(get_music_dir(), song_name)
    
    try:
        # Determine player command
        if song_name.lower().endswith('.mp3'):
            cmd = ['mpg123', '-q', song_path]
        elif song_name.lower().endswith('.wav'):
            cmd = ['paplay', song_path]
        else:
            # Fallback to play or mpg123
            cmd = ['mpg123', '-q', song_path]
            
        # Spawn in a new process group to allow killing whole group
        _current_process = subprocess.Popen(cmd, preexec_fn=os.setsid)
        _current_song = song_name
        _is_paused = False
        return f"Memutar lagu: '{song_name}'"
    except Exception as e:
        return f"Gagal memutar lagu: {str(e)}"

def play_random_or_first() -> str:
    songs = get_songs()
    if not songs:
        return f"Tidak ada file musik di folder {get_music_dir()}. Letakkan file .mp3 di sana."
    song = random.choice(songs)
    return play_song(song)

def stop_song() -> str:
    global _current_process, _current_song, _is_paused
    if _current_process:
        try:
            # Kill process group
            os.killpg(os.getpgid(_current_process.pid), signal.SIGKILL)
        except Exception:
            try:
                _current_process.terminate()
            except Exception:
                pass
        song_name = _current_song
        _current_process = None
        _current_song = None
        _is_paused = False
        return f"Musik dihentikan (sebelumnya memutar: '{song_name}')"
    return "Tidak ada musik yang sedang diputar."

def pause_song() -> str:
    global _current_process, _is_paused
    if _current_process and not _is_paused:
        try:
            os.killpg(os.getpgid(_current_process.pid), signal.SIGSTOP)
            _is_paused = True
            return "Musik dijeda."
        except Exception as e:
            return f"Gagal menjeda musik: {str(e)}"
    return "Tidak ada musik yang aktif untuk dijeda."

def resume_song() -> str:
    global _current_process, _is_paused
    if _current_process and _is_paused:
        try:
            os.killpg(os.getpgid(_current_process.pid), signal.SIGCONT)
            _is_paused = False
            return "Melanjutkan pemutaran musik."
        except Exception as e:
            return f"Gagal melanjutkan musik: {str(e)}"
    return "Tidak ada musik yang sedang dijeda."

def get_status() -> dict:
    return {
        "playing": _current_song is not None,
        "song": _current_song,
        "paused": _is_paused,
        "folder": get_music_dir()
    }

def play_next_song() -> str:
    global _current_song
    songs = get_songs()
    if not songs:
        return "Tidak ada lagu di folder musik."
    if not _current_song or _current_song not in songs:
        return play_random_or_first()
    try:
        idx = songs.index(_current_song)
        next_idx = (idx + 1) % len(songs)
        return play_song(songs[next_idx])
    except ValueError:
        return play_random_or_first()

def play_prev_song() -> str:
    global _current_song
    songs = get_songs()
    if not songs:
        return "Tidak ada lagu di folder musik."
    if not _current_song or _current_song not in songs:
        return play_random_or_first()
    try:
        idx = songs.index(_current_song)
        prev_idx = (idx - 1) % len(songs)
        return play_song(songs[prev_idx])
    except ValueError:
        return play_random_or_first()

_system_volume = 70

def set_system_volume(level: int) -> str:
    global _system_volume
    level = max(0, min(100, level))
    _system_volume = level
    try:
        success = False
        # Try amixer for Raspberry Pi / ALSA systems
        for control in ['Master', 'PCM', 'Headphone']:
            res = subprocess.run(["amixer", "-q", "sset", control, f"{level}%"], capture_output=True)
            if res.returncode == 0:
                success = True
                break
        
        if success:
            return f"Volume sistem berhasil diatur ke {level}%."
            
        # Try pactl for PulseAudio/PipeWire systems
        res = subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"], capture_output=True)
        if res.returncode == 0:
            return f"Volume sistem diatur ke {level}% via PulseAudio."
            
        return f"Volume sistem diatur ke {level}%."
    except Exception as e:
        return f"Gagal mengubah volume sistem: {str(e)}"

def change_system_volume(delta: int) -> str:
    global _system_volume
    new_vol = max(0, min(100, _system_volume + delta))
    return set_system_volume(new_vol)


