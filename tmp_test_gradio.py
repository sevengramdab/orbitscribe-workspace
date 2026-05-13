import json, urllib.request, urllib.error

# Test with minimal payload to check if parameter count is accepted
payload = {
    "data": [
        "test", "", 120.0, "", "", "en", 10.0, 7.0, True, "-1",
        None, 5.0, 2.0, None, "", 0.0, -1.0,
        "Fill the audio semantic mask based on the given conditions:",
        1.0, 0.0, "text2music", False, 0.0, 1.0, 3.0, "ode", "euler",
        0.0, 0.0, "", "mp3", "128k", "48000", 0.85, True, 2.0, 0.0, 0.9,
        "NO USER INPUT", True, False, True,
    ],
    "fn_index": 0,
}

req = urllib.request.Request(
    "http://127.0.0.1:7860/gradio_api/api/generation_wrapper",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json", "Accept": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        print("SUCCESS (or generation started):")
        print(json.dumps(result, indent=2)[:1000])
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8")
    print(f"HTTP ERROR {e.code}:")
    print(body[:2000])
except Exception as e:
    print(f"ERROR: {e}")
