# 🚀 Quick Reference - Image Upload Feature

## What's New

### ✨ Image Upload Search
Search by visual similarity using CLIP image encoder instead of text queries.

### 🎯 Improved Result Diversity
- **100 frames gap** (4 seconds) between results
- **Max 3 frames** per video
- **75 total results** (optimized for performance)

### 💡 Mode Tooltips
Hover over "Temporal" and "Expansion" buttons to see explanations.

---

## How to Use

### 📁 Upload Image
1. Click the image drop area (camera icon)
2. Select image from your computer
3. View preview and wait for results

### 📋 Paste from Clipboard
1. Copy any image (screenshot, browser image, etc.)
2. Press **Ctrl+V** anywhere in the interface
3. Results appear automatically

### 🎯 Drag & Drop
1. Drag image file from file explorer
2. Drop onto the image area
3. Search executes automatically

---

## Technical Details

### Backend Endpoint
```bash
POST http://localhost:8000/ImageQuery
Content-Type: multipart/form-data

# Test with curl
curl -X POST http://localhost:8000/ImageQuery -F "file=@image.jpg"
```

### Response Format
```json
{
  "query_type": "image",
  "total_results": 75,
  "kq": [
    {
      "entity": {
        "keyframe_path": "L06/V002/27588.jpg",
        "video_path": "L06_V002.mp4",
        "time": "00:18:23.520",
        "time_seconds": 1103.52,
        "frame_id": 27588,
        "video": "L06_V002"
      },
      "distance": 0.85
    }
  ]
}
```

### Configuration
```json
{
  "diversity_min_gap_frames": 100,
  "diversity_max_per_video": 3,
  "diversity_max_results": 75,
  "use_ocr_search": true,
  "use_ram_tags": true
}
```

---

## Troubleshooting

### Backend not responding
```bash
cd /home/ir/retrievalBaseline/backend
pkill -f "python.*main.py"
nohup python3 main.py > backend.log 2>&1 &
tail -f backend.log
```

### Frontend changes not visible
```bash
# Clear browser cache (Ctrl+Shift+R)
# Or redeploy
cd /home/ir/retrievalBaseline/frontend
sudo cp -r src/* /var/www/retrieval-frontend/src/
sudo cp index.html /var/www/retrieval-frontend/
```

### Image upload fails
1. Check file size (very large images may timeout)
2. Check image format (must be valid image file)
3. Check backend logs: `tail -f backend/backend.log`
4. Check browser console: F12 → Console tab

### Results show duplicates
- Check diversity_min_gap_frames in config.json
- Increase to 150 for 6-second gaps
- Restart backend after config changes

---

## Testing Commands

```bash
# 1. Create test image
python3 -c "from PIL import Image; Image.new('RGB', (224,224), 'blue').save('/tmp/test.jpg')"

# 2. Test API
curl -X POST http://localhost:8000/ImageQuery -F "file=@/tmp/test.jpg" | jq .total_results

# 3. Check backend health
curl http://localhost:8000/health | jq .

# 4. View recent logs
tail -30 /home/ir/retrievalBaseline/backend/backend.log | grep "Image query"
```

---

## Performance Tips

### For faster searches:
- Reduce `diversity_max_results` (e.g., 50)
- Use smaller images (224x224 is ideal)
- Close other browser tabs

### For better quality:
- Use high-quality images
- Crop images to focus on main subject
- Use images similar to video keyframes (not illustrations)

---

## Access Points

- **Frontend**: http://localhost:8007 or http://192.168.20.156:18007
- **Backend API**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **Config**: /home/ir/retrievalBaseline/backend/config.json

---

## Files Reference

| File | Purpose |
|------|---------|
| `backend/main.py` | Backend API with `/ImageQuery` endpoint |
| `frontend/src/scripts/image_search.js` | Image upload logic |
| `frontend/src/styles/left_panel.css` | Image area styling |
| `frontend/index.html` | UI with image drop areas |
| `backend/config.json` | Diversity and search settings |

---

## Support

For issues or questions:
1. Check logs: `backend/backend.log`
2. Check browser console: F12
3. Verify config: `cat backend/config.json`
4. Test API directly: `curl localhost:8000/health`

