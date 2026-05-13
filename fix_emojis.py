import sys

path = r'C:\Users\Shadow\.vscode\extensions\orbstudio.orbitscribe-swarm-1.0.2\out\panels\SwarmPanel.js'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace corrupted emojis
replacements = [
    ('<h1>?? ORBITSCRIBE SWARM</h1>', '<h1>🐝 ORBITSCRIBE SWARM</h1>'),
    ('<button class="voice-btn" id="voiceBtn" title="Voice input (requires OrbitScribe)">??</button>', 
     '<button class="voice-btn" id="voiceBtn" title="Voice input (requires OrbitScribe)">🎤</button>'),
    ('vscode.window.showInformationMessage(`?? Undone ${undoneCount} change(s).`);',
     'vscode.window.showInformationMessage(`↩️ Undone ${undoneCount} change(s).`);'),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f'Replaced: {old[:30]}... -> {new[:30]}...')
    else:
        print(f'Not found: {old[:30]}...')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open(path, 'r', encoding='utf-8') as f:
    verify = f.read()

print(f"Bee present: {'🐝' in verify}")
print(f"Mic present: {'🎤' in verify}")
print(f"Undo present: {'↩️' in verify}")
