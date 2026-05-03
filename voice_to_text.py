#!/usr/bin/env python3
"""
Voice-to-Text Tool
==================
Press Ctrl+Alt+V to start recording. Speak, then release to transcribe.
The transcribed text is:
1. Copied to your clipboard (paste with Ctrl+V anywhere)
2. Optionally typed directly into the active window

Requirements: Python 3.8+, microphone access, internet connection
"""

import os
import sys
import time
import threading
import queue
import signal

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
    import keyboard
except ImportError:
    MISSING.append("keyboard")

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
    print("    pip install SpeechRecognition PyAudio pyperclip pyautogui keyboard")
    print("=" * 60)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HOTKEY = "ctrl+alt+v"          # Global hotkey to trigger recording
TIMEOUT_SECONDS = 10           # Max seconds to wait for speech to START
PHRASE_TIME_LIMIT = 60         # Max seconds for a single utterance
ENERGY_THRESHOLD = 300         # Microphone sensitivity (lower = more sensitive)
PAUSE_THRESHOLD = 2.0          # Seconds of silence before auto-stop (higher = less cutoff)
PHRASE_THRESHOLD = 0.3         # Minimum seconds of speaking to start recording
DYNAMIC_ENERGY_ADJUSTMENT = True
AUTO_TYPE = True               # Set to False if you only want clipboard copy
BEEP_ON_START = True
BEEP_ON_STOP = True

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
recognizer = sr.Recognizer()
microphone = sr.Microphone()
recording_event = threading.Event()
audio_queue = queue.Queue()
shutdown_event = threading.Event()
status_lock = threading.Lock()
current_status = "idle"  # idle | listening | processing


def beep(freq=800, duration=150):
    """Play a simple Windows beep."""
    if sys.platform == "win32":
        import winsound
        try:
            winsound.Beep(freq, duration)
        except Exception:
            pass


def set_status(status: str):
    global current_status
    with status_lock:
        current_status = status
    if status == "listening":
        print("\n[MIC ON] LISTENING... Speak now")
    elif status == "processing":
        print("[...] Processing...")
    elif status == "idle":
        print("[IDLE] Press Ctrl+Alt+V to speak")


def process_audio_worker():
    """Background thread: grab audio from queue and send to Google STT."""
    while not shutdown_event.is_set():
        try:
            audio = audio_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        set_status("processing")
        try:
            text = recognizer.recognize_google(audio, language="en-US")
            text = text.strip()
            if text:
                print(f"[OK] Transcribed: {text}")

                # Copy to clipboard
                try:
                    pyperclip.copy(text)
                    print("[CLIPBOARD] Copied to clipboard -- press Ctrl+V to paste")
                except Exception as e:
                    print(f"[WARN] Clipboard error: {e}")

                # Auto-type into focused field
                if AUTO_TYPE:
                    # Small delay so user can move focus if needed
                    time.sleep(0.3)
                    try:
                        # We suppress the hotkey keys so they don't get typed
                        pyautogui.typewrite(text, interval=0.01)
                        print("[TYPED] Typed into active window")
                    except Exception as e:
                        print(f"[WARN] Typing error: {e}")
            else:
                print("[WARN] No speech detected]")
        except sr.UnknownValueError:
            print("[ERROR] Could not understand audio")
        except sr.RequestError as e:
            print(f"[ERROR] API error: {e}")
        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            set_status("idle")
            audio_queue.task_done()


def record_once():
    """Record a single utterance and enqueue for transcription."""
    if recording_event.is_set():
        beep(400, 100)
        time.sleep(0.05)
        beep(400, 100)
        print("[INFO] Already recording — ignoring duplicate hotkey")
        return  # Already recording
    recording_event.set()
    set_status("listening")

    if BEEP_ON_START:
        beep(880, 100)
        time.sleep(0.05)
        beep(1100, 100)

    try:
        with microphone as source:
            # Adjust for ambient noise quickly
            if DYNAMIC_ENERGY_ADJUSTMENT:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)

            audio = recognizer.listen(
                source,
                timeout=TIMEOUT_SECONDS,
                phrase_time_limit=PHRASE_TIME_LIMIT,
            )
            audio_queue.put(audio)
    except sr.WaitTimeoutError:
        print("[WARN] Recording timed out -- no speech detected")
        set_status("idle")
    except OSError as e:
        print(f"[ERROR] Microphone error: {e}")
        print("    Make sure your microphone is connected and not in use by another app.")
        set_status("idle")
    except Exception as e:
        print(f"[ERROR] Recording error: {e}")
        set_status("idle")
    finally:
        recording_event.clear()
        if BEEP_ON_STOP:
            beep(600, 100)


def on_hotkey():
    """Called when the global hotkey is pressed."""
    t = threading.Thread(target=record_once, daemon=True)
    t.start()


def print_banner():
    print("=" * 60)
    print("       ORBITSCRIBE")
    print("=" * 60)
    print(f"  Hotkey:        {HOTKEY.upper()}")
    print(f"  Auto-type:     {'ON' if AUTO_TYPE else 'OFF'}")
    print(f"  Max duration:  {TIMEOUT_SECONDS}s")
    print()
    print("  1. Press the hotkey anywhere")
    print("  2. Speak clearly into your microphone")
    print("  3. Release — text is copied & typed automatically")
    print()
    print("  Press Ctrl+C in this window to exit")
    print("=" * 60)
    print()


def main():
    hide_console()
    print_banner()

    # Configure recognizer
    recognizer.energy_threshold = ENERGY_THRESHOLD
    recognizer.pause_threshold = PAUSE_THRESHOLD
    recognizer.phrase_threshold = PHRASE_THRESHOLD
    recognizer.dynamic_energy_threshold = DYNAMIC_ENERGY_ADJUSTMENT

    # Warm-up: list microphones and do a quick ambient calibration
    print("[Initializing microphone...]")
    try:
        mics = sr.Microphone.list_microphone_names()
        if mics:
            print(f"[Found {len(mics)} audio device(s)]")
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
        print(f"[Energy threshold set to {recognizer.energy_threshold}]")
    except Exception as e:
        print(f"[WARN] Microphone init warning: {e}")

    # Start background transcription worker
    worker = threading.Thread(target=process_audio_worker, daemon=True)
    worker.start()

    # Register global hotkey
    try:
        keyboard.add_hotkey(HOTKEY, on_hotkey)
    except Exception as e:
        print(f"[ERROR] Failed to register hotkey: {e}")
        print("    Try running this script as Administrator.")
        sys.exit(1)

    set_status("idle")

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Shutting down...]")
        shutdown_event.set()
        keyboard.unhook_all_hotkeys()
        sys.exit(0)


if __name__ == "__main__":
    main()
