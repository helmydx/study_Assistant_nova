import os
import sqlite3
from google import genai
from google.genai import types

API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

# Simple test tool
def get_system_time() -> str:
    """Mengambil waktu sistem saat ini."""
    return "2026-05-28 12:00:00"

def test_combined():
    try:
        config = types.GenerateContentConfig(
            system_instruction="Kamu adalah Nova. Gunakan tools lokal jika ditanya tentang sistem, dan gunakan Google Search untuk info eksternal.",
            tools=[get_system_time, {"google_search": {}}],
            temperature=0.7
        )
        
        chat = client.chats.create(
            model="gemini-2.5-flash",
            config=config
        )
        
        # Test 1: Local Tool
        print("Sending Query 1 (Local Tool)...")
        r1 = chat.send_message("jam berapa sekarang?")
        print(f"Response 1: {r1.text}\n")
        
        # Test 2: Web Search
        print("Sending Query 2 (Google Search)...")
        r2 = chat.send_message("siapa perdana menteri Inggris sekarang?")
        print(f"Response 2: {r2.text}\n")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_combined()
