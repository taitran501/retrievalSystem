import requests
import json

url = "http://localhost:8000/SequentialQuery"
data = {
    "queries": ["người đi bộ", "xe máy màu xanh"],
    "top_k": 5
}

print(f"Testing Sequential Query with SAT: {data['queries']}")
resp = requests.post(url, json=data)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    result = resp.json()
    print(f"Total results: {result.get('total_results', 0)}")
    print(f"Translated queries: {result.get('queries')}")
    for i, res in enumerate(result.get('kq', [])):
        print(f"{i+1}. Video: {res['entity']['video']}, Frame: {res['entity']['frame_id']}, Match: {res['matched_steps']}")
else:
    print(f"Error: {resp.text}")
