import pygetwindow as gw
for w in gw.getAllWindows():
    if w.title and ('Developer Tools' in w.title or 'devtools' in w.title.lower()):
        print(f"DevTools window: '{w.title}' at ({w.left}, {w.top}) size {w.width}x{w.height}")
