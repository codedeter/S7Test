
import urllib.request
import json

try:
    print("Testing /api/status with urllib...")
    req = urllib.request.Request('http://127.0.0.1:3000/api/status')
    with urllib.request.urlopen(req, timeout=10) as response:
        print(f"Status code: {response.status}")
        data = response.read()
        print(f"Response data:")
        result = json.loads(data.decode('utf-8'))
        print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
