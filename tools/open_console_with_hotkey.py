"""Open Console in devtools with Ctrl+Shift+J and capture."""
import pyautogui, pygetwindow, time

# Find devtools window
wins = [w for w in pygetwindow.getAllWindows()
        if w.title and 'Developer Tools' in w.title]
if not wins:
    print("No devtools window found")
    exit(1)

win = wins[0]
print(f"DevTools: '{win.title}' at ({win.left}, {win.top})")

# Click on devtools to focus it
pyautogui.click(win.left + 100, win.top + 50)
time.sleep(0.3)

# Press Ctrl+Shift+J to open Console
print("Pressing Ctrl+Shift+J...")
pyautogui.keyDown('ctrl')
pyautogui.keyDown('shift')
pyautogui.keyDown('j')
pyautogui.keyUp('j')
pyautogui.keyUp('shift')
pyautogui.keyUp('ctrl')
time.sleep(1.0)

# Capture the devtools window
region = (win.left, win.top, win.width, win.height)
screenshot = pyautogui.screenshot(region=region)
output_path = r"c:\Users\Shadow\voice to text engine\screenshots\devtools_console2.png"
screenshot.save(output_path)
print(f"Saved to: {output_path}")
