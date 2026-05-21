"""Click Console tab in devtools window and capture."""
import pyautogui, pygetwindow, time

# Find devtools window
wins = [w for w in pygetwindow.getAllWindows()
        if w.title and 'Developer Tools' in w.title]
if not wins:
    print("No devtools window found")
    exit(1)

win = wins[0]
print(f"DevTools: '{win.title}' at ({win.left}, {win.top}) {win.width}x{win.height}")

# Click on Console tab (second tab from left in devtools)
# Tabs are around y=55, Elements is ~x=60, Console is ~x=120
console_x = win.left + 120
console_y = win.top + 55
print(f"Clicking Console at ({console_x}, {console_y})")
pyautogui.click(console_x, console_y)
time.sleep(1.0)

# Capture the devtools window
region = (win.left, win.top, win.width, win.height)
screenshot = pyautogui.screenshot(region=region)
output_path = r"c:\Users\Shadow\voice to text engine\screenshots\devtools_console.png"
screenshot.save(output_path)
print(f"Saved to: {output_path}")
