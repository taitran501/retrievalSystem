#!/usr/bin/env python3
"""
Quick test script to verify the sequential query system is working
"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Test the 5-step DRES example quickly
queries = [
    "news story online scams malicious links",
    "female interviewer woman reporter",
    "aerial view trees mountain rocky mountainside",
    "aerial shot trees rocky cliff mountain",
    "girls selfie sticks Guizhou China"
]

print("Testing 5-step DRES query...")
print("Steps:")
for i, q in enumerate(queries, 1):
    print(f"  {i}. {q}")

response = requests.post(
    f"{BASE_URL}/SequentialQuery",
    json={"queries": queries, "top_k": 10, "require_all_steps": False},
    timeout=30
)

if response.status_code == 200:
    data = response.json()
    print(f"\n✅ Success! Found {len(data['kq'])} results")
    print(f"Query time: {data.get('execution_time', 0):.2f}s")
    
    # Show first 3 results
    print("\nTop 3 results:")
    for i, r in enumerate(data['kq'][:3], 1):
        entity = r['entity']
        steps = ','.join(str(s+1) for s in r['matched_steps'])
        print(f"  {i}. {entity['video']} frame {entity['frame_id']} - Steps: {steps} - Completeness: {r['completeness']*100:.0f}%")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
