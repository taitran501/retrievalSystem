import requests
import json
import time

# Test the 3 failing queries mentioned by user
failing_queries = [
    "con lân",  # lion
    "rác nằm trên đường",  # trash on the road  
    "đám cháy"  # fire
]

print("Testing FAILING queries mentioned by user...")
print("=" * 60)

for query in failing_queries:
    print(f"\nQuery: '{query}'")
    
    start = time.time()
    response = requests.post(
        "http://localhost:8000/TextQuery",
        json={"First_query": query, "top_k": 10},
        headers={"Content-Type": "application/json"}
    )
    elapsed = time.time() - start
    
    
    if response.status_code == 200:
        result = response.json()
        total = result.get('total_results', 0)
        print(f"  Status: ✅ HTTP 200")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Results: {total} frames")
        
        if total > 0:
            # Show first 3 results
            kq = result.get('kq', [])[:3]
            for i, r in enumerate(kq, 1):
                print(f"    {i}. {r.get('video', 'N/A')} - Frame {r.get('frame_id', 'N/A')}")
    else:
        print(f"  Status: ❌ HTTP {response.status_code}")
        print(f"  Error: {response.text}")

print("\n" + "=" * 60)
