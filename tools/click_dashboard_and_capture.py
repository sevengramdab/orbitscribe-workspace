"""Click the Dashboard tab in VS Code: Simple Browser, wait, and capture."""
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

    # Click on the Dashboard tab (approximate position based on screenshot)
    # The tab bar is below the header, around y = 220-250 relative to window top
    # Tabs: Splash | Dashboard | Creative | Architecture | Render Queue | Prerender Jet | Library | Album | NEG-SPACE | Global Ctrl
    # Dashboard is the second tab, around x = 300-400
    tab_x = win.left + 340
    tab_y = win.top + 240
    print(f"Clicking Dashboard tab at ({tab_x}, {tab_y})...")
    pyautogui.click(tab_x, tab_y)
    time.sleep(1.0)

    # Scroll down to see the preview iframe
    print("Scrolling down...")
    pyautogui.scroll(-5, win.left + win.width // 2, win.top + win.height // 2)
    time.sleep(1.0)

    # Wait for stream to connect
    print("Waiting 10 seconds for stream to connect...")
    time.sleep(10.0)

    # Capture screenshot
    region = (win.left, win.top, win.width, win.height)
    screenshot = pyautogui.screenshot(region=region)
    output_path = r"c:\Users\Shadow\voice to text engine\screenshots\vscode_dashboard.png"
    screenshot.save(output_path)
    print(f"Screenshot saved to: {output_path}")

if __name__ == "__main__":
    main()
