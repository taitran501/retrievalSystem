#!/bin/bash

echo "========================================="
echo "FULL SYSTEM TEST"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Backend Health
echo "1. Testing Backend Health..."
HEALTH=$(curl -s http://localhost:8000/health)
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${RED}✗ Backend not responding${NC}"
    exit 1
fi
echo ""

# Test 2: Frontend Running
echo "2. Testing Frontend..."
FRONTEND=$(curl -s http://localhost:3000 | grep -o "frontend-v2")
if [ ! -z "$FRONTEND" ]; then
    echo -e "${GREEN}✓ Frontend is running${NC}"
else
    echo -e "${RED}✗ Frontend not responding${NC}"
fi
echo ""

# Test 3: Standard Text Search
echo "3. Testing Standard Text Search..."
TEXT_RESULT=$(curl -s -X POST http://localhost:8000/TextQuery \
    -H "Content-Type: application/json" \
    -d '{"First_query":"person talking","top_k":5}')
TEXT_COUNT=$(echo "$TEXT_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['total_results'])" 2>/dev/null)
if [ "$TEXT_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Text search works: $TEXT_COUNT results${NC}"
else
    echo -e "${RED}✗ Text search failed${NC}"
fi
echo ""

# Test 4: Visual Concept Search
echo "4. Testing Visual Concept Search..."
VISUAL_RESULT=$(curl -s -X POST http://localhost:8000/VisualConceptSearch \
    -H "Content-Type: application/json" \
    -d '{"query":"car","top_k":5}')
VISUAL_COUNT=$(echo "$VISUAL_RESULT" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['results']))" 2>/dev/null)
if [ "$VISUAL_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Visual search works: $VISUAL_COUNT results${NC}"
else
    echo -e "${YELLOW}⚠ Visual search returned 0 results (may need Google API)${NC}"
fi
echo ""

# Test 5: Temporal/Sequential Query
echo "5. Testing Temporal Query..."
TEMPORAL_RESULT=$(curl -s -X POST http://localhost:8000/SequentialQuery \
    -H "Content-Type: application/json" \
    -d '{"queries":["person speaking","audience clapping"],"top_k":5}')
TEMPORAL_COUNT=$(echo "$TEMPORAL_RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('total_results', len(d.get('results', []))))" 2>/dev/null)
if [ "$TEMPORAL_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Temporal search works: $TEMPORAL_COUNT results${NC}"
else
    echo -e "${RED}✗ Temporal search failed${NC}"
fi
echo ""

# Test 6: OCR Search
echo "6. Testing OCR Search..."
OCR_RESULT=$(curl -s -X POST http://localhost:8000/TextQuery \
    -H "Content-Type: application/json" \
    -d '{"First_query":"","ocr_text":"TIẾP THEO","top_k":5}')
OCR_COUNT=$(echo "$OCR_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['total_results'])" 2>/dev/null)
OCR_SCORE=$(echo "$OCR_RESULT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['kq'][0].get('ocr_score', 0) if d['kq'] else 0)" 2>/dev/null)
if [ "$OCR_COUNT" -gt 0 ] && (( $(echo "$OCR_SCORE > 0" | bc -l) )); then
    echo -e "${GREEN}✓ OCR search works: $OCR_COUNT results, top score=$OCR_SCORE${NC}"
else
    echo -e "${YELLOW}⚠ OCR search returned results but low matching scores${NC}"
fi
echo ""

# Test 7: Neighbor Frames
echo "7. Testing Neighbor Frames..."
NEIGHBOR_RESULT=$(curl -s -X POST http://localhost:8000/get_neighbor_frames \
    -H "Content-Type: application/json" \
    -d '{"video":"V026","frame_id":1894,"count":3}')
NEIGHBOR_COUNT=$(echo "$NEIGHBOR_RESULT" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['neighbors']))" 2>/dev/null)
if [ "$NEIGHBOR_COUNT" -eq 6 ]; then
    echo -e "${GREEN}✓ Neighbor frames works: $NEIGHBOR_COUNT frames (3 before + 3 after)${NC}"
else
    echo -e "${RED}✗ Neighbor frames failed: got $NEIGHBOR_COUNT frames instead of 6${NC}"
fi
echo ""

# Test 8: Video and Keyframe Paths
echo "8. Testing Video Access..."
VIDEO_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/videos/batch1/L01_V001.mp4)
if [ "$VIDEO_STATUS" -eq 200 ]; then
    echo -e "${GREEN}✓ Video files accessible${NC}"
else
    echo -e "${RED}✗ Video files not accessible (status: $VIDEO_STATUS)${NC}"
fi

KEYFRAME_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/keyframes/L01/V001/100.jpg)
if [ "$KEYFRAME_STATUS" -eq 200 ]; then
    echo -e "${GREEN}✓ Keyframe files accessible${NC}"
else
    echo -e "${YELLOW}⚠ Keyframe access issue (status: $KEYFRAME_STATUS)${NC}"
fi
echo ""

echo "========================================="
echo "TEST SUMMARY"
echo "========================================="
echo "All core features tested."
echo ""
echo "If you see mostly green checkmarks, the system is working!"
echo "If you see red crosses, check the specific failed tests above."
echo ""
