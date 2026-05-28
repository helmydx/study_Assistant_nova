# main.py
import os
import re
import json
import time
import asyncio
import threading
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import database
import music_player
from stt import dengarkan
import gemini_bot
from gemini_bot import tanya_gemini
from tts import bicara, stop_bicara

def trigger_ws_start_pomodoro(dur_study: int, dur_break: int):
    try:
        try:
            l = asyncio.get_running_loop()
        except RuntimeError:
            l = asyncio.get_event_loop()
        if l.is_running():
            asyncio.run_coroutine_threadsafe(
                manager.broadcast({
                    "type": "start_pomodoro",
                    "study_time": dur_study,
                    "break_time": dur_break
                }),
                l
            )
    except RuntimeError:
        pass

def trigger_ws_start_timer(dur_minutes: int, label: str):
    try:
        try:
            l = asyncio.get_running_loop()
        except RuntimeError:
            l = asyncio.get_event_loop()
        if l.is_running():
            asyncio.run_coroutine_threadsafe(
                manager.broadcast({
                    "type": "start_timer",
                    "duration": dur_minutes,
                    "label": label
                }),
                l
            )
    except RuntimeError:
        pass

gemini_bot.register_callback("start_pomodoro", trigger_ws_start_pomodoro)
gemini_bot.register_callback("start_timer", trigger_ws_start_timer)

def trigger_ws_open_app(app_name: str):
    try:
        try:
            l = asyncio.get_running_loop()
        except RuntimeError:
            l = asyncio.get_event_loop()
        if l.is_running():
            asyncio.run_coroutine_threadsafe(
                manager.broadcast({
                    "type": "open_app",
                    "app": app_name
                }),
                l
            )
    except RuntimeError:
        pass

gemini_bot.register_callback("open_app", trigger_ws_open_app)

def get_system_stats_dict() -> dict:
    import glob
    stats = {"cpu": "N/A", "ram": "N/A", "battery": "N/A", "battery_charging": False}
    
    # 1. CPU Usage
    try:
        with open("/proc/loadavg", "r") as f:
            load = f.read().split()
            stats['cpu'] = load[0]
    except Exception:
        pass
        
    # 2. RAM Usage
    try:
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    meminfo[parts[0].strip()] = int(parts[1].replace("kB", "").strip())
                    
        total = meminfo.get("MemTotal", 0)
        free = meminfo.get("MemFree", 0)
        buffers = meminfo.get("Buffers", 0)
        cached = meminfo.get("Cached", 0)
        
        available = free + buffers + cached
        used = total - available
        used_percent = int((used / total) * 100) if total > 0 else 0
        stats['ram'] = f"{used_percent}%"
    except Exception:
        pass
        
    # 3. Battery
    try:
        bat_paths = glob.glob("/sys/class/power_supply/BAT*")
        if bat_paths:
            bat_path = bat_paths[0]
            with open(os.path.join(bat_path, "capacity"), "r") as f:
                cap = f.read().strip()
            with open(os.path.join(bat_path, "status"), "r") as f:
                status = f.read().strip()
            stats['battery'] = f"{cap}%"
            stats['battery_charging'] = "charge" in status.lower() or "full" in status.lower()
        else:
            stats['battery'] = "N/A"
    except Exception:
        pass
        
    return stats

# Ensure folders exist
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Connection Manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        await self.send_sidebar_data(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass

    async def send_sidebar_data(self, websocket: WebSocket):
        try:
            notes = database.get_notes()
            tasks = database.get_tasks()
            alarms = database.get_alarms()
            songs = music_player.get_songs()
            music_status = music_player.get_status()
            await websocket.send_text(json.dumps({
                "type": "sidebar_data",
                "notes": notes,
                "tasks": tasks,
                "alarms": alarms,
                "songs": songs,
                "music_status": music_status
            }))
        except Exception as e:
            print("Error sending sidebar data:", e)

    async def broadcast_sidebar_data(self):
        notes = database.get_notes()
        tasks = database.get_tasks()
        alarms = database.get_alarms()
        songs = music_player.get_songs()
        music_status = music_player.get_status()
        await self.broadcast({
            "type": "sidebar_data",
            "notes": notes,
            "tasks": tasks,
            "alarms": alarms,
            "songs": songs,
            "music_status": music_status
        })

INDO_NUMBERS = {
    "nol": 0, "satu": 1, "dua": 2, "tiga": 3, "empat": 4, "lima": 5,
    "enam": 6, "tujuh": 7, "delapan": 8, "sembilan": 9, "sepuluh": 10,
    "sebelas": 11, "dua belas": 12, "tiga belas": 13, "empat belas": 14,
    "lima belas": 15, "enam belas": 16, "tujuh belas": 17, "delapan belas": 18,
    "sembilan belas": 19, "dua puluh": 20, "tiga puluh": 30, "empat puluh": 40,
    "lima puluh": 50, "enam puluh": 60, "tujuh puluh": 70, "delapan puluh": 80,
    "sembilan puluh": 90, "seratus": 100
}

def parse_indo_number(text_str: str) -> float:
    text_str = text_str.strip().lower()
    if text_str.isdigit():
        return int(text_str)
    try:
        return float(text_str.replace(",", "."))
    except ValueError:
        pass
        
    words = text_str.split()
    total = 0
    temp = 0
    for w in words:
        if w == "belas":
            if temp == 0:
                temp = 10
            else:
                temp = 10 + temp
        elif w == "puluh":
            if temp == 0:
                temp = 10
            else:
                temp *= 10
        elif w == "ratus":
            if temp == 0:
                temp = 100
            else:
                temp *= 100
        elif w in INDO_NUMBERS:
            temp += INDO_NUMBERS[w]
    total += temp
    return total

def hitung_offline(text_lower: str) -> str:
    pattern = r"(?:hitung|kalkulasi|berapa)\s+(.+?)\s+(tambah|kurang|kali|bagi|\+|\-|\*|x|/)\s+(.+)"
    match = re.search(pattern, text_lower)
    if not match:
        return None
        
    val1_str, op_str, val2_str = match.groups()
    op_str = op_str.strip()
    
    try:
        num1 = parse_indo_number(val1_str)
        num2 = parse_indo_number(val2_str)
    except Exception:
        return "Maaf, format angka tidak dikenali."
    
    if op_str in ["tambah", "+"]:
        res = num1 + num2
        op_word = "tambah"
    elif op_str in ["kurang", "-"]:
        res = num1 - num2
        op_word = "kurang"
    elif op_str in ["kali", "*", "x"]:
        res = num1 * num2
        op_word = "kali"
    elif op_str in ["bagi", "/"]:
        if num2 == 0:
            return "Maaf, pembagian dengan nol tidak diperbolehkan."
        res = num1 / num2
        op_word = "bagi"
    else:
        return None
        
    if isinstance(res, float) and res.is_integer():
        res = int(res)
        
    if isinstance(res, float):
        res = round(res, 3)
        
    return f"Hasil dari {num1} {op_word} {num2} adalah {res}."

MOTIVATIONAL_QUOTES = [
    "Belajar adalah investasi terbaik untuk masa depanmu.",
    "Jangan takut salah, kesalahan adalah bukti bahwa kamu sedang mencoba.",
    "Fokuslah pada proses belajar, hasil akan mengikuti kerja kerasmu.",
    "Setiap hari adalah kesempatan baru untuk menjadi lebih pintar.",
    "Pendidikan adalah senjata paling ampuh yang bisa kamu gunakan untuk mengubah dunia.",
    "Kesuksesan hari esok dimulai dari apa yang kamu pelajari hari ini.",
    "Teruslah melangkah, walau pelan, karena belajar adalah maraton, bukan sprint.",
    "Bermimpilah yang tinggi, dan belajarlah dengan giat untuk mencapainya."
]

def generate_startup_greeting() -> str:
    import random
    current_hour = time.localtime().tm_hour
    if 5 <= current_hour < 12:
        sapaan = "Selamat pagi"
    elif 12 <= current_hour < 17:
        sapaan = "Selamat siang"
    elif 17 <= current_hour < 19:
        sapaan = "Selamat sore"
    else:
        sapaan = "Selamat malam"
        
    quote = random.choice(MOTIVATIONAL_QUOTES)
    return f"Halo, {sapaan}! Senang bertemu kembali denganmu. Ingat, {quote}"

def parse_local_command(text: str):
    """
    Mencoba mencocokkan input pengguna dengan pola perintah lokal (CRUD catatan, tugas, alarm).
    Mengmengembalikan (jawaban_teks, success) jika berhasil diproses secara lokal.
    Mengmengembalikan (None, False) jika tidak cocok dan membutuhkan Gemini AI.
    """
    text_lower = text.lower().strip()
    
    # List of known exact offline commands for fuzzy correction
    known_commands = [
        "catat", "tambah catatan", "daftar lagu", "daftar musik",
        "putar musik", "mainkan lagu", "jeda", "pause", "lanjut", "resume",
        "stop", "stop musik", "lagu selanjutnya", "musik berikutnya",
        "next", "lagu sebelumnya", "musik sebelumnya", "prev",
        "tambah volume", "kerasin volume", "kecilin volume", "kurangi volume",
        "mute", "matikan suara", "unmute", "suarakan",
        "mulai pomodoro", "pomodoro mulai", "belajar pomodoro", "fokus pomodoro",
        "cek status laptop", "cek performa", "status sistem", "cek ram cpu",
        "status perangkat", "performa perangkat",
        "buka catatan", "masuk catatan", "tampilkan catatan", "halaman catatan",
        "buka tugas", "masuk tugas", "tampilkan tugas", "halaman tugas",
        "buka alarm", "masuk alarm", "tampilkan alarm", "halaman alarm",
        "buka fokus", "buka pomodoro", "masuk fokus", "masuk pomodoro",
        "tampilkan fokus", "tampilkan pomodoro", "halaman fokus",
        "buka musik", "masuk musik", "tampilkan musik", "halaman musik",
        "tutup", "keluar", "kembali", "tutup aplikasi", "keluar aplikasi",
        "kembali ke layar utama", "tutup catatan", "tutup tugas", "tutup alarm",
        "tutup fokus", "tutup musik"
    ]
    
    # Try to find a very close match (minimum 80% similarity) to correct speech errors
    import difflib
    close_matches = difflib.get_close_matches(text_lower, known_commands, n=1, cutoff=0.8)
    if close_matches:
        if text_lower != close_matches[0]:
            print(f"🔮 Koreksi Otomatis Suara: '{text_lower}' -> '{close_matches[0]}'")
            text_lower = close_matches[0]
    
    # 1. Catatan (Notes)
    # Mulai mencatat tanpa konten langsung
    if text_lower in ["catat", "tambah catatan"]:
        return "START_NOTE_SESSION", True

    # Pattern: "catat <konten>" atau "tambah catatan <konten>"
    match_catat = re.match(r"^(?:catat|tambah catatan)\s+(.+)$", text_lower, re.IGNORECASE)
    if match_catat:
        content = match_catat.group(1).strip()
        start_idx = text.lower().find(content.lower())
        original_content = text[start_idx:].strip()
        res = database.add_note(original_content)
        return res, True
        
    # Pattern: "hapus catatan <id>"
    match_hapus_catat = re.match(r"^(?:hapus catatan|catatan hapus)\s+(\d+)$", text_lower, re.IGNORECASE)
    if match_hapus_catat:
        note_id = int(match_hapus_catat.group(1))
        res = database.delete_note(note_id)
        return res, True

    # 2. Tugas (Tasks)
    # Pattern: "tambah tugas <judul> [tenggat/jam/pukul] <tenggat>"
    # Pattern: "tugas <judul> [tenggat/jam/pukul] <tenggat>"
    if text_lower.startswith("tugas ") or text_lower.startswith("tambah tugas "):
        clean_text = text
        if text_lower.startswith("tambah tugas "):
            clean_text = text[13:].strip()
        elif text_lower.startswith("tugas "):
            clean_text = text[6:].strip()
            
        deadline = ""
        title = clean_text
        for keyword in [" tenggat ", " jam ", " pukul "]:
            if keyword in f" {clean_text.lower()} ":
                parts = re.split(rf"\s+{keyword.strip()}\s+", clean_text, flags=re.IGNORECASE)
                if len(parts) >= 2:
                    title = parts[0].strip()
                    deadline = parts[1].strip()
                    break
        
        if not (text_lower.startswith("tugas selesai") or text_lower.startswith("hapus tugas") or text_lower.startswith("tugas hapus")):
            res = database.add_task(title, deadline)
            return res, True

    # Pattern: "selesai tugas <id>" atau "tugas selesai <id>"
    match_selesai_tugas = re.match(r"^(?:selesai tugas|tugas selesai)\s+(\d+)$", text_lower, re.IGNORECASE)
    if match_selesai_tugas:
        task_id = int(match_selesai_tugas.group(1))
        res = database.complete_task(task_id)
        return res, True
        
    # Pattern: "hapus tugas <id>" atau "tugas hapus <id>"
    match_hapus_tugas = re.match(r"^(?:hapus tugas|tugas hapus)\s+(\d+)$", text_lower, re.IGNORECASE)
    if match_hapus_tugas:
        task_id = int(match_hapus_tugas.group(1))
        res = database.delete_task(task_id)
        return res, True

    # 3. Alarm
    # Pattern: "pasang alarm <HH:MM> label <label>" atau "pasang alarm <HH:MM> <label>"
    # Pattern: "alarm jam <HH:MM> <label>"
    # Pattern: "alarm <HH:MM> <label>"
    match_alarm = re.search(r"\b(\d{1,2})[.:](\d{2})\b", text_lower)
    if match_alarm and ("alarm" in text_lower or "pasang" in text_lower):
        hours = match_alarm.group(1).zfill(2)
        minutes = match_alarm.group(2)
        alarm_time = f"{hours}:{minutes}"
        
        label = text
        label = label.replace(match_alarm.group(0), "")
        for kw in ["pasang", "alarm", "jam", "pukul", "label"]:
            label = re.sub(rf"\b{kw}\b", "", label, flags=re.IGNORECASE)
        label = re.sub(r"\s+", " ", label).strip()
        
        if not ("hapus" in text_lower or "matikan" in text_lower or "aktifkan" in text_lower or "nonaktifkan" in text_lower):
            res = database.add_alarm(alarm_time, label)
            return res, True

    # Pattern: "hapus alarm <id>" atau "alarm hapus <id>"
    match_hapus_alarm = re.match(r"^(?:hapus alarm|alarm hapus)\s+(\d+)$", text_lower, re.IGNORECASE)
    if match_hapus_alarm:
        alarm_id = int(match_hapus_alarm.group(1))
        res = database.delete_alarm(alarm_id)
        return res, True

    # Pattern: "matikan alarm <id>" atau "alarm mati <id>"
    match_matikan_alarm = re.match(r"^(?:matikan alarm|alarm mati|nonaktifkan alarm)\s+(\d+)$", text_lower, re.IGNORECASE)
    if match_matikan_alarm:
        alarm_id = int(match_matikan_alarm.group(1))
        res = database.toggle_alarm(alarm_id, 0)
        return res, True

    # Pattern: "aktifkan alarm <id>" atau "alarm aktif <id>"
    match_aktifkan_alarm = re.match(r"^(?:aktifkan alarm|alarm aktif)\s+(\d+)$", text_lower, re.IGNORECASE)
    if match_aktifkan_alarm:
        alarm_id = int(match_aktifkan_alarm.group(1))
        res = database.toggle_alarm(alarm_id, 1)
        return res, True

    # 4. Musik (Music Player)
    # Jeda (Pause)
    if text_lower in ["jeda musik", "pause musik", "jeda lagu", "pause lagu", "jeda", "pause"]:
        res = music_player.pause_song()
        return res, True
        
    # Lanjut (Resume)
    if text_lower in ["lanjut musik", "resume musik", "lanjutkan musik", "lanjut lagu", "resume lagu", "lanjut", "resume"]:
        res = music_player.resume_song()
        return res, True
        
    # Stop/Matikan (Stop)
    if text_lower in ["stop musik", "matikan musik", "berhenti musik", "matikan lagu", "stop lagu", "stop"]:
        res = music_player.stop_song()
        return res, True

    # Daftar Lagu (List)
    if text_lower in ["daftar musik", "daftar lagu", "lihat musik", "lihat lagu", "list lagu", "list musik"]:
        res = music_player.list_songs()
        return res, True

    # Putar Lagu Acak/Pertama (Play)
    if text_lower in ["putar musik", "mainkan musik", "putar lagu", "mainkan lagu"]:
        res = music_player.play_random_or_first()
        return res, True

    # Putar Lagu Spesifik (Play Specific)
    match_putar = re.match(r"^(?:putar|mainkan)\s+(?:lagu|musik)\s+(.+)$", text_lower, re.IGNORECASE)
    if match_putar:
        song_query = match_putar.group(1).strip()
        start_idx = text.lower().find(song_query.lower())
        original_query = text[start_idx:].strip()
        res = music_player.play_song(original_query)
        return res, True

    # 5. Pengatur Volume
    if text_lower in ["kerasin volume", "tambah volume", "naikkan volume", "kencangkan volume", "naikan volume"]:
        res = music_player.change_system_volume(15)
        return res, True
    if text_lower in ["kecilin volume", "kurangi volume", "turunkan volume", "pelankan volume"]:
        res = music_player.change_system_volume(-15)
        return res, True
    if text_lower in ["mute volume", "senyap volume", "mute", "matikan suara", "diam"]:
        res = music_player.set_system_volume(0)
        return res, True
    if text_lower in ["unmute volume", "unmute", "suarakan"]:
        res = music_player.set_system_volume(50)
        return res, True
    
    match_vol = re.match(r"^(?:set volume|volume)\s+(\d+)$", text_lower, re.IGNORECASE)
    if match_vol:
        vol_level = int(match_vol.group(1))
        res = music_player.set_system_volume(vol_level)
        return res, True

    # 6. Pomodoro
    if text_lower in ["mulai pomodoro", "pomodoro mulai", "belajar pomodoro", "fokus pomodoro"]:
        gemini_bot.trigger_callback("start_pomodoro", 25, 5)
        return "Sesi Pomodoro belajar dimulai selama 25 menit.", True

    # 7. Status Perangkat
    if text_lower in ["cek status laptop", "cek performa", "status sistem", "cek ram cpu", "status perangkat", "performa perangkat"]:
        res = gemini_bot.ambil_status_sistem()
        return res, True

    # 8. Masuk Aplikasi (Open Pages)
    if text_lower in ["buka catatan", "masuk catatan", "tampilkan catatan", "halaman catatan"]:
        return "OPEN_APP_CATATAN", True
    if text_lower in ["buka tugas", "masuk tugas", "tampilkan tugas", "halaman tugas"]:
        return "OPEN_APP_TUGAS", True
    if text_lower in ["buka alarm", "masuk alarm", "tampilkan alarm", "halaman alarm"]:
        return "OPEN_APP_ALARM", True
    if text_lower in ["buka fokus", "buka pomodoro", "masuk fokus", "masuk pomodoro", "tampilkan fokus", "tampilkan pomodoro", "halaman fokus"]:
        return "OPEN_APP_POMODORO", True
    if text_lower in ["buka musik", "masuk musik", "tampilkan musik", "halaman musik"]:
        return "OPEN_APP_MUSIK", True

    # 9. Keluar Aplikasi (Close Pages)
    if text_lower in ["tutup", "keluar", "kembali", "tutup aplikasi", "keluar aplikasi", "kembali ke layar utama", "tutup catatan", "tutup tugas", "tutup alarm", "tutup fokus", "tutup musik"]:
        return "CLOSE_ALL_APPS", True

    # 10. Kalkulator Offline
    res_calc = hitung_offline(text_lower)
    if res_calc:
        return res_calc, True

    return None, False

manager = ConnectionManager()
is_processing = False
conversation_history = []
note_draft = ""
session_state = None

async def set_state(state: str):
    await manager.broadcast({"type": "state", "value": state})

async def process_user_input(text: str, mode: str = "hybrid"):
    global is_processing, conversation_history, note_draft, session_state
    if is_processing:
        return
    is_processing = True
    
    try:
        # Show what user said/typed
        await manager.broadcast({"type": "user_speech", "value": text})
        await set_state("thinking")
        
        # Tentukan pemrosesan berdasarkan mode / session_state
        jawaban = None
        success = False
        source = "local"
        
        text_lower = text.lower().strip()
        
        # JIKA sedang dalam mode mencatat catatan
        if session_state == "recording_note":
            # Cek pembatalan
            if text_lower in ["batal", "batalkan", "batal catatan", "batalkan catatan", "cancel"]:
                session_state = None
                note_draft = ""
                jawaban = "Pembuatan catatan dibatalkan."
                success = True
                source = "local"
            # Cek penyelesaian catatan
            elif "selesai catatan" in text_lower or "selesai mencatat" in text_lower or "simpan catatan" in text_lower:
                clean_text = text
                for kw in ["selesai catatan", "selesai mencatat", "simpan catatan"]:
                    pattern = re.compile(re.escape(kw), re.IGNORECASE)
                    clean_text = pattern.sub("", clean_text)
                clean_text = clean_text.strip()
                
                if clean_text:
                    note_draft = f"{note_draft} {clean_text}".strip()
                
                if not note_draft:
                    jawaban = "Catatan kosong, tidak ada yang disimpan."
                else:
                    database.add_note(note_draft)
                    jawaban = f"Catatan berhasil disimpan: '{note_draft}'"
                
                session_state = None
                note_draft = ""
                success = True
                source = "local"
            else:
                # Tambahkan ke draft catatan
                note_draft = f"{note_draft} {text}".strip()
                jawaban = f"Ditambahkan ke draf catatan: '{text}'. Silakan lanjutkan mencatat atau katakan 'selesai catatan' untuk menyimpan."
                success = True
                source = "local"
        else:
            if mode == "local":
                jawaban, success = parse_local_command(text)
                if not success:
                    jawaban = "Maaf, perintah tidak dikenali secara lokal. Silakan gunakan mode AI atau Hybrid."
                    success = True
                source = "local"
            elif mode == "ai":
                # Bypass local command completely
                success = False
            else:  # hybrid
                jawaban, success = parse_local_command(text)
                source = "local" if success else None

            if success:
                if jawaban == "OPEN_APP_CATATAN" or jawaban == "START_NOTE_SESSION":
                    session_state = "recording_note"
                    note_draft = ""
                    await manager.broadcast({"type": "open_app", "app": "catatan"})
                    jawaban = "Aplikasi Catatan dibuka. Silakan sebutkan catatan yang ingin disimpan. Katakan 'selesai catatan' jika sudah selesai."
                elif jawaban == "OPEN_APP_TUGAS":
                    await manager.broadcast({"type": "open_app", "app": "tugas"})
                    jawaban = "Aplikasi Tugas dibuka. Tugas baru apa yang ingin Anda tambahkan?"
                elif jawaban == "OPEN_APP_ALARM":
                    await manager.broadcast({"type": "open_app", "app": "alarm"})
                    jawaban = "Aplikasi Alarm dibuka. Jam berapa alarm ingin dipasang?"
                elif jawaban == "OPEN_APP_POMODORO":
                    await manager.broadcast({"type": "open_app", "app": "pomodoro"})
                    jawaban = "Aplikasi Fokus Pomodoro dibuka."
                elif jawaban == "OPEN_APP_MUSIK":
                    await manager.broadcast({"type": "open_app", "app": "musik"})
                    jawaban = "Pemutar Musik dibuka."
                elif jawaban == "CLOSE_ALL_APPS":
                    session_state = None
                    note_draft = ""
                    await manager.broadcast({"type": "close_app"})
                    jawaban = "Kembali ke layar utama."
                else:
                    print(f"⚡ Perintah diproses secara lokal (Tanpa AI): {text} -> {jawaban}")

        if not success:
            # Query Gemini in a thread
            loop = asyncio.get_running_loop()
            jawaban, updated_history = await loop.run_in_executor(
                None, lambda: tanya_gemini(text, conversation_history)
            )
            if jawaban == "ERROR_QUOTA":
                jawaban = "Maaf, batas kuota penggunaan harian AI Nova sudah habis. Silakan coba lagi nanti ya."
                source = "local"
            else:
                conversation_history = updated_history
                source = "gemini"
        
        # Show bot response
        await manager.broadcast({
            "type": "bot_response",
            "value": jawaban,
            "source": source,
            "session_state": session_state
        })
        
        # Refresh sidebar in case notes/tasks/alarms changed
        await manager.broadcast_sidebar_data()
        
        # TTS Callback functions to update WebSocket UI state
        loop = asyncio.get_running_loop()
        def on_start():
            try:
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(set_state("speaking"), loop)
            except RuntimeError:
                pass
            
        def on_end():
            try:
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(set_state("idle"), loop)
            except RuntimeError:
                pass
            
        # Play speech
        await loop.run_in_executor(
            None, lambda: bicara(jawaban, on_start=on_start, on_end=on_end)
        )
        
    except Exception as e:
        print("Error in process_user_input:", e)
        await manager.broadcast({"type": "bot_response", "value": f"Maaf, terjadi kesalahan: {str(e)}", "source": "local"})
        await set_state("idle")
    finally:
        is_processing = False

async def trigger_voice_input(mode: str = "hybrid"):
    global is_processing
    if is_processing:
        return
    is_processing = True
    
    try:
        await set_state("listening")
        
        loop = asyncio.get_running_loop()
        teks_suara = await loop.run_in_executor(
            None, lambda: dengarkan(durasi=5)
        )
        
        if not teks_suara:
            await manager.broadcast({"type": "user_speech", "value": "(Tidak ada suara terdeteksi)"})
            await set_state("idle")
            is_processing = False
            return
            
        is_processing = False
        await process_user_input(teks_suara, mode)
        
    except Exception as e:
        print("Error in trigger_voice_input:", e)
        await set_state("idle")
        is_processing = False

def parse_task_time(deadline_str):
    if not deadline_str:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%H:%M:%S", "%H:%M"):
        try:
            dt = datetime.strptime(deadline_str.strip(), fmt)
            if fmt in ("%H:%M:%S", "%H:%M"):
                dt = datetime.combine(datetime.now().date(), dt.time())
            return dt
        except ValueError:
            continue
    return None

# Alarm Checker Loop
async def alarm_checker_loop(websocket_manager: ConnectionManager):
    last_checked_minute = ""
    stats_counter = 0
    while True:
        try:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            
            # Send system stats every 10 seconds
            stats_counter += 1
            if stats_counter >= 10:
                stats_counter = 0
                stats = get_system_stats_dict()
                await websocket_manager.broadcast({
                    "type": "system_stats",
                    "value": stats
                })
            
            if current_time != last_checked_minute:
                last_checked_minute = current_time
                
                # Check exact Alarms
                alarms = database.get_alarms()
                for alarm in alarms:
                    if alarm["active"] == 1 and alarm["time"] == current_time:
                        label = alarm["label"] or "Alarm!"
                        print(f"⏰ ALARM BERBUNYI: {current_time} - {label}")
                        
                        # Broadcast alarm trigger to client
                        await websocket_manager.broadcast({
                            "type": "alarm_trigger",
                            "time": current_time,
                            "label": label
                        })
                        
                        # Speak alarm details in a background thread
                        def speak_alarm():
                            bicara(f"Perhatian! Alarm pukul {current_time} berbunyi. {label}")
                        threading.Thread(target=speak_alarm, daemon=True).start()
                
                # Check Alarms 1 Hour Before
                from datetime import timedelta
                one_hour_later = (now + timedelta(hours=1)).strftime("%H:%M")
                for alarm in alarms:
                    if alarm["active"] == 1 and alarm["time"] == one_hour_later:
                        label = alarm["label"] or "Alarm"
                        print(f"⏰ PEMBERITAHUAN ALARM (1 JAM SEBELUMNYA): {one_hour_later} - {label}")
                        def speak_alarm_warning(waktu_alarm=one_hour_later, label_alarm=label):
                            bicara(f"Pemberitahuan. Satu jam lagi alarm pukul {waktu_alarm} akan berbunyi, dengan catatan: {label_alarm}.")
                        threading.Thread(target=speak_alarm_warning, daemon=True).start()
                
                # Check Tasks 1 Hour Before
                tasks = database.get_tasks()
                target_time = (now + timedelta(hours=1)).replace(second=0, microsecond=0)
                for task in tasks:
                    if task["completed"] == 0 and task["deadline"]:
                        deadline_dt = parse_task_time(task["deadline"])
                        if deadline_dt:
                            deadline_minute = deadline_dt.replace(second=0, microsecond=0)
                            if deadline_minute == target_time:
                                title = task["title"]
                                deadline_str = task["deadline"]
                                print(f"📋 PEMBERITAHUAN TUGAS (1 JAM SEBELUMNYA): {title}")
                                def speak_task_warning(judul=title, deadline=deadline_str):
                                    bicara(f"Pemberitahuan. Satu jam lagi ada tugas yang harus dikerjakan, yaitu: {judul}. Batas waktu pengerjaan adalah pukul {deadline}.")
                                threading.Thread(target=speak_task_warning, daemon=True).start()
            
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print("Error in alarm loop:", e)
            await asyncio.sleep(5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background alarm task
    alarm_task = asyncio.create_task(alarm_checker_loop(manager))
    yield
    # Clean up background alarm task
    alarm_task.cancel()
    await alarm_task

# Initialize FastAPI App
app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_index():
    return FileResponse("templates/index.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Generate and play startup greeting
        greeting_text = generate_startup_greeting()
        loop = asyncio.get_running_loop()
        def speak_greeting():
            try:
                bicara(greeting_text)
            except Exception as e:
                print("Error speaking greeting:", e)
        loop.run_in_executor(None, speak_greeting)
        
        await websocket.send_text(json.dumps({
            "type": "bot_response",
            "value": greeting_text,
            "source": "local"
        }))

        # Send initial session state
        await websocket.send_text(json.dumps({
            "type": "session_state",
            "value": session_state
        }))
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "user_input":
                user_text = message["value"]
                mode = message.get("mode", "hybrid")
                asyncio.create_task(process_user_input(user_text, mode))
                
            elif message["type"] == "trigger_listen":
                mode = message.get("mode", "hybrid")
                asyncio.create_task(trigger_voice_input(mode))
                
            elif message["type"] == "stop_speak":
                stop_bicara()
                await set_state("idle")
                
            elif message["type"] == "music_control":
                action = message.get("action")
                if action == "play":
                    song = message.get("song")
                    if song:
                        music_player.play_song(song)
                    else:
                        music_player.play_random_or_first()
                elif action == "pause":
                    music_player.pause_song()
                elif action == "resume":
                    music_player.resume_song()
                elif action == "stop":
                    music_player.stop_song()
                elif action == "next":
                    music_player.play_next_song()
                elif action == "prev":
                    music_player.play_prev_song()
                elif action == "volume":
                    val = message.get("value", 70)
                    music_player.set_system_volume(val)
                await manager.broadcast_sidebar_data()
                
            elif message["type"] == "set_volume_system":
                val = message.get("value", 70)
                music_player.set_system_volume(val)
                await manager.broadcast_sidebar_data()

            elif message["type"] == "trigger_pomodoro_ws":
                action = message.get("action")
                if action == "start":
                    study_t = message.get("study_time", 25)
                    break_t = message.get("break_time", 5)
                    trigger_ws_start_pomodoro(study_t, break_t)
                elif action == "stop":
                    await manager.broadcast({"type": "stop_pomodoro"})
                    
            elif message["type"] == "speak_text":
                val = message.get("value", "")
                if val:
                    loop = asyncio.get_running_loop()
                    def run_speak():
                        bicara(val)
                    threading.Thread(target=run_speak, daemon=True).start()
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print("WebSocket error:", e)
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    print("Menjalankan server FastAPI di http://localhost:8005")
    uvicorn.run(app, host="0.0.0.0", port=8005)