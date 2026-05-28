import sys, re, os
sys.path.insert(0, 'swarm-backend')
from core.business_tools.registry import registry
tools = set(t['name'] for t in registry.list_tools())

agent_dir = 'money_engine/agents'
for fname in sorted(os.listdir(agent_dir)):
    if not fname.endswith('.py') or fname == '__init__.py':
        continue
    path = os.path.join(agent_dir, fname)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    for m in re.finditer(r'generate_asset_via_registry\(\s*["\']([^"\']+)["\']', content):
        tool_name = m.group(1)
        if tool_name not in tools:
            print(f'{fname}: UNKNOWN tool "{tool_name}"')
