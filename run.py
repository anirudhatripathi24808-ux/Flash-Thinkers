import os
import sys
from pathlib import Path

# Ensure workspace root is in python path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app import create_app
from backend.sockets import socketio

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    print("=" * 60)
    print("   FLASHNOVA – Futuristic Next-Gen EdTech Platform")
    print("   'Every Student Matters. Every Confusion Counts.'")
    print(f"   Server listening at: http://localhost:{port}")
    print("=" * 60)
    socketio.run(app, host=host, port=port, debug=False)
