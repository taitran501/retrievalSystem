#!/bin/bash
# Sync frontend files to nginx directory
# Usage: bash sync_frontend.sh

echo "=========================================="
echo "  Syncing Frontend Files"
echo "=========================================="

SOURCE="/home/ir/retrievalBaseline/frontend"
DEST="/var/www/retrieval-frontend"

if [ ! -d "$SOURCE" ]; then
    echo "❌ Source directory not found: $SOURCE"
    exit 1
fi

echo ""
echo "Copying files from:"
echo "  $SOURCE"
echo "to:"
echo "  $DEST"
echo ""

# Copy all files
sudo cp -r $SOURCE/* $DEST/

# Set proper permissions
sudo chown -R www-data:www-data $DEST/
sudo chmod -R 755 $DEST/

echo ""
echo "✅ Files synchronized successfully!"
echo ""
echo "Verifying new files..."

if [ -f "$DEST/src/scripts/sequential_query_builder.js" ]; then
    echo "  ✅ sequential_query_builder.js"
else
    echo "  ❌ sequential_query_builder.js NOT FOUND"
fi

if [ -f "$DEST/src/styles/sequential_query.css" ]; then
    echo "  ✅ sequential_query.css"
else
    echo "  ❌ sequential_query.css NOT FOUND"
fi

echo ""
echo "🔄 Reloading nginx..."
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "=========================================="
echo "✅ DONE!"
echo "=========================================="
echo ""
echo "🔄 Clear browser cache:"
echo "   Ctrl + Shift + R (Windows)"
echo "   Cmd + Shift + R (Mac)"
echo ""
echo "Then refresh: http://localhost:18007"
echo ""
