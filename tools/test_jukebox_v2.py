"""
Test ACE-Step generation via the Jukebox frontend.
Takes screenshots and verifies via API.
"""
import subprocess
import time
import pyautogui
from PIL import ImageGrab
import urllib.request
import json

# 1. Open Chrome with the jukebox URL
subprocess.Popen([
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--new-window",
    "http://127.0.0.1:58080/jukebox/"
])
time.sleep(4)

# 2. Take initial screenshot
screenshot1 = ImageGrab.grab()
screenshot1.save(r"C:\Users\Shadow\voice to text engine\screenshots\jukebox_before_v2.png")
print("Saved: jukebox_before_v2.png")

# 3. Click Generate Track button (better coordinates based on screenshot)
# The button is in the ACE-Step panel, right side, near bottom.
# Screen is 1680x1050. Button appears around x=1450, y=900.
screen_width, screen_height = pyautogui.size()
btn_x = int(screen_width * 0.86)
btn_y = int(screen_height * 0.86)
print(f"Clicking Generate Track at ({btn_x}, {btn_y})")
pyautogui.click(btn_x, btn_y)

# 4. Wait for generation
time.sleep(50)

# 5. Take after screenshot
screenshot2 = ImageGrab.grab()
screenshot2.save(r"C:\Users\Shadow\voice to text engine\screenshots\jukebox_after_v2.png")
print("Saved: jukebox_after_v2.png")

# 6. Verify via API that generation works
req = urllib.request.Request(
    'http://127.0.0.1:58080/jukebox/api/acestep/generate',
    data=json.dumps({'caption': 'A peaceful acoustic guitar melody with soft vocals', 'duration': 5}).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
with urllib.request.urlopen(req, timeout=120) as resp:
    result = json.loads(resp.read().decode('utf-8'))
    print('API Test - OK:', result.get('ok'))
    print('API Test - Error:', result.get('error'))
    print('API Test - Audio URL:', result.get('audio_url'))

print("Done!")
