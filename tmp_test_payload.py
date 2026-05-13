import sys
sys.path.insert(0, r'C:\Users\Shadow\voice to text engine')
from infinite_jukebox.acestep_bridge import AceStepBridge

bridge = AceStepBridge()
payload = bridge._build_generation_payload(bridge.params)
data = payload["data"]
print(f"Payload size: {len(data)} elements")
print(f"Element 42 (missing param): {data[42]}")
print(f"Element 43 (constrained_decoding_debug): {data[43]}")
print(f"Element 59 (auto_gen): {data[59]}")
