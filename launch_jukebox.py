"""
Standalone Infinite Jukebox Launcher
====================================
Like a dedicated generator that only powers the visualizer wing,
without energizing the rest of the building.
"""

from flask import Flask
from infinite_jukebox.server import register_with_app

app = Flask(__name__)
register_with_app(app)

if __name__ == "__main__":
    print("=" * 60)
    print("   INFINITE JUKEBOX — STANDALONE")
    print("=" * 60)
    print("   http://127.0.0.1:58082/jukebox")
    print("=" * 60)
    app.run(host="127.0.0.1", port=58082, threaded=True, debug=False)
