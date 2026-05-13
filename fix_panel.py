import re

path = r'C:\Users\Shadow\.vscode\extensions\orbstudio.orbitscribe-swarm-1.0.2\out\panels\SwarmPanel.js'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Save backup
with open(path + '.backup2', 'w', encoding='utf-8') as f:
    f.write(content)

# Find the getHtml method and everything until sendMessage
start = content.find('    static getHtml(webview, extensionUri, initialMode) {')
end = content.find('    sendMessage(message) {')

if start == -1 or end == -1:
    print(f'Could not find markers: start={start}, end={end}')
    exit(1)

old_block = content[start:end]

new_block = """    static getHtml(webview, extensionUri, initialMode) {
        return `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Test</title></head>
<body style="background:blue;padding:40px;">
<h1 id="test" style="color:white;font-family:sans-serif;">Waiting for JS...</h1>
<script>
document.body.style.background = '#0f1117';
document.getElementById('test').textContent = 'JAVASCRIPT IS RUNNING';
document.getElementById('test').style.color = '#22c55e';
console.log('TEST SCRIPT EXECUTED');
</script>
</body>
</html>`;
    }
"""

new_content = content.replace(old_block, new_block)

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Done. Replaced getHtml with minimal diagnostic test.')
