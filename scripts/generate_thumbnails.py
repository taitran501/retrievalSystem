import os
import glob
from PIL import Image
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

# Configuration
BASE_DIR = "c:/Users/trant/Documents/retrieval_system/retrievalSystem/data"
KEYFRAMES_DIR = os.path.join(BASE_DIR, "keyframes")
THUMBNAILS_DIR = os.path.join(BASE_DIR, "thumbnails")
THUMB_SIZE = (224, 126)  # Optimized: smaller but enough for CLIP and preview
MAX_WORKERS = 12 # Speed up on modern CPUs

def generate_thumb(relative_path):
    """Generate a single thumbnail"""
    src_path = os.path.join(KEYFRAMES_DIR, relative_path)
    dst_path = os.path.join(THUMBNAILS_DIR, relative_path)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    
    try:
        with Image.open(src_path) as img:
            img.thumbnail(THUMB_SIZE)
            # Use lower quality (75) to significantly reduce disk usage
            img.save(dst_path, "JPEG", quality=75, optimize=True)
        return True
    except Exception as e:
        print(f"Error processing {src_path}: {e}")
        return False

def main():
    print(f"--- THUMBNAIL GENERATOR ---")
    print(f"Source: {KEYFRAMES_DIR}")
    print(f"Target: {THUMBNAILS_DIR}")
    
    # Collect all jpg files relative to KEYFRAMES_DIR
    print("Scanning for keyframes...")
    all_files = []
    # Using L*/V*/*.jpg structure
    for l_dir in os.listdir(KEYFRAMES_DIR):
        if not l_dir.startswith('L'): continue
        l_path = os.path.join(KEYFRAMES_DIR, l_dir)
        for v_dir in os.listdir(l_path):
            if not v_dir.startswith('V'): continue
            v_full_path = os.path.join(l_path, v_dir)
            files = glob.glob(os.path.join(v_full_path, "*.jpg"))
            for f in files:
                all_files.append(os.path.relpath(f, KEYFRAMES_DIR))
                
    print(f"Found {len(all_files)} files. Starting conversion...")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        list(tqdm(executor.map(generate_thumb, all_files), total=len(all_files)))
        
    print("--- DONE ---")

if __name__ == "__main__":
    main()
