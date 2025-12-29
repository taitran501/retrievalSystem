import requests
import json

# Test Vietnam news queries
test_queries = [
    "chủ tịch nước phát biểu",
    "thủ tướng tham dự hội nghị",
    "lễ khánh thành",
    "họp báo tại tp.hcm",
]

print("Testing Vietnam News Dictionary...")
print("=" * 60)

for query in test_queries:
    print(f"\nQuery: '{query}'")
    
    response = requests.post(
        "http://localhost:8000/TextQuery",
        json={"First_query": query, "top_k": 3},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"  Status: ✅ HTTP 200")
        print(f"  Results: {result.get('total_results', 0)} frames")
    else:
        print(f"  Status: ❌ HTTP {response.status_code}")
        print(f"  Error: {response.text}")

print("\n" + "=" * 60)
print("Test complete!")
