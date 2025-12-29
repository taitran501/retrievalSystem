import requests
import json
import time

# Test single query to check reranking
query = "người đàn ông đi bộ"

print(f"Testing query: '{query}'")
print("Checking if reranking is applied...")

start_time = time.time()
response = requests.post(
    "http://localhost:8000/TextQuery",
    json={"First_query": query, "top_k": 5},
    headers={"Content-Type": "application/json"}
)
end_time = time.time()

if response.status_code == 200:
    result = response.json()
    print(f"\n✅ Query successful!")
    print(f"   Total time: {end_time - start_time:.3f}s")
    print(f"   Results: {result.get('total_results', 0)} frames")
    print(f"\n   Check backend logs for:")
    print(f"   - 'use_reranking' or 'rerank' messages")
    print(f"   - Query execution time breakdown")
else:
    print(f"❌ Error: HTTP {response.status_code}")
    print(response.text)
