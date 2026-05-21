"""Click precisely on Console tab in devtools."""
import pyautogui, pygetwindow, time

wins = [w for w in pygetwindow.getAllWindows()
        if w.title and 'Developer Tools' in w.title]
if not wins:
    print("No devtools window found")
    exit(1)

win = wins[0]
print(f"DevTools: '{win.title}' at ({win.left}, {win.top})")

# Click directly on the "Console" text in the tab bar
# Based on screenshot analysis: Console tab is around x=210, y=47 within devtools
console_x = win.left + 210
console_y = win.top + 47
print(f"Clicking Console tab at ({console_x}, {console_y})")
pyautogui.click(console_x, console_y)
time.sleep(1.5)

# Capture
region = (win.left, win.top, win.width, win.height)
screenshot = pyautogui.screenshot(region=region)
output_path = r"c:\Users\Shadow\voice to text engine\screenshots\devtools_console3.png"
screenshot.save(output_path)
print(f"Saved to: {output_path}")
