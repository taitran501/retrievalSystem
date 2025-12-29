# 🎯 Quick Action Plan - Priority Improvements

**Generated:** December 15, 2025

---

## ⚡ Immediate Actions (Do Now - 2 Hours)

### 1. Enable GPU Acceleration 🚀
**Impact:** 5-10x faster queries (1.28s → 150ms)

```bash
# Check GPU availability
nvidia-smi
python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# Update config
cd /home/ir/retrievalBaseline/backend
nano config.json
```

**Change:**
```json
{
  "device": "cuda",  // Change from "cpu"
}
```

**Restart:**
```bash
pkill -f "python.*main.py"
nohup python3 main.py > backend.log 2>&1 &
```

---

### 2. Fix Cache Key Bug 🐛
**Problem:** Cache ignores `require_all_steps` and `time_gap_constraints`

**File:** [main.py](retrievalBaseline/backend/main.py) line ~848

**Change:**
```python
# OLD
cache_key = hashlib.md5("|".join(queries).encode()).hexdigest()

# NEW
cache_key = hashlib.md5(
    "|".join(queries).encode() +
    str(require_all_steps).encode() +
    str(time_gap_constraints).encode()
).hexdigest()
```

---

### 3. Verify Collection Consistency ✅
```bash
python3 /home/ir/retrievalBaseline/check_collection.py

# Check model matches
grep "clip_model_name" /home/ir/retrievalBaseline/backend/config.json
```

**Expected:** `ViT-L-14` (768 dimensions)

---

## 📊 This Week (High-Value - 1-2 Days)

### 4. Improve OCR Matching
**Impact:** +20-30% accuracy for text queries

```bash
cd /home/ir/retrievalBaseline/backend
pip install underthesea fuzzywuzzy python-Levenshtein
```

**Add fuzzy matching to:** [ocr_processor.py](retrievalBaseline/backend/ocr_processor.py)

---

### 5. Add Virtual Scrolling
**Impact:** 2-3x faster UI for large result sets

**File:** Create `frontend/src/scripts/virtual_scroll.js`

**Benefit:** Render only visible items (20 vs 1000+)

---

### 6. Tune Diversity Filter
**Current:**
```json
{
  "diversity_min_gap_frames": 100,  // 4 seconds
  "diversity_max_per_video": 3,
  "diversity_max_results": 75
}
```

**Recommended:**
```json
{
  "diversity_min_gap_frames": 75,   // 3 seconds - faster changes
  "diversity_max_per_video": 5,     // More coverage per video
  "diversity_max_results": 100      // Competition may need more
}
```

---

## 🔮 Next Month (Advanced - 1-2 Weeks)

### 7. Query Expansion System
**Impact:** +15-20% recall

- Synonym dictionary (car → vehicle, automobile)
- Vietnamese word segmentation (`underthesea`)
- Multi-query search with result merging

---

### 8. Multi-Model Ensemble
**Impact:** +10-15% top-K accuracy

- CLIP ViT-L-14 (current)
- BLIP-2 reranking
- Ensemble scoring (0.7 CLIP + 0.3 BLIP)

---

### 9. Redis Caching Layer
**Impact:** Better cache persistence

```bash
docker run -d --name redis -p 6379:6379 redis:alpine
pip install redis
```

**Multi-tier cache:**
- L1: In-memory (5 min)
- L2: Redis (1 hour)
- L3: Milvus (source)

---

## 📈 Monitoring Setup (2-3 Days)

### 10. Add Prometheus Metrics
```bash
pip install prometheus-client
```

**Track:**
- Query latency (P50, P95, P99)
- Cache hit rate
- GPU utilization
- Error rates

### 11. Grafana Dashboard
```bash
docker run -d -p 3000:3000 grafana/grafana
```

**Panels:**
- Query performance
- Resource usage
- Search quality metrics

---

## 🔒 Security Hardening (1 Day)

### 12. Add Authentication
```python
# Add API key to headers
X-API-Key: your-secret-key
```

### 13. Rate Limiting
```bash
pip install slowapi
```

```python
@limiter.limit("10/minute")
async def text_query_endpoint(request: Request):
```

### 14. Restrict CORS
```python
allow_origins=["http://localhost:8007"],  # Remove "*"
```

---

## 🧪 Testing (Ongoing)

### 15. Add Unit Tests
```bash
pip install pytest pytest-asyncio
pytest tests/
```

### 16. Load Testing
```bash
pip install locust
locust -f tests/load_test.py --users 50
```

---

## 📊 Expected Results

| Improvement | Time | Impact | Effort |
|-------------|------|--------|--------|
| GPU Enable | 30 min | 🔥🔥🔥🔥🔥 (5-10x) | ⚡ Easy |
| Fix Cache Bug | 10 min | 🔥🔥🔥 (Correctness) | ⚡ Easy |
| OCR Fuzzy Match | 4 hours | 🔥🔥🔥🔥 (+20-30%) | 🔨 Medium |
| Virtual Scroll | 3 hours | 🔥🔥🔥 (2-3x UI) | 🔨 Medium |
| Query Expansion | 2 days | 🔥🔥🔥🔥 (+15-20%) | 🔨 Medium |
| Ensemble Rerank | 1 week | 🔥🔥🔥 (+10-15%) | 🏗️ Hard |
| Redis Cache | 1 day | 🔥🔥 (Persistence) | 🔨 Medium |
| Monitoring | 2 days | 🔥🔥 (Observability) | 🔨 Medium |

---

## 🎯 Success Metrics

### Before Improvements:
- ❌ CPU-only processing: ~1.28s for 5-step query
- ❌ Cache misses on parameter changes
- ❌ OCR: Exact match only
- ❌ UI: Renders all 1000+ results

### After Improvements:
- ✅ GPU processing: ~150-200ms for 5-step query (**8x faster**)
- ✅ Cache works correctly for all scenarios
- ✅ OCR: Fuzzy matching + Vietnamese segmentation (**+25% accuracy**)
- ✅ UI: Virtual scroll, renders 20 items (**50x faster rendering**)

---

## 📝 Next Steps

1. **Today:** Enable GPU + fix cache bug (30 minutes)
2. **This week:** OCR improvements + virtual scroll (1 day)
3. **Next week:** Query expansion + ensemble reranking (1 week)
4. **Next month:** Monitoring + security hardening (1 week)

---

## 🔗 Related Documents

- [SYSTEM_EVALUATION_REPORT.md](SYSTEM_EVALUATION_REPORT.md) - Full analysis
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Current features
- [retrievalBaseline/README.md](retrievalBaseline/README.md) - Setup guide

---

**Questions?** Check logs:
```bash
tail -f /home/ir/retrievalBaseline/backend/backend.log
```

**Need help?** Review documentation or create GitHub issues.
