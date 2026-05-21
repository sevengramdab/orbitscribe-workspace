"""Open VS Code: Simple Browser with the DJ panel URL."""
import pyautogui, pygetwindow, time, sys

def main():
    wins = [w for w in pygetwindow.getAllWindows()
            if "Visual Studio Code" in w.title or "Cursor" in w.title]
    wins = [w for w in wins if w.width > 200 and w.height > 200]
    if not wins:
        print("[open_simple_browser] No VS Code: window found.")
        sys.exit(1)

    win = wins[0]
    print(f"[open_simple_browser] Found window: '{win.title}' ({win.width}x{win.height})")

    # Click on the title bar to focus the window
    print("[open_simple_browser] Clicking to focus...")
    pyautogui.click(win.left + 200, win.top + 10)
    time.sleep(0.5)

    # Open Command Palette
    print("[open_simple_browser] Opening Command Palette...")
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('shift')
    pyautogui.keyDown('p')
    pyautogui.keyUp('p')
    pyautogui.keyUp('shift')
    pyautogui.keyUp('ctrl')
    time.sleep(1.5)

    # Type Simple Browser command
    print("[open_simple_browser] Typing 'Simple Browser: Show'...")
    pyautogui.typewrite("""Simple Browser: Show""", interval=0.02)
    time.sleep(1.0)

    # Press Enter
    pyautogui.keyDown('return')
    pyautogui.keyUp('return')
    time.sleep(3.0)

    # Type URL
    print("[open_simple_browser] Typing URL...")
    pyautogui.typewrite("""http://localhost:8503""", interval=0.02)
    time.sleep(0.5)

    # Press Enter
    pyautogui.keyDown('return')
    pyautogui.keyUp('return')
    time.sleep(6.0)

    print("[open_simple_browser] Done.")

if __name__ == "__main__":
    main()
