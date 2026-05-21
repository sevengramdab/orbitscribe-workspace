"""Click Console tab in devtools and capture screenshot."""
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

    # The devtools window is on the left side of the screen
    # Click on the "Console" tab in devtools
    # Based on the screenshot, devtools is at the top left, tabs are near y=40
    console_x = win.left + 120
    console_y = win.top + 50
    print(f"Clicking Console tab at ({console_x}, {console_y})...")
    pyautogui.click(console_x, console_y)
    time.sleep(1.0)

    # Capture screenshot
    region = (win.left, win.top, win.width, win.height)
    screenshot = pyautogui.screenshot(region=region)
    output_path = r"c:\Users\Shadow\voice to text engine\screenshots\vscode_console.png"
    screenshot.save(output_path)
    print(f"Screenshot saved to: {output_path}")

if __name__ == "__main__":
    main()
