import urllib.request

r = urllib.request.urlopen('http://localhost:58091/monetization', timeout=3)
html = r.read().decode()

print('has old style.css:', 'href="style.css"' in html)
print('has new style.css:', 'href="/monetization/static/style.css"' in html)
print('has old app.js:', 'src="app.js"' in html)
print('has new app.js:', 'src="/monetization/static/app.js"' in html)

for path in ['/monetization/static/style.css', '/monetization/static/app.js']:
    r2 = urllib.request.urlopen('http://localhost:58091' + path, timeout=3)
    print(path, '->', r2.status, len(r2.read()), 'bytes')
