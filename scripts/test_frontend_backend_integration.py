#!/usr/bin/env python3
"""
Test frontend-backend integration
Simulates what frontend does when user clicks search
"""

import requests
import json
import time

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:8007"

print("="*70)
print("FRONTEND-BACKEND INTEGRATION TEST")
print("="*70)

# Test 1: Frontend is accessible
print("\n1. Testing Frontend Server...")
try:
    response = requests.get(FRONTEND_URL, timeout=5)
    if response.status_code == 200:
        print(f"   ✅ Frontend accessible at {FRONTEND_URL}")
    else:
        print(f"   ❌ Frontend returned status {response.status_code}")
except Exception as e:
    print(f"   ❌ Cannot access frontend: {e}")

# Test 2: Backend health check
print("\n2. Testing Backend Health...")
try:
    response = requests.get(f"{BACKEND_URL}/health", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Backend healthy: {data}")
    else:
        print(f"   ❌ Backend health check failed: {response.status_code}")
except Exception as e:
    print(f"   ❌ Cannot access backend: {e}")

# Test 3: Legacy TextQuery (what frontend uses for 2-step queries)
print("\n3. Testing Legacy TextQuery Endpoint...")
try:
    start = time.time()
    response = requests.post(
        f"{BACKEND_URL}/TextQuery",
        json={"First_query": "person walking", "Next_query": ""},
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    elapsed = time.time() - start
    
    if response.status_code == 200:
        data = response.json()
        count = len(data.get('kq', []))
        print(f"   ✅ TextQuery works: {count} results in {elapsed:.2f}s")
    else:
        print(f"   ❌ TextQuery failed: {response.status_code}")
        print(f"      Response: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ TextQuery error: {e}")

# Test 4: Sequential Query (new multi-step feature)
print("\n4. Testing SequentialQuery Endpoint...")
try:
    start = time.time()
    response = requests.post(
        f"{BACKEND_URL}/SequentialQuery",
        json={
            "queries": ["person walking", "person sitting", "person standing"],
            "top_k": 20,
            "require_all_steps": False
        },
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    elapsed = time.time() - start
    
    if response.status_code == 200:
        data = response.json()
        count = len(data.get('kq', []))
        num_steps = data.get('num_steps', 0)
        print(f"   ✅ SequentialQuery works: {count} results in {elapsed:.2f}s")
        print(f"      Steps: {num_steps}")
        if count > 0:
            first = data['kq'][0]
            steps = first.get('matched_steps', [])
            completeness = first.get('completeness', 0)
            print(f"      Top result: Steps {steps}, Completeness {completeness*100:.0f}%")
    else:
        print(f"   ❌ SequentialQuery failed: {response.status_code}")
        print(f"      Response: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ SequentialQuery error: {e}")

# Test 5: Check if keyframes are accessible
print("\n5. Testing Keyframe Image Access...")
try:
    # Try to get a sample keyframe
    test_path = "/keyframes/part_1/keyframes/L09/V009/29567.jpg"
    response = requests.get(f"{BACKEND_URL}{test_path}", timeout=5)
    
    if response.status_code == 200:
        size_kb = len(response.content) / 1024
        print(f"   ✅ Keyframe accessible: {size_kb:.1f}KB")
    else:
        print(f"   ⚠️  Keyframe path may need adjustment: {response.status_code}")
        print(f"      Try: {test_path}")
except Exception as e:
    print(f"   ⚠️  Keyframe access: {e}")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

# Final recommendations
print("\n✅ If all tests passed:")
print("   1. Open browser: http://localhost:8007")
print("   2. Enable 'Multi-Step Query Mode' toggle")
print("   3. Enter 3-5 sequential queries")
print("   4. Click 'Search Sequential Query'")
print("   5. Results should appear in ~1-2 seconds")

print("\n📡 For remote access from Windows:")
server_ip = requests.get('http://ifconfig.me/ip', timeout=5).text.strip() if True else "YOUR_SERVER_IP"
print(f"   ssh -L 18007:localhost:8007 -L 18000:localhost:8000 ir@{server_ip}")
print("   Then open: http://localhost:18007")

print("\n" + "="*70)
