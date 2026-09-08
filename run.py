import uvicorn
import os
import threading
import webview
from app.main import app

def run_server():
    os.makedirs("temp_storage", exist_ok=True)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

if __name__ == "__main__":
    # Start FastAPI server in a background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Create a native desktop window wrapping the local web app
    webview.create_window(
        "Data AI Engine",
        "http://127.0.0.1:8000",
        width=1280,
        height=800,
        min_size=(800, 600)
    )
    webview.start()