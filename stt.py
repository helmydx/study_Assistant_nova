# stt.py
import sounddevice as sd
import numpy as np
import time
from faster_whisper import WhisperModel

print("🔄 Memuat model Whisper 'small' (500 MB unduhan pertama kali)...")
model = WhisperModel("small", device="cpu", compute_type="int8")

def dengarkan(durasi=5, fs=16000):
    """
    Rekam audio secara dinamis dengan kalibrasi noise latar belakang
    dan Voice Activity Detection (VAD). Jika gagal, fallback ke rekam statis.
    """
    # Prompt panduan transkripsi agar Whisper tidak salah eja perintah lokal
    prompt_panduan = "Nova, catat catatan, hapus catatan, tambah tugas, selesaikan tugas, atur alarm, hapus alarm, putar lagu, selesai catatan, batalkan catatan, buka catatan, masuk catatan, buka tugas, masuk tugas, buka alarm, masuk alarm, buka fokus, masuk fokus, buka musik, masuk musik, keluar, tutup, kembali"
    
    try:
        # 1. Kalibrasi kebisingan lingkungan selama 0.4 detik
        print("🎙️ Kalibrasi mikrofon...")
        calib_duration = 0.4
        calib_data = sd.rec(int(calib_duration * fs), samplerate=fs, channels=1, dtype=np.float32)
        sd.wait()
        noise_rms = np.sqrt(np.mean(calib_data**2))
        
        # Tentukan batas ambang suara (threshold)
        threshold = max(noise_rms + 0.015, 0.015)
        print(f"🔧 Noise RMS: {noise_rms:.5f} | Threshold: {threshold:.5f}")
        
        print("🎤 Bicara sekarang...")
        
        chunk_size = 1024
        audio_data = []
        is_speaking = False
        silence_start = None
        silence_duration = 1.3  # berhenti jika sunyi selama 1.3 detik
        timeout = durasi + 2    # batas maksimum mendengarkan
        start_time = time.time()
        
        # Callback untuk merekam suara secara real-time
        def callback(indata, frames, time_info, status):
            nonlocal is_speaking, silence_start, audio_data
            volume = np.sqrt(np.mean(indata**2))
            
            if not is_speaking:
                if volume > threshold:
                    is_speaking = True
                    print("🎙️ Suara terdeteksi...")
                    audio_data.extend(indata.flatten())
            else:
                audio_data.extend(indata.flatten())
                if volume < threshold:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start > silence_duration:
                        raise sd.CallbackStop()
                else:
                    silence_start = None

        with sd.InputStream(callback=callback, channels=1, samplerate=fs, blocksize=chunk_size):
            while True:
                sd.sleep(100)
                # Keluar jika timeout sebelum berbicara
                if not is_speaking and (time.time() - start_time > timeout):
                    print("⚠️ Timeout: Tidak ada suara terdeteksi.")
                    break
                # Keluar jika selesai berbicara (hening terdeteksi)
                if is_speaking and silence_start and (time.time() - silence_start > silence_duration):
                    print("🛑 Selesai merekam.")
                    break
                    
        if not audio_data:
            return ""
            
        audio_np = np.array(audio_data, dtype=np.float32)
        print("⏳ Mentranskripsi...")
        segments, _ = model.transcribe(
            audio_np, 
            language="id", 
            vad_filter=True, 
            initial_prompt=prompt_panduan
        )
        teks = " ".join([seg.text for seg in segments])
        return teks.strip()
        
    except Exception as e:
        print(f"⚠️ Gagal merekam dinamis ({e}). Menggunakan rekaman statis {durasi} detik...")
        # Fallback ke rekaman statis
        try:
            rekaman = sd.rec(int(durasi * fs), samplerate=fs, channels=1, dtype=np.float32)
            sd.wait()
            print("⏳ Mentranskripsi (fallback)...")
            segments, _ = model.transcribe(
                rekaman.flatten(), 
                language="id", 
                vad_filter=True, 
                initial_prompt=prompt_panduan
            )
            teks = " ".join([seg.text for seg in segments])
            return teks.strip()
        except Exception as ex:
            print(f"❌ Gagal merekam audio: {ex}")
            return ""

if __name__ == "__main__":
    hasil = dengarkan(durasi=5)
    print("Hasil:", hasil)