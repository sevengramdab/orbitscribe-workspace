"""
Reopen the ORBIT Command Deck via VS Code: Command Palette.
"""
import pyautogui, pygetwindow, time, sys

def main():
    wins = [w for w in pygetwindow.getAllWindows()
            if "Visual Studio Code" in w.title or "Cursor" in w.title]
    wins = [w for w in wins if w.width > 200 and w.height > 200]
    if not wins:
        print("[reopen_cmddeck] No VS Code: window found.")
        sys.exit(1)

    win = wins[0]
    print(f"[reopen_cmddeck] Found window: '{win.title}' ({win.width}x{win.height})")
    win.activate()
    time.sleep(1.0)

    # Open Command Palette
    print("[reopen_cmddeck] Opening Command Palette...")
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('shift')
    pyautogui.keyDown('p')
    pyautogui.keyUp('p')
    pyautogui.keyUp('shift')
    pyautogui.keyUp('ctrl')
    time.sleep(1.2)

    # Type command slowly to ensure it registers
    print("[reopen_cmddeck] Typing command...")
    pyautogui.typewrite("""Open ORBIT Command Deck""", interval=0.02)
    time.sleep(1.0)

    # Press Enter
    pyautogui.keyDown('return')
    pyautogui.keyUp('return')
    time.sleep(3.0)

    print("[reopen_cmddeck] Done.")

if __name__ == "__main__":
    main()
