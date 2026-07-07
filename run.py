"""Launch backend server + pywebview desktop window."""
import sys, threading, time
from pathlib import Path
import uvicorn
import webview

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def serve():
    uvicorn.run(
        "backend.main:app", host="127.0.0.1", port=8765,
        log_level="warning", reload=False,
    )


def main():
    t = threading.Thread(target=serve, daemon=True)
    t.start()
    time.sleep(1.5)
    window = webview.create_window(
        "Indicator Dashboard",
        "http://127.0.0.1:8765/",
        width=1500, height=900, resizable=True,
    )
    webview.start(debug=True)


if __name__ == "__main__":
    main()
