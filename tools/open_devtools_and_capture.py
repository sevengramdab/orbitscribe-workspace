"""Open devtools in VS Code: Simple Browser and capture screenshot."""
import pyautogui, pygetwindow, time, sys

def main():
    wins = [w for w in pygetwindow.getAllWindows()
            if "Visual Studio Code" in w.title or "Cursor" in w.title]
    wins = [w for w in wins if w.width > 200 and w.height > 200]
    if not wins:
        print("No VS Code: window found.")
        sys.exit(1)

    win = wins[0]
    print(f"Found window: '{win.title}' ({win.width}x{win.height})")

    # Click on the Simple Browser area to focus it
    browser_x = win.left + win.width // 2
    browser_y = win.top + 200
    pyautogui.click(browser_x, browser_y)
    time.sleep(0.5)

    # Press F12 to open devtools
    print("Pressing F12 to open devtools...")
    pyautogui.keyDown('f12')
    pyautogui.keyUp('f12')
    time.sleep(2.0)

    # Capture screenshot
    region = (win.left, win.top, win.width, win.height)
    screenshot = pyautogui.screenshot(region=region)
    output_path = r"c:\Users\Shadow\voice to text engine\screenshots\vscode_devtools.png"
    screenshot.save(output_path)
    print(f"Screenshot saved to: {output_path}")

if __name__ == "__main__":
    main()
