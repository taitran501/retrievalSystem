import os
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor

def get_fps(video_path):
    cmd = [
        'ffprobe', 
        '-v', 'error', 
        '-select_streams', 'v:0', 
        '-show_entries', 'stream=avg_frame_rate', 
        '-of', 'default=noprint_wrappers=1:nokey=1', 
        video_path
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8').strip()
        if '/' in output:
            num, den = map(int, output.split('/'))
            return num / den
        return float(output)
    except Exception as e:
        return None

def process_video(line):
    path = line.strip()
    if not path: return None
    filename = os.path.basename(path)
    video_id = os.path.splitext(filename)[0]
    fps = get_fps(path)
    return video_id, fps

video_list_file = 'all_videos.txt'
if not os.path.exists(video_list_file):
    print("all_videos.txt not found")
    exit(1)

with open(video_list_file, 'r') as f:
    lines = f.readlines()

print(f"Auditing {len(lines)} videos...")

video_fps_map = {}
with ThreadPoolExecutor(max_workers=8) as executor:
    results = list(executor.map(process_video, lines))

for res in results:
    if res:
        vid, fps = res
        if fps:
            video_fps_map[vid] = fps

with open('video_fps_map.json', 'w') as f:
    json.dump(video_fps_map, f, indent=2)

print(f"Done. Saved {len(video_fps_map)} entries to video_fps_map.json")

# Summary of FPS counts
fps_counts = {}
for fps in video_fps_map.values():
    fps_counts[fps] = fps_counts.get(fps, 0) + 1
print("FPS Summary:", fps_counts)
