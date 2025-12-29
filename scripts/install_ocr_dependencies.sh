#!/bin/bash
# Install OCR dependencies for EasyOCR

echo "=========================================="
echo "Installing OCR Dependencies (EasyOCR)"
echo "=========================================="

# Check Python version
python3 --version

# Install EasyOCR and dependencies
echo ""
echo "📦 Installing EasyOCR..."
pip install easyocr torch torchvision

# Verify installation
echo ""
echo "✅ Verifying installation..."
python3 -c "import easyocr; print('EasyOCR installed successfully')"

# Pre-download models
echo ""
echo "📥 Pre-downloading OCR models (English)..."
python3 << 'EOF'
import easyocr
print("Initializing OCR (this will download models)...")
reader = easyocr.Reader(['en'], gpu=False)
print("✅ Models downloaded and cached")
EOF

echo ""
echo "=========================================="
echo "✅ Installation Complete!"
echo "=========================================="
echo ""
echo "Test OCR with:"
echo "  python3 /home/ir/retrievalBaseline/backend/ocr_processor.py --levels L01"
echo ""
echo "Full processing (all levels):"
echo "  python3 /home/ir/retrievalBaseline/backend/ocr_processor.py"
echo ""
