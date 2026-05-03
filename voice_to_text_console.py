#!/usr/bin/env python3
"""
Voice-to-Text Tool (Console Version)
====================================
No admin rights required. No global hotkeys.
Just press Enter to record, then speak.

Great for: Copilot Chat, VS Code terminal, browser text boxes, etc.
"""

import os
import sys
import time
import threading
import queue

# Fix Windows console encoding
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

# Dependency check
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

if MISSING:
    print("=" * 60)
    print("MISSING DEPENDENCIES")
    print("=" * 60)
    print("Please install: pip install SpeechRecognition PyAudio pyperclip pyautogui")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TIMEOUT_SECONDS = 10
PHRASE_TIME_LIMIT = 60
ENERGY_THRESHOLD = 300
PAUSE_THRESHOLD = 2.0
PHRASE_THRESHOLD = 0.3
AUTO_TYPE = True

recognizer = sr.Recognizer()
microphone = sr.Microphone()
recording_event = threading.Event()


def beep(freq=800, duration=150):
    if sys.platform == "win32":
        import winsound
        try:
            winsound.Beep(freq, duration)
        except Exception:
            pass


def record_and_transcribe():
    if recording_event.is_set():
        print("[INFO] Already recording — please wait")
        beep(400, 100)
        time.sleep(0.05)
        beep(400, 100)
        return

    recording_event.set()
    try:
        print("\n[MIC ON] Listening... Speak now")
        beep(880, 100)
        time.sleep(0.05)
        beep(1100, 100)

        try:
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = recognizer.listen(source, timeout=TIMEOUT_SECONDS, phrase_time_limit=PHRASE_TIME_LIMIT)
        except sr.WaitTimeoutError:
            print("[WARN] Timed out -- no speech detected")
            beep(400, 200)
            return
        except OSError as e:
            print(f"[ERROR] Microphone error: {e}")
            return
        except Exception as e:
            print(f"[ERROR] Recording error: {e}")
            return

        beep(600, 100)
        print("[...] Processing...")

        try:
            text = recognizer.recognize_google(audio, language="en-US").strip()
            if not text:
                print("[WARN] No speech detected")
                return

            print(f"[OK] Transcribed: {text}")

            # Clipboard
            try:
                pyperclip.copy(text)
                print("[CLIPBOARD] Copied to clipboard")
            except Exception as e:
                print(f"[WARN] Clipboard error: {e}")

            # Auto-type
            if AUTO_TYPE:
                time.sleep(0.2)
                try:
                    pyautogui.typewrite(text, interval=0.01)
                    print("[TYPED] Typed into active window")
                except Exception as e:
                    print(f"[WARN] Typing error: {e}")

        except sr.UnknownValueError:
            print("[ERROR] Could not understand audio")
        except sr.RequestError as e:
            print(f"[ERROR] API error: {e}")
        except Exception as e:
            print(f"[ERROR] {e}")
    finally:
        recording_event.clear()


def main():
    hide_console()
    print("=" * 60)
    print("       ORBITSCRIBE (Console Version)")
    print("=" * 60)
    print("  No admin rights needed!")
    print()
    print("  1. Click the chat box where you want text typed")
    print("  2. Come back here and press Enter to record")
    print("  3. Speak clearly")
    print("  4. Text is copied and typed automatically")
    print()
    print("  Press Ctrl+C to exit")
    print("=" * 60)
    print()

    recognizer.energy_threshold = ENERGY_THRESHOLD
    recognizer.pause_threshold = PAUSE_THRESHOLD
    recognizer.phrase_threshold = PHRASE_THRESHOLD
    recognizer.dynamic_energy_threshold = True

    print("[Initializing microphone...]")
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
        print(f"[Ready] Energy threshold: {recognizer.energy_threshold:.1f}")
    except Exception as e:
        print(f"[WARN] Mic init warning: {e}")

    print("\nPress Enter to start recording (or Ctrl+C to quit)...")

    try:
        while True:
            input()
            record_and_transcribe()
            print("\nPress Enter to record again...")
    except KeyboardInterrupt:
        print("\n[Goodbye]")
        sys.exit(0)


if __name__ == "__main__":
    main()
