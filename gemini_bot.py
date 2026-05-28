# gemini_bot.py
import os
import database
import music_player
from google import genai
from google.genai import types

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY tidak ditemukan. Pastikan sudah diset di ~/.bashrc")

client = genai.Client(api_key=API_KEY)

SYSTEM_PROMPT = """
Kamu adalah "Nova", asisten belajar dan desktop yang ramah untuk siswa.
Jawab pertanyaan dalam bahasa Indonesia dengan singkat, jelas, dan akurat.
Kamu memiliki akses ke database lokal untuk menyimpan catatan (notes), tugas sekolah (tasks), dan alarm.
Kamu juga memiliki akses ke pemutar musik lokal (music_player) untuk memutar musik (.mp3/.wav) di folder musik.
Gunakan tools yang disediakan saat siswa memintamu untuk mengelola catatan/tugas/alarm atau memutar/menghentikan musik.
PENTING: Jangan membuat asumsi. Jika pengguna tidak menyebutkan parameter wajib (seperti waktu alarm), tanyakan kembali dengan ramah.
"""

# --- Tools / Functions for Gemini Calling ---

def tambah_catatan(isi: str) -> str:
    """Menambahkan catatan baru untuk siswa. Contoh: 'catat belanja buku besok'"""
    trigger_callback("open_app", "catatan")
    return database.add_note(content=isi)

def ambil_catatan() -> str:
    """Mengambil semua daftar catatan yang disimpan siswa."""
    trigger_callback("open_app", "catatan")
    notes = database.get_notes()
    if not notes:
        return "Tidak ada catatan yang disimpan."
    res = "Daftar Catatan Anda:\n"
    for n in notes:
        res += f"- [ID: {n['id']}] {n['content']} (dibuat: {n['created_at']})\n"
    return res

def hapus_catatan(id_catatan: int) -> str:
    """Menghapus catatan berdasarkan ID catatan."""
    trigger_callback("open_app", "catatan")
    return database.delete_note(note_id=id_catatan)

def tambah_tugas(judul: str, deadline: str = "") -> str:
    """Menambahkan tugas sekolah baru. Deadline opsional (format bebas, misal: 'besok', 'senin')."""
    trigger_callback("open_app", "tugas")
    return database.add_task(title=judul, deadline=deadline)

def ambil_tugas() -> str:
    """Mengambil semua daftar tugas sekolah."""
    trigger_callback("open_app", "tugas")
    tasks = database.get_tasks()
    if not tasks:
        return "Tidak ada tugas dalam daftar."
    res = "Daftar Tugas Anda:\n"
    for t in tasks:
        status = "Selesai" if t['completed'] == 1 else "Belum Selesai"
        deadline_str = f" (Deadline: {t['deadline']})" if t['deadline'] else ""
        res += f"- [ID: {t['id']}] {t['title']} - {status}{deadline_str}\n"
    return res

def selesaikan_tugas(id_tugas: int) -> str:
    """Menandai tugas sekolah sebagai selesai berdasarkan ID tugas."""
    trigger_callback("open_app", "tugas")
    return database.complete_task(task_id=id_tugas)

def hapus_tugas(id_tugas: int) -> str:
    """Menghapus tugas sekolah dari daftar berdasarkan ID tugas."""
    trigger_callback("open_app", "tugas")
    return database.delete_task(task_id=id_tugas)

def tambah_alarm(waktu: str, label: str = "") -> str:
    """Menambahkan alarm baru. Waktu HARUS dalam format 24 jam HH:MM (contoh: '07:00', '18:30'). Label alarm opsional."""
    trigger_callback("open_app", "alarm")
    return database.add_alarm(time=waktu, label=label)

def ambil_alarm() -> str:
    """Mengambil semua daftar alarm."""
    trigger_callback("open_app", "alarm")
    alarms = database.get_alarms()
    if not alarms:
        return "Tidak ada alarm yang aktif."
    res = "Daftar Alarm Anda:\n"
    for a in alarms:
        status = "Aktif" if a['active'] == 1 else "Nonaktif"
        label_str = f" ({a['label']})" if a['label'] else ""
        res += f"- [ID: {a['id']}] Pukul {a['time']}{label_str} - {status}\n"
    return res

def hapus_alarm(id_alarm: int) -> str:
    """Menghapus alarm berdasarkan ID alarm."""
    trigger_callback("open_app", "alarm")
    return database.delete_alarm(alarm_id=id_alarm)

# --- Music Player Tools ---

def putar_musik(nama_lagu_atau_indeks: str = "") -> str:
    """Memutar musik lokal dari folder musik. Parameter 'nama_lagu_atau_indeks' opsional (jika kosong, akan memutar lagu acak atau lagu pertama)."""
    trigger_callback("open_app", "musik")
    if not nama_lagu_atau_indeks:
        return music_player.play_random_or_first()
    return music_player.play_song(nama_lagu_atau_indeks)

def stop_musik() -> str:
    """Menghentikan pemutaran musik yang sedang berlangsung."""
    trigger_callback("open_app", "musik")
    return music_player.stop_song()

def jeda_musik() -> str:
    """Menjeda (pause) pemutaran musik yang sedang berlangsung."""
    trigger_callback("open_app", "musik")
    return music_player.pause_song()

def lanjutkan_musik() -> str:
    """Melanjutkan (resume) pemutaran musik yang sedang dijeda."""
    trigger_callback("open_app", "musik")
    return music_player.resume_song()

def daftar_musik() -> str:
    """Mendapatkan daftar semua file lagu (.mp3, .wav, .ogg) yang tersedia di folder musik."""
    trigger_callback("open_app", "musik")
    return music_player.list_songs()

# --- Callback Registry for Async Events ---
_callbacks = {}

def register_callback(name: str, func):
    _callbacks[name] = func

def trigger_callback(name: str, *args, **kwargs):
    if name in _callbacks:
        try:
            _callbacks[name](*args, **kwargs)
        except Exception as e:
            print(f"Error executing callback {name}: {e}")

# --- Device & System Tools ---

def ambil_status_sistem() -> str:
    """Mengambil informasi statistik performa perangkat saat ini (CPU Load, RAM, Baterai)."""
    import glob
    stats = {}
    
    # 1. CPU Usage
    try:
        with open("/proc/loadavg", "r") as f:
            load = f.read().split()
            stats['cpu'] = load[0]
    except Exception:
        stats['cpu'] = "N/A"
        
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
        
        used_gb = used / (1024 * 1024)
        total_gb = total / (1024 * 1024)
        used_percent = (used / total) * 100 if total > 0 else 0
        stats['ram'] = f"{used_percent:.1f}% ({used_gb:.1f} GB dari {total_gb:.1f} GB)"
    except Exception:
        stats['ram'] = "N/A"
        
    # 3. Battery
    try:
        bat_paths = glob.glob("/sys/class/power_supply/BAT*")
        if bat_paths:
            bat_path = bat_paths[0]
            with open(os.path.join(bat_path, "capacity"), "r") as f:
                cap = f.read().strip()
            with open(os.path.join(bat_path, "status"), "r") as f:
                status = f.read().strip()
            stats['battery'] = f"{cap}% ({status})"
        else:
            stats['battery'] = "Tidak ada baterai (Desktop PC/Raspberry Pi)"
    except Exception:
        stats['battery'] = "N/A"
        
    return f"Status Perangkat Anda:\n- CPU Load (1m): {stats['cpu']}\n- Penggunaan RAM: {stats['ram']}\n- Baterai: {stats['battery']}"

def atur_volume_sistem(level: int) -> str:
    """Mengatur volume suara perangkat ke tingkat tertentu (nilai integer antara 0 dan 100)."""
    return music_player.set_system_volume(level)

def atur_pomodoro(durasi_belajar: int = 25, durasi_istirahat: int = 5) -> str:
    """Memulai sesi timer belajar Pomodoro. Parameter opsional: durasi_belajar (menit) dan durasi_istirahat (menit)."""
    trigger_callback("start_pomodoro", durasi_belajar, durasi_istirahat)
    return f"Sesi Pomodoro belajar dimulai selama {durasi_belajar} menit, diikuti istirahat {durasi_istirahat} menit."

def atur_timer(durasi_menit: int, label: str = "Timer") -> str:
    """Mengatur hitung mundur (timer) dalam satuan menit dengan label tertentu untuk pengingat belajar."""
    trigger_callback("start_timer", durasi_menit, label)
    return f"Timer '{label}' selama {durasi_menit} menit telah dipasang."

# List of tools to register with Gemini
TOOLS_LIST = [
    tambah_catatan, ambil_catatan, hapus_catatan,
    tambah_tugas, ambil_tugas, selesaikan_tugas, hapus_tugas,
    tambah_alarm, ambil_alarm, hapus_alarm,
    putar_musik, stop_musik, jeda_musik, lanjutkan_musik, daftar_musik,
    ambil_status_sistem, atur_volume_sistem, atur_pomodoro, atur_timer
]

def tanya_gemini(pertanyaan: str, riwayat: list = None) -> tuple[str, list]:
    """
    Kirim pertanyaan ke Gemini dengan menyertakan riwayat percakapan bersih.
    Kembalikan (jawaban_final, riwayat_terbaru).
    Gunakan fallback model jika terjadi kegagalan/limit.
    """
    if riwayat is None:
        riwayat = []
        
    # Trim riwayat ke maks 10 pesan (5 turn) untuk hemat token
    if len(riwayat) > 10:
        riwayat = riwayat[-10:]
        
    # Konversi riwayat teks menjadi format Content SDK
    sdk_history = []
    for msg in riwayat:
        sdk_history.append(
            types.Content(
                role=msg["role"],
                parts=[types.Part.from_text(text=msg["text"])]
            )
        )
        
    model_list = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-2.5-flash-lite"]
    quota_exceeded = False
    
    # Check if the query asks for search/grounding or tools
    search_keywords = ["cari", "berita", "cuaca", "siapa", "harga", "saham", "presiden", "sekarang", "hari ini", "google", "tanya", "apa itu", "mengapa", "kenapa"]
    is_search = any(kw in pertanyaan.lower() for kw in search_keywords)
    
    # Google Search and Function Calling cannot be combined in the same request. Choose one.
    active_tools = [{"google_search": {}}] if is_search else TOOLS_LIST
    
    for model_name in model_list:
        try:
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=active_tools,
                temperature=0.7
            )
            chat = client.chats.create(
                model=model_name,
                history=sdk_history,
                config=config
            )
            response = chat.send_message(pertanyaan)
            
            if response.text:
                jawaban_teks = response.text.strip()
                riwayat.append({"role": "user", "text": pertanyaan})
                riwayat.append({"role": "model", "text": jawaban_teks})
                return jawaban_teks, riwayat
            else:
                raise RuntimeError("Response text is empty (function calling did not return final text)")
            
        except Exception as e:
            err_msg = str(e)
            print(f"⚠️ Model {model_name} gagal: {err_msg}")
            if "429" in err_msg or "quota" in err_msg.lower():
                quota_exceeded = True
            continue
            
    if quota_exceeded:
        return "ERROR_QUOTA", riwayat
        
    return "Maaf, semua model gagal memproses permintaan. Coba lagi nanti.", riwayat

if __name__ == "__main__":
    print("Menguji asisten Gemini dengan fungsi database...")
    jawaban, riwayat = tanya_gemini("tolong catat belajar pemrograman besok pagi")
    print("Jawaban:", jawaban)
    print("Riwayat:", riwayat)
    print("\nAmbil catatan...")
    jawaban, riwayat = tanya_gemini("tampilkan catatan saya", riwayat)
    print("Jawaban:", jawaban)