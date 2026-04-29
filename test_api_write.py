import requests
import json
import time

payload = {
    'class_id': f'TEST-WAMP-{int(time.time())}',
    'class_name': 'WAMP Verification Test Class',
    'section': 'A',
    'semester': '1'
}
print(f'Creating class: {payload["class_id"]}')
try:
    r = requests.post('http://localhost:8080/api/backend/classes', json=payload, timeout=5)
    print(f'Status: {r.status_code}')
    print(f'Response: {json.dumps(r.json(), indent=2)}')
except Exception as e:
    print(f'Error: {e}')
