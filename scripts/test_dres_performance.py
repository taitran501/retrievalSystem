#!/usr/bin/env python3
"""
DRES Performance Testing Script
================================
Tests TKIS (Text-based) and VKIS (Visual) queries to measure system performance
"""

import requests
import time
import json
from typing import List, Dict, Any

BACKEND_URL = "http://localhost:8000"

# Test queries simulating DRES competition scenarios
TKIS_QUERIES = [
    # Vietnamese news text queries
    "Chủ tịch Hồ Chí Minh",
    "Quốc hội Việt Nam",
    "NGUYỄN VĂN A",
    "Bản tin thời sự",
    "Sự kiện văn hóa",
    "Thành phố Hồ Chí Minh",
    "Người phát ngôn",
    "Hội nghị thượng đỉnh",
]

VKIS_QUERIES = [
    # Visual concept queries
    "person speaking at podium",
    "news anchor in studio",
    "crowd of people waving flags",
    "government building exterior",
    "city street with traffic",
    "people in formal suits",
    "cultural performance on stage",
    "press conference with journalists",
]

def test_query_performance(query: str, endpoint: str, query_type: str) -> Dict[str, Any]:
    """Test single query and measure performance"""
    
    start_time = time.time()
    
    try:
        if query_type == "TKIS":
            body = {
                "First_query": query,
                "Next_query": "",
                "top_k": 100
            }
        else:  # VKIS
            body = {
                "First_query": query,
                "top_k": 100
            }
        
        response = requests.post(
            f"{BACKEND_URL}{endpoint}",
            json=body,
            timeout=10
        )
        
        end_time = time.time()
        latency = (end_time - start_time) * 1000  # Convert to ms
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('kq', data.get('results', []))
            
            # Analyze result quality
            top_5_scores = [r.get('distance', 0) for r in results[:5]]
            avg_score = sum(top_5_scores) / len(top_5_scores) if top_5_scores else 0
            
            return {
                "success": True,
                "query": query,
                "latency_ms": latency,
                "num_results": len(results),
                "top_5_avg_score": avg_score,
                "top_1_score": top_5_scores[0] if top_5_scores else 0,
                "error": None
            }
        else:
            return {
                "success": False,
                "query": query,
                "latency_ms": latency,
                "error": f"HTTP {response.status_code}"
            }
            
    except Exception as e:
        end_time = time.time()
        latency = (end_time - start_time) * 1000
        return {
            "success": False,
            "query": query,
            "latency_ms": latency,
            "error": str(e)
        }

def run_performance_tests():
    """Run comprehensive performance tests"""
    
    print("=" * 70)
    print("🎯 DRES Performance Testing")
    print("=" * 70)
    print()
    
    # Test 1: TKIS (Textual Known Item Search)
    print("📝 Testing TKIS (Text-based queries)...")
    print("-" * 70)
    
    tkis_results = []
    for query in TKIS_QUERIES:
        result = test_query_performance(query, "/TextQuery", "TKIS")
        tkis_results.append(result)
        
        status = "✅" if result["success"] else "❌"
        print(f"{status} '{query[:40]}...' → {result['latency_ms']:.1f}ms, "
              f"{result.get('num_results', 0)} results, "
              f"score: {result.get('top_1_score', 0):.3f}")
    
    print()
    
    # Test 2: VKIS (Visual Known Item Search)
    print("🖼️  Testing VKIS (Visual concept queries)...")
    print("-" * 70)
    
    vkis_results = []
    for query in VKIS_QUERIES:
        result = test_query_performance(query, "/TextQuery", "VKIS")
        vkis_results.append(result)
        
        status = "✅" if result["success"] else "❌"
        print(f"{status} '{query[:40]}...' → {result['latency_ms']:.1f}ms, "
              f"{result.get('num_results', 0)} results, "
              f"score: {result.get('top_1_score', 0):.3f}")
    
    print()
    print("=" * 70)
    
    # Calculate statistics
    tkis_success = [r for r in tkis_results if r["success"]]
    vkis_success = [r for r in vkis_results if r["success"]]
    
    if tkis_success:
        tkis_avg_latency = sum(r["latency_ms"] for r in tkis_success) / len(tkis_success)
        tkis_avg_score = sum(r["top_1_score"] for r in tkis_success) / len(tkis_success)
        print(f"📊 TKIS Statistics:")
        print(f"   Success Rate: {len(tkis_success)}/{len(tkis_results)} ({100*len(tkis_success)/len(tkis_results):.0f}%)")
        print(f"   Avg Latency: {tkis_avg_latency:.1f}ms")
        print(f"   Avg Top-1 Score: {tkis_avg_score:.3f}")
        print()
    
    if vkis_success:
        vkis_avg_latency = sum(r["latency_ms"] for r in vkis_success) / len(vkis_success)
        vkis_avg_score = sum(r["top_1_score"] for r in vkis_success) / len(vkis_success)
        print(f"📊 VKIS Statistics:")
        print(f"   Success Rate: {len(vkis_success)}/{len(vkis_results)} ({100*len(vkis_success)/len(vkis_results):.0f}%)")
        print(f"   Avg Latency: {vkis_avg_latency:.1f}ms")
        print(f"   Avg Top-1 Score: {vkis_avg_score:.3f}")
        print()
    
    print("=" * 70)
    
    # Performance assessment
    print("🎯 Performance Assessment:")
    print()
    
    if tkis_success and tkis_avg_latency < 100:
        print("✅ TKIS latency < 100ms → Good for competition")
    elif tkis_success:
        print("⚠️  TKIS latency > 100ms → May have timeout issues")
    
    if vkis_success and vkis_avg_latency < 100:
        print("✅ VKIS latency < 100ms → Good for competition")
    elif vkis_success:
        print("⚠️  VKIS latency > 100ms → May have timeout issues")
    
    print()
    
    # Estimate DRES ranking based on scores
    if tkis_success:
        if tkis_avg_score > 0.75:
            print("🏆 TKIS Predicted Ranking: Top 25-35% (High scores)")
        elif tkis_avg_score > 0.65:
            print("🥉 TKIS Predicted Ranking: Top 35-45% (Good scores)")
        else:
            print("📊 TKIS Predicted Ranking: Top 45-55% (Average scores)")
    
    if vkis_success:
        if vkis_avg_score > 0.70:
            print("🏆 VKIS Predicted Ranking: Top 30-40% (High scores)")
        elif vkis_avg_score > 0.60:
            print("🥉 VKIS Predicted Ranking: Top 40-50% (Good scores)")
        else:
            print("📊 VKIS Predicted Ranking: Top 50-60% (Average scores)")
    
    print()
    print("=" * 70)
    print("✅ Performance testing complete!")
    print("=" * 70)
    
    # Save results
    with open('/home/ir/dres_test_results.json', 'w') as f:
        json.dump({
            'tkis_results': tkis_results,
            'vkis_results': vkis_results,
            'summary': {
                'tkis_avg_latency': tkis_avg_latency if tkis_success else None,
                'tkis_avg_score': tkis_avg_score if tkis_success else None,
                'vkis_avg_latency': vkis_avg_latency if vkis_success else None,
                'vkis_avg_score': vkis_avg_score if vkis_success else None,
            }
        }, f, indent=2)
    
    print("\n💾 Results saved to: /home/ir/dres_test_results.json")

if __name__ == "__main__":
    run_performance_tests()
