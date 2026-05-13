import pyautogui, time
pyautogui.FAILSAFE = False

# Switch to Chrome via Alt+Tab
pyautogui.keyDown('alt')
pyautogui.keyDown('tab')
pyautogui.keyUp('tab')
pyautogui.keyUp('alt')
time.sleep(0.5)

# Open console
pyautogui.keyDown('ctrl')
pyautogui.keyDown('shift')
pyautogui.keyDown('j')
pyautogui.keyUp('j')
pyautogui.keyUp('shift')
pyautogui.keyUp('ctrl')
time.sleep(0.5)

# Type diagnostic command
cmd1 = "window.jukeboxFluid ? console.log('dt:', window.jukeboxFluid.dt, 'running:', window.jukeboxFluid.running, 'bg:', window.jukeboxFluid._themeBgColor) : console.log('no fluid')"
pyautogui.typewrite(cmd1, interval=0.01)
pyautogui.keyDown('return')
pyautogui.keyUp('return')
time.sleep(0.3)

# Check for NaN in WebGL textures - read a pixel
cmd2 = "console.log('canvas size:', window.jukeboxFluid ? [window.jukeboxFluid.canvas.width, window.jukeboxFluid.canvas.height] : 'n/a')"
pyautogui.typewrite(cmd2, interval=0.01)
pyautogui.keyDown('return')
pyautogui.keyUp('return')
time.sleep(0.3)

pyautogui.screenshot('chrome_diag_result.png')
print('Saved chrome_diag_result.png')
