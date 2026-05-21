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

    # Click on the main editor area to shift focus away from Kimi panel/terminal
    editor_x = win.left + win.width // 2
    editor_y = win.top + win.height // 2
    print(f"[open_simple_browser] Clicking editor area at ({editor_x}, {editor_y})...")
    pyautogui.click(editor_x, editor_y)
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
    print("[open_simple_browser] Typing command...")
    pyautogui.typewrite(""">Simple Browser: Show""", interval=0.02)
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
