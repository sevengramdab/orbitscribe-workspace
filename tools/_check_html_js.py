import re

with open(r'c:\Users\Shadow\voice to text engine\templates\monetization_dashboard.html', 'r', encoding='utf-8') as f:
    html = f.read()

m = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
if m:
    js = m.group(1)
    stack = []
    in_string = None
    escape = False
    for i, ch in enumerate(js):
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if in_string:
            if ch == in_string:
                in_string = None
            continue
        if ch in '"\'`':
            in_string = ch
            continue
        if ch == '/':
            if i + 1 < len(js):
                if js[i + 1] == '/':
                    j = js.find('\n', i)
                    if j == -1:
                        break
                    continue
                elif js[i + 1] == '*':
                    j = js.find('*/', i + 2)
                    if j == -1:
                        break
                    continue
        if ch in '({[':
            stack.append(ch)
        elif ch in ')}]':
            if not stack:
                print(f'UNBALANCED at {i}: {ch}')
                exit(1)
            last = stack.pop()
            pairs = {'(': ')', '{': '}', '[': ']'}
            if pairs[last] != ch:
                print(f'MISMATCH at {i}: expected {pairs[last]}, got {ch}')
                exit(1)
    if stack:
        print('UNCLOSED:', stack)
        exit(1)
    print('JS BALANCED: OK')
else:
    print('NO SCRIPT FOUND')
