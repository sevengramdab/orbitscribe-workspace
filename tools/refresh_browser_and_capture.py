"""Refresh VS Code: Simple Browser and capture screenshot."""
import pyautogui, pygetwindow, time

# Find VS Code: window
wins = [w for w in pygetwindow.getAllWindows()
        if "Visual Studio Code" in w.title or "Cursor" in w.title]
wins = [w for w in wins if w.width > 200 and w.height > 200]
if not wins:
    print("No VS Code: window found")
    exit(1)

win = wins[0]
print(f"Found window: '{win.title}' ({win.width}x{win.height})")

# Click on browser area to focus it
browser_x = win.left + win.width // 2
browser_y = win.top + 200
pyautogui.click(browser_x, browser_y)
time.sleep(0.5)

# Press F5 to refresh
print("Refreshing browser...")
pyautogui.keyDown('f5')
pyautogui.keyUp('f5')
time.sleep(8.0)  # Wait for page to reload and stream to connect

# Capture screenshot
region = (win.left, win.top, win.width, win.height)
screenshot = pyautogui.screenshot(region=region)
output_path = r"c:\Users\Shadow\voice to text engine\screenshots\vscode_after_refresh.png"
screenshot.save(output_path)
print(f"Saved to: {output_path}")
