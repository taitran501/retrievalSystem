#!/usr/bin/env python3
"""
Merge OCR Data Files
Converts CSV to JSON and merges all OCR results into single file
"""

import json
import csv
from pathlib import Path

def csv_to_json(csv_path: Path) -> list:
    """Convert CSV to JSON format"""
    results = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append({
                'keyframe_path': row['keyframe_path'],
                'ocr_text': row['ocr_text']
            })
    return results

def merge_ocr_files(p1_json: Path, p1_csv: Path, p2_csv: Path, output: Path):
    """Merge all OCR files into single JSON"""
    
    print("="*70)
    print("OCR Data Merger")
    print("="*70)
    
    # Load p1 JSON (L01-L06)
    print(f"\n📁 Loading {p1_json}...")
    with open(p1_json, 'r', encoding='utf-8') as f:
        p1_json_data = json.load(f)
    print(f"   ✅ Loaded {len(p1_json_data):,} entries from JSON")
    
    # Load p1 CSV (L01-L06 - might be duplicate or different data)
    print(f"\n📁 Loading {p1_csv}...")
    p1_csv_data = csv_to_json(p1_csv)
    print(f"   ✅ Loaded {len(p1_csv_data):,} entries from CSV")
    
    # Load p2 CSV (L07-L12)
    print(f"\n📁 Loading {p2_csv}...")
    p2_csv_data = csv_to_json(p2_csv)
    print(f"   ✅ Loaded {len(p2_csv_data):,} entries from CSV")
    
    # Check for duplicates between p1_json and p1_csv
    p1_json_paths = {entry['keyframe_path'] for entry in p1_json_data}
    p1_csv_paths = {entry['keyframe_path'] for entry in p1_csv_data}
    overlap = p1_json_paths & p1_csv_paths
    
    if overlap:
        print(f"\n⚠️  Found {len(overlap):,} duplicate paths between p1 JSON and CSV")
        print(f"   Using JSON version (discarding CSV duplicates)")
        # Remove duplicates from CSV data
        p1_csv_data = [e for e in p1_csv_data if e['keyframe_path'] not in p1_json_paths]
    
    # Merge all data
    print(f"\n🔀 Merging data...")
    all_data = p1_json_data + p1_csv_data + p2_csv_data
    
    # Create lookup by keyframe_path for deduplication
    merged = {}
    for entry in all_data:
        path = entry['keyframe_path']
        # Normalize path format (remove escapes if present)
        path = path.replace('\\/', '/')
        merged[path] = entry['ocr_text']
    
    # Convert back to list format
    final_data = [
        {'keyframe_path': k, 'ocr_text': v}
        for k, v in merged.items()
    ]
    
    # Sort by keyframe_path for easier lookup
    final_data.sort(key=lambda x: x['keyframe_path'])
    
    # Statistics by level
    print(f"\n📊 Statistics:")
    print(f"   Total unique entries: {len(final_data):,}")
    
    level_counts = {}
    for entry in final_data:
        level = entry['keyframe_path'].split('/')[0]
        level_counts[level] = level_counts.get(level, 0) + 1
    
    print(f"\n   Breakdown by level:")
    for level in sorted(level_counts.keys()):
        print(f"      {level}: {level_counts[level]:,} frames")
    
    # Save merged data
    print(f"\n💾 Saving to {output}...")
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    print(f"   ✅ Saved {len(final_data):,} entries")
    print(f"\n" + "="*70)
    print("✅ OCR DATA MERGE COMPLETE")
    print("="*70)
    
    return len(final_data)

if __name__ == "__main__":
    base_dir = Path("/home/ir")
    
    p1_json = base_dir / "ocr_results_p1.json"
    p1_csv = base_dir / "ocr_results_p1.csv"
    p2_csv = base_dir / "ocr_results_p2.csv"
    output = base_dir / "ocr_results_all.json"
    
    # Verify files exist
    for f in [p1_json, p1_csv, p2_csv]:
        if not f.exists():
            print(f"❌ Error: {f} not found!")
            exit(1)
    
    merge_ocr_files(p1_json, p1_csv, p2_csv, output)
