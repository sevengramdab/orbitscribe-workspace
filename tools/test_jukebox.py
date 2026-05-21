"""
Open the Infinite Jukebox dashboard and test ACE-Step generation.
Takes screenshots before and after clicking Generate Track.
"""
import subprocess
import time
import pyautogui
from PIL import ImageGrab

# 1. Open Chrome with the jukebox URL
subprocess.Popen([
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--new-window",
    "http://127.0.0.1:58080/jukebox/"
])

# Wait for Chrome to open
time.sleep(4)

# 2. Take initial screenshot
screenshot1 = ImageGrab.grab()
screenshot1.save(r"C:\Users\Shadow\voice to text engine\screenshots\jukebox_before_generate.png")
print("Saved: screenshots/jukebox_before_generate.png")

# 3. Find and click the Generate Track button
# The button is in the ACE-Step section. We'll use pyautogui to locate it.
# First, let's try to find it by looking for the button text.
time.sleep(2)

# Try to locate the Generate Track button by its color/position
# The button is cyan colored near the bottom of the ACE-Step panel.
# Let's just click a known coordinate based on the dashboard layout.
# The panel is on the right side. Button should be around x=1450, y=650
# But let's try to be smarter and use image recognition.

# Actually, let's just try clicking at coordinates where the button should be.
# The dashboard is on the right side of the screen. ACE-Step panel is the last section.
screen_width, screen_height = pyautogui.size()
print(f"Screen: {screen_width}x{screen_height}")

# The Generate Track button is in the ACE-Step section.
# Based on the screenshot, it's in the right panel, roughly in the lower half.
# Let's click around where it should be.
# x ~ 75% of screen width, y ~ 65-70% of screen height
btn_x = int(screen_width * 0.75)
btn_y = int(screen_height * 0.72)

print(f"Clicking Generate Track at ({btn_x}, {btn_y})")
pyautogui.click(btn_x, btn_y)

# 4. Wait for generation (can take 30-60 seconds)
print("Waiting for generation...")
time.sleep(45)

# 5. Take after screenshot
screenshot2 = ImageGrab.grab()
screenshot2.save(r"C:\Users\Shadow\voice to text engine\screenshots\jukebox_after_generate.png")
print("Saved: screenshots/jukebox_after_generate.png")
print("Done!")
