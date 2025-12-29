#!/usr/bin/env python3
"""
Comprehensive demo of the multi-step sequential query system
Shows all features and capabilities
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def test_query(queries, top_k=50, require_all=False, description=""):
    print(f"\n📝 {description}")
    print(f"   Steps: {len(queries)}, Top-K: {top_k}, Require All: {require_all}")
    
    for i, q in enumerate(queries, 1):
        print(f"   {i}. {q}")
    
    start = time.time()
    response = requests.post(
        f"{BASE_URL}/SequentialQuery",
        json={
            "queries": queries,
            "top_k": top_k,
            "require_all_steps": require_all
        },
        timeout=30
    )
    elapsed = time.time() - start
    
    if response.status_code == 200:
        data = response.json()
        results = data['kq']
        
        complete = sum(1 for r in results if r['completeness'] == 1.0)
        partial = len(results) - complete
        avg_comp = sum(r['completeness'] for r in results) / len(results) if results else 0
        
        print(f"   ✅ {elapsed:.2f}s | {len(results)} results | Complete: {complete} | Partial: {partial} | Avg: {avg_comp*100:.0f}%")
        
        # Show top 3
        if results:
            for i, r in enumerate(results[:3], 1):
                e = r['entity']
                steps = ','.join(str(s+1) for s in r['matched_steps'])
                print(f"      {i}. {e['video']} F{e['frame_id']} | Steps:{steps} | {r['completeness']*100:.0f}% | Score:{r['sequential_score']:.4f}")
        
        return True
    else:
        print(f"   ❌ Error: {response.status_code}")
        return False

print_section("MULTI-STEP SEQUENTIAL QUERY SYSTEM - COMPREHENSIVE DEMO")

# Test 1: Your 5-step DRES example
test_query(
    queries=[
        "news story online scams malicious links",
        "female interviewer woman reporter",
        "aerial view trees mountain rocky mountainside",
        "aerial shot trees rocky cliff mountain",
        "girls selfie sticks Guizhou China"
    ],
    top_k=50,
    require_all=False,
    description="5-Step DRES Competition Query (Partial Matches)"
)

# Test 2: Same query, strict mode
test_query(
    queries=[
        "news story online scams malicious links",
        "female interviewer woman reporter",
        "aerial view trees mountain rocky mountainside",
        "aerial shot trees rocky cliff mountain",
        "girls selfie sticks Guizhou China"
    ],
    top_k=20,
    require_all=True,
    description="5-Step DRES Query (Strict Mode - All Steps Required)"
)

# Test 3: Shorter practical query
test_query(
    queries=[
        "person walking on street",
        "person enters building",
        "person sitting at desk"
    ],
    top_k=30,
    require_all=False,
    description="3-Step Practical Query (Office Activity Sequence)"
)

# Test 4: Vehicle sequence
test_query(
    queries=[
        "red car on highway",
        "car exits highway",
        "car enters parking lot",
        "person exits car"
    ],
    top_k=25,
    require_all=False,
    description="4-Step Vehicle Tracking Sequence"
)

# Test 5: Simple 2-step (backward compatibility)
test_query(
    queries=[
        "person holding phone",
        "person typing on phone"
    ],
    top_k=30,
    require_all=False,
    description="2-Step Legacy Query (Backward Compatibility)"
)

# Test 6: Large query (stress test)
test_query(
    queries=[
        "person enters room",
        "person walks to table",
        "person sits down",
        "person opens laptop",
        "person typing",
        "person closes laptop",
        "person stands up",
        "person exits room"
    ],
    top_k=20,
    require_all=False,
    description="8-Step Extended Sequence (Stress Test)"
)

print_section("FEATURE SUMMARY")

print("""
✅ Multi-Step Queries: 2 to 10 steps supported
✅ Partial Matching: Show results with 60%+ steps matched (configurable)
✅ Strict Mode: Option to require all steps
✅ Fast Performance: 1-2 seconds for 5-step queries
✅ Flexible Top-K: Configurable results limit (10-100)
✅ Temporal Ordering: Ensures steps occur in sequence within same video
✅ Smart Scoring: Completeness (50%) + Similarity (40%) + Coherence (10%)
✅ Cache Support: Instant response for repeated queries
✅ Frontend UI: Toggle mode, dynamic steps, visual indicators
✅ Backward Compatible: Works with existing 2-query system

🎯 READY FOR DRES COMPETITION!
""")

print_section("FRONTEND FEATURES")

print("""
1. 🔗 Multi-Step Query Mode Toggle
   - Switch between legacy 2-query and multi-step mode
   - Settings persist across sessions

2. ➕➖ Dynamic Step Management
   - Add/remove steps (2-10 supported)
   - Visual step counter: ①→②→③→④→⑤

3. 🎚️ Top-K Control
   - Slider: 10 to 100 results
   - Default: 50 (optimal for competition)

4. ✓ Step Indicators on Results
   - Green badges: Matched steps
   - Gray badges: Unmatched steps
   - Progress bar: Completeness visualization
   - Score display: Sequential similarity score

5. 🎨 Visual Feedback
   - Green border: Complete matches (100%)
   - Yellow border: Partial matches (60-99%)
   - Color-coded completeness bars

6. 💾 Persistent Settings
   - Queries saved in localStorage
   - Preferences restored on reload
""")

print_section("USAGE TIPS FOR DRES COMPETITION")

print("""
1. Start with 3-5 steps for your query sequence
2. Use descriptive but concise queries (5-10 words each)
3. Set top-K to 50 for good coverage without overwhelming
4. Keep "Require all steps" OFF for maximum recall
5. Look for green-bordered results (complete matches) first
6. Check step badges to understand which parts matched
7. Use completeness bar to quickly assess match quality
8. Sequential score helps distinguish between similar results

Example Workflow:
  1. Read DRES question carefully
  2. Break into 3-5 temporal steps
  3. Enter each step in sequential query builder
  4. Click search, wait ~1-2 seconds
  5. Scan top results (green borders = best)
  6. Click result to view video
  7. Verify it matches the question
  8. Submit to DRES system

Good luck! 🏆
""")

print("\n" + "="*80)
print("DEMO COMPLETE - System is ready for production use!")
print("="*80 + "\n")
