#!/usr/bin/env python3
"""
Voice-to-Text Tool (Web GUI)
============================
Runs a local web server. Open your browser to the displayed URL
(or it opens automatically) to see a clean GUI for recording
and transcribing speech.

Requirements: Python 3.8+, microphone access, internet connection
"""

import os
import sys
import time
import threading
import queue
import webbrowser
import json
import struct
import math

# Fix Windows console encoding for Unicode
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    sys.stdout.reconfigure(encoding="utf-8")


def hide_console():
    if sys.platform == "win32":
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)


def show_console():
    if sys.platform == "win32":
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 1)

# ---------------------------------------------------------------------------
# Dependency check with helpful error messages
# ---------------------------------------------------------------------------
MISSING = []

try:
    import speech_recognition as sr
except ImportError:
    MISSING.append("SpeechRecognition")

try:
    import pyaudio
except ImportError:
    MISSING.append("PyAudio")

try:
    import pyperclip
except ImportError:
    MISSING.append("pyperclip")

try:
    import pyautogui
except ImportError:
    MISSING.append("pyautogui")

try:
    import flask
except ImportError:
    MISSING.append("Flask")

try:
    import pyttsx3
except ImportError:
    MISSING.append("pyttsx3")

if MISSING:
    print("=" * 60)
    print("MISSING DEPENDENCIES")
    print("=" * 60)
    print("The following Python packages are required but not installed:")
    for pkg in MISSING:
        print(f"  - {pkg}")
    print()
    print("Install them by running:")
    print("    setup.bat")
    print()
    print("Or manually with pip:")
    print("    pip install SpeechRecognition PyAudio pyperclip pyautogui Flask pyttsx3")
    print("=" * 60)
    sys.exit(1)

from flask import Flask, render_template, jsonify, request, Response

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TIMEOUT_SECONDS = 30       # Max seconds to wait for speech to START
PHRASE_TIME_LIMIT = 30     # Max seconds for a single utterance
ENERGY_THRESHOLD = 300
PAUSE_THRESHOLD = 1.5      # Seconds of silence before auto-stop
PHRASE_THRESHOLD = 0.3
DYNAMIC_ENERGY_ADJUSTMENT = True
ENERGY_THRESHOLD_MIN = 50
ENERGY_THRESHOLD_MAX = 2000
AUTO_COPY = True               # Automatically copy transcribed text to clipboard
AUTO_TYPE = True
BEEP_ON_START = True
BEEP_ON_STOP = True
HOST = "127.0.0.1"
PORT = 58080


def sanitize_for_typewrite(text):
    """Replace Unicode chars that pyautogui can't type with ASCII equivalents."""
    replacements = {
        '\u2018': "'",   # left single quotation mark
        '\u2019': "'",   # right single quotation mark
        '\u201c': '"',   # left double quotation mark
        '\u201d': '"',   # right double quotation mark
        '\u2013': '-',   # en dash
        '\u2014': '-',   # em dash
        '\u2026': '...', # ellipsis
        '\u00a0': ' ',   # non-breaking space
        '\u2018': "'",   # smart single open
        '\u2019': "'",   # smart single close
        '\u201c': '"',   # smart double open
        '\u201d': '"',   # smart double close
    }
    for uni, ascii_ch in replacements.items():
        text = text.replace(uni, ascii_ch)
    return text


def paste_text(text):
    """Type text into the active window using pyautogui.
    Switches to previous window with Alt+Tab if OrbitScribe is foreground.
    Uses slower interval (0.04) to prevent dropped/reordered keys."""
    try:
        if sys.platform == "win32":
            try:
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                buf = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
                if "OrbitScribe" in buf.value:
                    try:
                        import keyboard
                        keyboard.send('alt+tab')
                    except Exception:
                        pyautogui.keyDown('alt')
                        pyautogui.keyDown('tab')
                        pyautogui.keyUp('tab')
                        pyautogui.keyUp('alt')
                    time.sleep(0.3)
            except Exception:
                pass

        pyautogui.FAILSAFE = False
        clean = sanitize_for_typewrite(text)
        if clean and not clean.endswith((" ", "\n")):
            clean += " "
        pyautogui.typewrite(clean, interval=0.04)
        return True
    except Exception as e:
        print(f"[WARN] Type error: {e}")
        return False


# ---------------------------------------------------------------------------
# TTS Engine
# ---------------------------------------------------------------------------
tts_engine = None
tts_voices = []

def init_tts():
    global tts_engine, tts_voices
    try:
        tts_engine = pyttsx3.init()
        tts_voices = []
        for v in tts_engine.getProperty("voices"):
            tts_voices.append({"id": v.id, "name": v.name})
        # Pick a Microsoft voice if available
        for v in tts_voices:
            if "microsoft" in v["name"].lower():
                tts_engine.setProperty("voice", v["id"])
                break
        print(f"[TTS] Loaded {len(tts_voices)} voice(s)")
    except Exception as e:
        print(f"[WARN] TTS init failed: {e}")


def speak_text(text: str, voice_id: str = None):
    def _speak():
        try:
            engine = pyttsx3.init()
            if voice_id:
                engine.setProperty("voice", voice_id)
            elif tts_engine:
                engine.setProperty("voice", tts_engine.getProperty("voice"))
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"[ERROR] TTS failed: {e}")
    threading.Thread(target=_speak, daemon=True).start()

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
app = Flask(__name__)

recognizer = sr.Recognizer()
microphone = sr.Microphone()

recording_event = threading.Event()
audio_queue = queue.Queue()
shutdown_event = threading.Event()

status_lock = threading.Lock()
current_status = "idle"  # idle | listening | processing
latest_result = None
result_history = []

status_callbacks = []

# Callbacks for float/docked window control (set by the frontend app)
mode_callback = None
close_callback = None
minimize_callback = None

# ---------------------------------------------------------------------------
# No-cache headers for all responses (prevents WebView2 from caching stale HTML)
# ---------------------------------------------------------------------------
@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ---------------------------------------------------------------------------
# Mic Meter — one-shot test only (avoids stream conflicts with recording)
# ---------------------------------------------------------------------------
@app.route("/api/test-mic", methods=["POST"])
def api_test_mic():
    if recording_event.is_set():
        return jsonify({"ok": False, "error": "Cannot test while recording"})
    p = None
    stream = None
    try:
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        # Read 3 chunks over ~200ms each
        peak = 0
        for _ in range(3):
            data = stream.read(1024, exception_on_overflow=False)
            count = len(data) // 2
            shorts = struct.unpack(f"{count}h", data)
            rms = math.sqrt(sum(s * s for s in shorts) / count) if count > 0 else 0
            peak = max(peak, min(100, int(rms / 30)))
            time.sleep(0.05)
        return jsonify({"ok": True, "level": peak})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})
    finally:
        if stream:
            try: stream.stop_stream(); stream.close()
            except: pass
        if p:
            try: p.terminate()
            except: pass


@app.route("/api/meter")
def api_meter():
    return jsonify({"level": 0, "active": False})


def beep(freq=800, duration=150):
    """Play a simple Windows beep."""
    if sys.platform == "win32":
        import winsound
        try:
            winsound.Beep(freq, duration)
        except Exception:
            pass


def set_status(status: str, message: str = None):
    global current_status, latest_result
    with status_lock:
        current_status = status
        if message:
            latest_result = message
    _notify_listeners(status, message)


def _notify_listeners(status: str, message: str = None):
    payload = json.dumps({"status": status, "message": message or ""})
    for q in list(status_callbacks):
        try:
            q.put(payload)
        except Exception:
            pass


def process_audio_worker():
    """Background thread: grab audio from queue and send to Google STT."""
    while not shutdown_event.is_set():
        try:
            audio = audio_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        set_status("processing")
        try:
            print("[STT] Sending audio to Google...")
            text = recognizer.recognize_google(audio, language="en-US")
            text = text.strip()
            print(f"[STT] Raw result: '{text}'")
            if text:
                print(f"[OK] Transcribed: {text}")

                # Copy to clipboard
                if AUTO_COPY:
                    try:
                        pyperclip.copy(text)
                        print("[CLIPBOARD] Copied to clipboard")
                    except Exception as e:
                        print(f"[WARN] Clipboard error: {e}")

                # Auto-type into focused field
                if AUTO_TYPE:
                    time.sleep(0.3)
                    if paste_text(text):
                        print("[TYPED] Pasted into active window")

                set_status("result", text)
                result_history.insert(0, {"text": text, "time": time.strftime("%H:%M:%S")})
                if len(result_history) > 50:
                    result_history.pop()
            else:
                print("[WARN] No speech detected")
                set_status("idle")
        except sr.UnknownValueError:
            print("[ERROR] Could not understand audio")
            set_status("error", "Could not understand — try speaking more clearly")
        except sr.RequestError as e:
            print(f"[ERROR] API error: {e}")
            set_status("error", f"Speech API error: {e}")
        except Exception as e:
            print(f"[ERROR] {e}")
            set_status("error", f"Error: {e}")
        finally:
            audio_queue.task_done()


def _rms(data_bytes):
    count = len(data_bytes) // 2
    if count == 0:
        return 0.0
    shorts = struct.unpack(f"{count}h", data_bytes)
    return math.sqrt(sum(s * s for s in shorts) / count)


def record_once():
    """Record a single utterance using speech_recognition and enqueue for transcription."""
    if recording_event.is_set():
        speak_text("Already recording")
        print("[INFO] Already recording — ignoring duplicate request")
        return
    recording_event.set()
    set_status("listening")

    if BEEP_ON_START:
        beep(880, 100)
        time.sleep(0.05)
        beep(1100, 100)

    try:
        with microphone as source:
            if recognizer.dynamic_energy_threshold:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = recognizer.listen(source, timeout=TIMEOUT_SECONDS, phrase_time_limit=PHRASE_TIME_LIMIT)
            audio_queue.put(audio)
    except sr.WaitTimeoutError:
        print("[WARN] Recording timed out -- no speech detected")
        set_status("idle")
    except OSError as e:
        print(f"[ERROR] Microphone error: {e}")
        set_status("idle")
    except Exception as e:
        print(f"[ERROR] Recording error: {e}")
        set_status("error", f"Recording error: {e}")
    finally:
        recording_event.clear()
        if BEEP_ON_STOP:
            beep(600, 100)


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    with status_lock:
        return jsonify({
            "status": current_status,
            "message": latest_result or "",
            "history": result_history[:20]
        })


@app.route("/api/record", methods=["POST"])
def api_record():
    if recording_event.is_set():
        speak_text("Already recording")
        return jsonify({"ok": False, "error": "Already recording"})
    t = threading.Thread(target=record_once, daemon=True)
    t.start()
    return jsonify({"ok": True})


@app.route("/api/mode", methods=["POST"])
def api_mode():
    data = request.get_json(force=True, silent=True) or {}
    mode = data.get("mode", "")
    if mode and mode_callback:
        try:
            mode_callback(mode)
        except Exception as e:
            print(f"[Mode callback error] {e}")
    return jsonify({"ok": True, "mode": mode})


@app.route("/api/close", methods=["POST"])
def api_close():
    if close_callback:
        try:
            close_callback()
        except Exception as e:
            print(f"[Close callback error] {e}")
    return jsonify({"ok": True})


@app.route("/api/console", methods=["POST"])
def api_console():
    data = request.get_json(force=True, silent=True) or {}
    if sys.platform == "win32" and data.get("action") == "show":
        show_console()
    return jsonify({"ok": True})


@app.route("/api/copy", methods=["POST"])
def api_copy():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "")
    if text:
        try:
            pyperclip.copy(text)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)})
    return jsonify({"ok": False, "error": "No text provided"})


@app.route("/api/type", methods=["POST"])
def api_type():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "")
    if text:
        if paste_text(text):
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Paste failed"})
    return jsonify({"ok": False, "error": "No text provided"})


@app.route("/api/test-type", methods=["POST"])
def api_test_type():
    if paste_text("Hello world"):
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Test type failed"})


@app.route("/api/clear", methods=["POST"])
def api_clear():
    global result_history, latest_result
    with status_lock:
        result_history = []
        latest_result = None
    return jsonify({"ok": True})


@app.route("/api/stream")
def api_stream():
    def event_stream():
        q = queue.Queue()
        status_callbacks.append(q)
        try:
            # Send initial state
            with status_lock:
                init = json.dumps({"status": current_status, "message": latest_result or ""})
            yield f"data: {init}\n\n"

            while not shutdown_event.is_set():
                try:
                    payload = q.get(timeout=1)
                    yield f"data: {payload}\n\n"
                except queue.Empty:
                    yield f"data: {json.dumps({'ping': True})}\n\n"
        finally:
            if q in status_callbacks:
                status_callbacks.remove(q)

    return Response(event_stream(), mimetype="text/event-stream")


# ---------------------------------------------------------------------------
# Settings & TTS endpoints
# ---------------------------------------------------------------------------
@app.route("/api/settings")
def api_settings_get():
    # Return default threshold when in auto mode so slider doesn't jump to weird values
    thresh = ENERGY_THRESHOLD if recognizer.dynamic_energy_threshold else recognizer.energy_threshold
    return jsonify({
        "auto_copy": AUTO_COPY,
        "auto_type": AUTO_TYPE,
        "energy_threshold": thresh,
        "energy_min": ENERGY_THRESHOLD_MIN,
        "energy_max": ENERGY_THRESHOLD_MAX,
        "dynamic_energy": recognizer.dynamic_energy_threshold
    })


@app.route("/api/settings", methods=["POST"])
def api_settings_post():
    global AUTO_COPY, AUTO_TYPE, DYNAMIC_ENERGY_ADJUSTMENT
    data = request.get_json(force=True, silent=True) or {}
    if "auto_copy" in data:
        AUTO_COPY = bool(data["auto_copy"])
    if "auto_type" in data:
        AUTO_TYPE = bool(data["auto_type"])
    if "energy_threshold" in data:
        val = int(data["energy_threshold"])
        val = max(ENERGY_THRESHOLD_MIN, min(ENERGY_THRESHOLD_MAX, val))
        recognizer.energy_threshold = val
        recognizer.dynamic_energy_threshold = False
    if "dynamic_energy" in data:
        recognizer.dynamic_energy_threshold = bool(data["dynamic_energy"])
        if recognizer.dynamic_energy_threshold:
            try:
                with microphone as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
            except Exception as e:
                print(f"[WARN] Could not re-calibrate mic: {e}")
    return jsonify({
        "ok": True,
        "auto_copy": AUTO_COPY,
        "auto_type": AUTO_TYPE,
        "energy_threshold": recognizer.energy_threshold,
        "dynamic_energy": recognizer.dynamic_energy_threshold
    })


@app.route("/api/calibrate", methods=["POST"])
def api_calibrate():
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
        recognizer.dynamic_energy_threshold = True
        print(f"[Auto-calibrated threshold: {recognizer.energy_threshold:.1f}]")
        return jsonify({
            "ok": True,
            "energy_threshold": recognizer.energy_threshold,
            "dynamic_energy": True
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/tts/voices")
def api_tts_voices():
    return jsonify({"voices": tts_voices})


@app.route("/api/shutdown", methods=["POST"])
def api_shutdown():
    def _shutdown():
        time.sleep(0.15)
        shutdown_event.set()
        # Close the pywebview window
        if close_callback:
            try:
                close_callback()
            except Exception as e:
                print(f"[Shutdown] Window close error: {e}")
        # Close the console window
        if sys.platform == "win32":
            try:
                hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if hwnd:
                    ctypes.windll.kernel32.FreeConsole()
            except Exception:
                pass
        time.sleep(0.3)
        os._exit(0)
    threading.Thread(target=_shutdown, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/tts", methods=["POST"])
def api_tts():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "").strip()
    voice_id = data.get("voice_id")
    if not text:
        return jsonify({"ok": False, "error": "No text provided"})
    if not tts_voices:
        return jsonify({"ok": False, "error": "TTS not available"})
    speak_text(text, voice_id)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def init_server():
    print("=" * 60)
    print("       ORBITSCRIBE - WEB GUI")
    print("=" * 60)

    recognizer.energy_threshold = ENERGY_THRESHOLD
    recognizer.pause_threshold = PAUSE_THRESHOLD
    recognizer.phrase_threshold = PHRASE_THRESHOLD
    recognizer.dynamic_energy_threshold = DYNAMIC_ENERGY_ADJUSTMENT

    print("[Initializing microphone...]")
    try:
        mics = sr.Microphone.list_microphone_names()
        if mics:
            print(f"[Found {len(mics)} audio device(s)]")
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
        print(f"[Auto-calibrated threshold: {recognizer.energy_threshold:.1f}]")
    except Exception as e:
        print(f"[WARN] Microphone init warning: {e}")

    print("[Initializing TTS engine...]")
    init_tts()

    # Announce startup via TTS
    speak_text("Voice to text ready")

    worker = threading.Thread(target=process_audio_worker, daemon=True)
    worker.start()

    set_status("idle")


def main():
    hide_console()
    init_server()

    url = f"http://{HOST}:{PORT}"
    print()
    print(f"  Opening browser at: {url}")
    print(f"  (If it doesn't open, navigate there manually)")
    print()
    print("  Press Ctrl+C in this window to stop the server")
    print("=" * 60)
    print()

    # Give server a moment to start, then open browser
    def open_browser():
        time.sleep(1.2)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        app.run(host=HOST, port=PORT, threaded=True, debug=False)
    except KeyboardInterrupt:
        print("\n[Shutting down...]")
        shutdown_event.set()
        sys.exit(0)


if __name__ == "__main__":
    main()
