# desktop_app.py
import threading
import uvicorn
import webview
import time
import socket
from main import app

def start_server():
    # Run uvicorn on localhost:8005
    uvicorn.run(app, host="127.0.0.1", port=8005, log_level="warning")

def is_server_running():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(("127.0.0.1", 8005))
        s.close()
        return True
    except socket.error:
        return False

def main():
    # Start server thread if not already running
    if not is_server_running():
        print("Starting local backend server...")
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        for _ in range(20):
            if is_server_running():
                break
            time.sleep(0.5)

    # Open Pywebview window
    # Optimized for a 7-inch display (typical size 800x480 or 1024x600)
    print("Launching Nova Desktop Window...")
    webview.create_window(
        title="Nova Robot Assistant",
        url="http://127.0.0.1:8005",
        width=1024,
        height=600,
        resizable=True,
        min_size=(800, 480),
        background_color="#050814"
    )
    webview.start()

if __name__ == "__main__":
    main()
