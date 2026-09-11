import asyncio
import logging
import os
import sys
import threading
import uvicorn
import webview
from app.main import app


def _suppress_connection_reset(loop, context):
    exception = context.get("exception")
    if isinstance(exception, ConnectionResetError):
        return
    loop.default_exception_handler(context)


logging.getLogger("asyncio").setLevel(logging.CRITICAL)


def run_server():
    os.makedirs("temp_storage", exist_ok=True)

    # Apply the exception filter when the loop starts
    if sys.platform == "win32":
        try:
            loop = asyncio.get_event_loop()
            loop.set_exception_handler(_suppress_connection_reset)
        except RuntimeError:
            pass

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    webview.create_window(
        "Data AI Engine",
        "http://127.0.0.1:8000",
        width=1280,
        height=800,
        min_size=(800, 600),
    )
    webview.start()