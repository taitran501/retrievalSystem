"""
Quick test to diagnose why TextQuery returns 0 results
"""
import requests
import json

# Test 1: Check health
print("=" * 60)
print("TEST 1: Health Check")
resp = requests.get("http://localhost:8000/health")
print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}")

# Test 2: Check config
print("\n" + "=" * 60)
print("TEST 2: Config Check")
resp = requests.get("http://localhost:8000/config")
print(f"Status: {resp.status_code}")
print(f"Response: {json.dumps(resp.json(), indent=2)}")

# Test 3: Simple text query
print("\n" + "=" * 60)
print("TEST 3: Simple Text Query - 'person'")
query_data = {
    "First_query": "person",
    "Next_query": "",
    "top_k": 5
}
resp = requests.post("http://localhost:8000/TextQuery", json=query_data)
print(f"Status: {resp.status_code}")
result = resp.json()
print(f"Total results: {result.get('total_results', 0)}")
print(f"Results preview: {json.dumps(result, indent=2)[:500]}")

# Test 4: Vietnamese query
print("\n" + "=" * 60)
print("TEST 4: Vietnamese Query - 'người đi bộ'")
query_data = {
    "First_query": "một người đang chạy cực nhanh",
    "Next_query": "",
    "top_k": 5
}
resp = requests.post("http://localhost:8000/TextQuery", json=query_data)
print(f"Status: {resp.status_code}")
result = resp.json()
print(f"Total results: {result.get('total_results', 0)}")
print(f"Results preview: {json.dumps(result, indent=2)[:500]}")
