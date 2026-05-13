import json, urllib.request

req = urllib.request.Request('http://127.0.0.1:7860/gradio_api/info', headers={'Accept': 'application/json'})
with urllib.request.urlopen(req, timeout=10) as resp:
    d = json.loads(resp.read().decode('utf-8'))

params = d.get('named_endpoints', {}).get('/generation_wrapper', {}).get('parameters', [])
nums = [int(p['parameter_name'].replace('param_', '')) for p in params]
print('Max param:', max(nums))
print('Total params:', len(params))
for p in params:
    n = int(p['parameter_name'].replace('param_', ''))
    if n >= 42:
        print(f"{p['parameter_name']}: {p['label']} default={p.get('parameter_default', 'N/A')}")
