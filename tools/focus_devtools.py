"""Find and focus the devtools window."""
import pyautogui, pygetwindow, time

wins = [w for w in pygetwindow.getAllWindows()
        if w.title and 'Developer Tools' in w.title]
if not wins:
    print("No devtools window found")
    exit(1)

win = wins[0]
print(f"DevTools: '{win.title}' at ({win.left}, {win.top}) {win.width}x{win.height}")

# Click on title bar to bring to front
pyautogui.click(win.left + 100, win.top + 10)
time.sleep(0.3)

# Click on Console tab
pyautogui.click(win.left + 200, win.top + 45)
time.sleep(0.5)

# Capture
region = (win.left, win.top, win.width, win.height)
screenshot = pyautogui.screenshot(region=region)
output_path = r"c:\Users\Shadow\voice to text engine\screenshots\devtools_focused.png"
screenshot.save(output_path)
print(f"Saved to: {output_path}")
