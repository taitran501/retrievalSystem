# Feature Implementation Plan

## 1. Image Upload + Clipboard Paste Search ✨

### Current State:
- Image upload button exists in UI but not functional
- No clipboard paste support
- Only text-based CLIP search implemented

### Implementation Plan:

#### Frontend Changes:
1. **Enable Image Upload Button**
   - File: `frontend/index.html` (already has image-drop-area)
   - Activate file input: `<input type="file" accept="image/*" id="Image-Query-1">`
   - Add event listener for file selection
   - Preview uploaded image in drop area

2. **Add Clipboard Paste Support**
   - Listen for `paste` event on document/search area
   - Extract image from `clipboard.items`
   - Convert to base64 or File object
   - Show preview with "Pasted from clipboard" label

3. **Image Preview UI**
   ```javascript
   // Show preview with remove button
   <div class="preview-upload-container">
     <img src="base64_or_url" />
     <button class="remove-image">✕</button>
   </div>
   ```

#### Backend Changes:
1. **New Endpoint: `/ImageQuery`**
   ```python
   @app.post("/ImageQuery")
   async def image_query_endpoint(file: UploadFile):
       # Decode image
       image = Image.open(BytesIO(await file.read()))
       
       # Encode with CLIP image encoder (not text encoder!)
       image_vector = encode_clip_image(image)
       
       # Search Milvus
       results = await query_milvus(image_vector, limit=100)
       
       return {"kq": results}
   ```

2. **Add CLIP Image Encoding**
   ```python
   def encode_clip_image(self, image: PIL.Image) -> torch.Tensor:
       # Preprocess image (resize, normalize)
       image_input = self.clip_preprocess(image).unsqueeze(0)
       
       # Encode with CLIP vision encoder
       with torch.no_grad():
           image_features = self.clip_model.encode_image(image_input)
           image_features = F.normalize(image_features, dim=-1)
       
       return image_features
   ```

#### Frontend JS Flow:
```javascript
// File upload
document.getElementById('Image-Query-1').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  
  // Show preview
  showImagePreview(file);
  
  // Upload to backend
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('/ImageQuery', {
    method: 'POST',
    body: formData
  });
  
  const data = await response.json();
  updateUIWithSearchResults(data.kq);
});

// Clipboard paste
document.addEventListener('paste', async (e) => {
  const items = e.clipboardData.items;
  for (let item of items) {
    if (item.type.indexOf('image') === 0) {
      const blob = item.getAsFile();
      // Same upload flow as file
      handleImageUpload(blob);
    }
  }
});
```

### Testing:
1. Upload image from file system → search by visual similarity
2. Copy image from browser/screenshot → Ctrl+V paste → search
3. Verify results match visual content (not text query)

---

## 2. Video Frame Seek Fix 🎯

### Issue:
- Click on result → video opens but doesn't seek to exact timestamp
- `time_seconds` field was NULL in API responses

### Root Cause:
- `hybrid_search_adaptive()` returns raw Milvus results
- Missing `_format_results_for_frontend()` call
- Frontend receives results without `time_seconds` field

### Solution Implemented:
- Added `_format_results_for_frontend()` helper function
- Converts time string "00:09:16.960" → 556.96 seconds
- Adds `video_path` field (L01_V001.mp4 format)
- Applied to hybrid search results

### Verification:
```bash
# Test API response
curl -s -X POST http://localhost:8000/TextQuery \
  -H "Content-Type: application/json" \
  -d '{"First_query": "car"}' | jq '.kq[0].entity.time_seconds'
# Should return: 556.96 (not null)
```

### Frontend Logic:
```javascript
// show_video.js:178-192
const timeSeconds = data.kq[img.id - 1].entity.time_seconds || 0;

if (player.video.readyState >= 1) {
  player.video.currentTime = timeSeconds; // Immediate seek
} else {
  player.video.addEventListener('loadedmetadata', () => {
    player.video.currentTime = timeSeconds; // Wait for load
  }, { once: true });
}
```

---

## 3. Temporal vs Expansion Modes 🔄

### UI Location:
- Two buttons under each search scene:
  - **Temporal** (active by default)
  - **Expansion** (alternative mode)

### Mode Explanations:

#### **TEMPORAL Mode** (Default)
**Purpose**: Sequential event search - find frames that appear **in order** over time

**Use Cases**:
- Multi-step events: "person walks → opens door → enters building"
- Story progression: "sunrise → people working → sunset"
- Action sequences: "car starts → drives → parks"

**How It Works**:
1. User enters Scene 1 query: "person walking"
2. User enters Scene 2 query: "person opening door"
3. Backend searches: Find frames where Scene 1 → Scene 2 appears sequentially
4. **Temporal constraint**: Scene 2 frames must be **after** Scene 1 frames (later in video timeline)
5. Scoring: Considers temporal proximity and semantic match

**Backend Logic**:
```python
# Scene 1 results
first_results = search(first_query)  # e.g., frame 100-200

# Scene 2 results (filtered to be AFTER Scene 1)
second_results = search(second_query)
second_results = [r for r in second_results if r.frame_id > max(first_results.frame_id)]

# Score based on temporal gap
for r1, r2 in zip(first_results, second_results):
    gap = r2.frame_id - r1.frame_id
    temporal_bonus = calculate_temporal_bonus(gap)  # Closer = higher score
    combined_score = similarity + temporal_bonus
```

**When to Use**:
- ✅ Events that happen in sequence
- ✅ Before/after scenarios
- ✅ Narrative flow searches
- ❌ Simultaneous events
- ❌ Searching for same object across video

---

#### **EXPANSION Mode**
**Purpose**: Query refinement - broaden or narrow search by adding **more context**

**Use Cases**:
- Refine results: Initial query "car" → expand with "red car in parking lot"
- Add context: "interview" → expand with "interview at news desk with city view"
- Combine concepts: "food" → expand with "food on table at restaurant"

**How It Works**:
1. User enters Scene 1 query: "car"
2. Backend performs initial search
3. User adds Scene 2 query: "red" (expansion)
4. Backend **re-ranks** Scene 1 results based on **both** queries
5. **No temporal constraint**: Finds frames matching BOTH concepts (can be same frame)
6. Scoring: Weighted combination of both semantic matches

**Backend Logic**:
```python
# Initial search
first_results = search(first_query)  # e.g., all "car" frames

# Expansion: combine both query embeddings
combined_embedding = (0.6 * first_embedding + 0.4 * second_embedding)

# Re-rank by combined similarity
for result in first_results:
    score = cosine_similarity(result.vector, combined_embedding)
    result.combined_score = score

# Sort by combined score
return sorted(first_results, key=lambda x: x.combined_score, reverse=True)
```

**When to Use**:
- ✅ Refining broad searches
- ✅ Adding attributes (color, location, context)
- ✅ Combining multiple concepts
- ✅ When Scene 1 + Scene 2 describe **same frame/moment**
- ❌ Sequential events
- ❌ Timeline-based searches

---

### Comparison Table:

| Aspect | Temporal Mode | Expansion Mode |
|--------|---------------|----------------|
| **Purpose** | Sequential event search | Query refinement |
| **Temporal Order** | Scene 2 AFTER Scene 1 | No order constraint |
| **Scoring** | Temporal proximity + similarity | Combined semantic similarity |
| **Frame Selection** | Different frames (scene 1 → scene 2) | Can be same frame |
| **Example Query** | "person stands" → "person sits" | "car" + "red" |
| **Use Case** | Story progression | Attribute refinement |

---

### Current Backend Implementation:

**File**: `backend/main.py`

#### Temporal Mode:
```python
async def process_temporal_query(first_query: str, second_query: str):
    # Search first query
    first_results = await query_milvus(first_query, limit=3000)
    
    if not second_query:
        return first_results  # Single query mode
    
    # Search second query
    second_results = await query_milvus(second_query, limit=3000)
    
    # Apply temporal constraint (Scene 2 after Scene 1)
    # + calculate temporal bonuses for closer matches
    # + combine scores with weighting
    
    return temporally_ranked_results
```

#### Expansion Mode:
```python
async def process_expansion_query(first_query: str, second_query: str):
    # Encode both queries
    first_embedding = encode_clip_text(first_query)
    second_embedding = encode_clip_text(second_query)
    
    # Combine embeddings (weighted average)
    combined_embedding = 0.6 * first_embedding + 0.4 * second_embedding
    
    # Single search with combined embedding
    results = await query_milvus(combined_embedding, limit=100)
    
    return results
```

---

### Recommendations:

1. **Default to Temporal**: Most AIC competition queries are sequential events
2. **Use Expansion for**:
   - Initial broad search needs refinement
   - Adding visual attributes (colors, objects)
   - Combining multiple concepts in same scene

3. **Add UI Tooltip**: Explain modes on hover
   ```html
   <button class="temporal-search active" title="Sequential events: Scene 2 happens AFTER Scene 1">Temporal</button>
   <button class="query-expansion" title="Refine search: Combine both queries for same scene">Expansion</button>
   ```

4. **Consider Hybrid Mode**: Some queries benefit from both
   - Temporal constraint for sequence
   - Expansion for attribute matching

---

## Priority Implementation:

### Phase 1 (Immediate): ✅
- [x] Fix video frame seek (`time_seconds` field)
- [x] RAM tags display in UI
- [x] Hybrid search scoring

### Phase 2 (Next):
- [ ] Add mode tooltips/help text (30 mins)
- [ ] Test temporal mode with sequential queries (1 hour)
- [ ] Document mode differences for users (30 mins)

### Phase 3 (High Priority):
- [ ] Implement image upload endpoint (2 hours)
- [ ] Add clipboard paste support (1 hour)
- [ ] Test image-based search (1 hour)

### Phase 4 (Nice to Have):
- [ ] Image + text hybrid search (visual + textual query)
- [ ] Drag-and-drop image upload
- [ ] Image crop/edit before search
- [ ] Search similar frames (right-click on result)
