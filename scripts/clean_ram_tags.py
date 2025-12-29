#!/usr/bin/env python3
"""
RAM Tags Preprocessing Script
Filters generic tags, validates byte-length, outputs JSON for upload
"""

import csv
import json
from tqdm import tqdm

# Configuration
INPUT_CSV = '/home/ir/ram_results_final.csv'
OUTPUT_JSON = '/home/ir/ram_results_cleaned.json'
MAX_BYTES = 1950  # Leave buffer for VARCHAR(2000)

# Blacklist: generic/low-value tags
TAG_BLACKLIST = {
    'image', 'video', 'clip', 'scene', 'media', 'photo', 'picture',
    'person', 'object', 'generated', 'content', 'frame'
}

def clean_tags(tags_string: str) -> str:
    """
    Filter blacklisted tags and ensure byte-length compliance
    
    Args:
        tags_string: Pipe-separated tags "city | skyline | person"
    
    Returns:
        Cleaned pipe-separated string
    """
    if not tags_string or tags_string.strip() == '':
        return ''
    
    # Split by pipe, strip whitespace, filter blacklist
    tags = tags_string.split('|')
    filtered = [
        t.strip() 
        for t in tags 
        if t.strip() and t.strip().lower() not in TAG_BLACKLIST
    ]
    
    # Rejoin
    cleaned = ' | '.join(filtered)
    
    # Validate byte-length
    while len(cleaned.encode('utf-8')) > MAX_BYTES and filtered:
        # Remove last tag and rejoin
        filtered.pop()
        cleaned = ' | '.join(filtered)
    
    return cleaned


def main():
    print(f"Reading RAM CSV: {INPUT_CSV}")
    
    cleaned_data = []
    total_entries = 0
    filtered_count = 0
    truncated_count = 0
    
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Count total lines first for progress bar
        print("Counting entries...")
        temp_lines = sum(1 for _ in open(INPUT_CSV, 'r', encoding='utf-8')) - 1  # -1 for header
        
        # Reset and process
        f.seek(0)
        next(reader)  # Skip header
        
        for row in tqdm(reader, total=temp_lines, desc="Cleaning RAM tags", unit="frame"):
            keyframe_path = row['keyframe_path']
            original_tags = row['tags']
            
            # Remove .jpg extension for lookup consistency
            path_key = keyframe_path.replace('.jpg', '').replace('.JPG', '')
            
            # Clean tags
            original_count = len(original_tags.split('|'))
            cleaned_tags = clean_tags(original_tags)
            cleaned_count = len(cleaned_tags.split('|')) if cleaned_tags else 0
            
            # Track statistics
            total_entries += 1
            if cleaned_count < original_count:
                filtered_count += 1
            
            byte_len = len(cleaned_tags.encode('utf-8'))
            if byte_len > MAX_BYTES:
                print(f"Warning: {path_key} still exceeds limit: {byte_len} bytes")
                truncated_count += 1
            
            cleaned_data.append({
                'keyframe_path': path_key,
                'ram_tags': cleaned_tags,
                'original_tag_count': original_count,
                'cleaned_tag_count': cleaned_count
            })
    
    # Save to JSON
    print(f"\nSaving cleaned data to: {OUTPUT_JSON}")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
    
    # Statistics
    print("\n" + "="*60)
    print("RAM TAGS CLEANING REPORT")
    print("="*60)
    print(f"Total entries processed: {total_entries:,}")
    print(f"Entries with filtered tags: {filtered_count:,} ({100*filtered_count/total_entries:.1f}%)")
    print(f"Entries truncated (byte overflow): {truncated_count}")
    print(f"Output file: {OUTPUT_JSON}")
    print(f"Average tags per frame: {sum(e['cleaned_tag_count'] for e in cleaned_data)/len(cleaned_data):.1f}")
    print("="*60)
    
    # Sample output
    print("\nSample cleaned entries:")
    for entry in cleaned_data[:5]:
        print(f"  {entry['keyframe_path']}: {entry['cleaned_tag_count']} tags")
        print(f"    {entry['ram_tags'][:100]}{'...' if len(entry['ram_tags']) > 100 else ''}")


if __name__ == '__main__':
    main()
