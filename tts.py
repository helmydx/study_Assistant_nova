# tts.py
import edge_tts
import asyncio
import os

SUARA = "id-ID-GadisNeural"  # suara perempuan Indonesia

async def _ucapkan(teks: str, file_output: str = "output.mp3"):
    communicate = edge_tts.Communicate(teks, SUARA)
    await communicate.save(file_output)
    # Putar dengan mpg123 (Linux)
    os.system(f'mpg123 -q {file_output}')

def bicara(teks: str, on_start=None, on_end=None):
    if on_start:
        try:
            on_start()
        except Exception as e:
            print("Error in on_start callback:", e)
            
    asyncio.run(_ucapkan(teks))
    
    if on_end:
        try:
            on_end()
        except Exception as e:
            print("Error in on_end callback:", e)

def stop_bicara():
    """Menghentikan pemutaran suara yang sedang berjalan dengan mematikan proses mpg123."""
    try:
        import subprocess
        subprocess.run(["pkill", "-9", "mpg123"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print("Error stopping speech:", e)

if __name__ == "__main__":
    bicara("Halo, saya Nova, asisten belajarmu.")