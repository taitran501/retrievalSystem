"""
Timestamp conversion utilities for video retrieval system.
Converts between frame indices, seconds, and milliseconds for DRES submission.
"""

from typing import Union
import os
import json


DEFAULT_FPS = 25.0


def frame_to_milliseconds(frame_id: Union[int, str], fps: float = DEFAULT_FPS) -> int:
    """
    Convert frame index to milliseconds.
    
    Args:
        frame_id: Frame index (integer or string representation)
        fps: Frames per second (default: 25.0)
    
    Returns:
        Milliseconds as integer
    """
    frame_index = int(frame_id)
    return int((frame_index / fps) * 1000)


def seconds_to_milliseconds(seconds: Union[float, str]) -> int:
    """
    Convert seconds (float or string) to milliseconds.
    
    Args:
        seconds: Time in seconds (can be float or string like "2.56")
    
    Returns:
        Milliseconds as integer
    """
    if isinstance(seconds, str):
        seconds = float(seconds)
    return int(seconds * 1000)


def get_video_fps(video_name: str, fps_map_file: str = None) -> float:
    """
    Get FPS for a specific video.
    
    Currently returns default FPS. Can be extended to read from metadata
    or configuration file if available.
    
    Args:
        video_name: Name of the video (without extension)
        fps_map_file: Optional path to JSON file mapping video names to FPS
    
    Returns:
        FPS value (default: 25.0)
    """
    if fps_map_file and os.path.exists(fps_map_file):
        try:
            with open(fps_map_file, 'r') as f:
                fps_map = json.load(f)
                return fps_map.get(video_name, DEFAULT_FPS)
        except Exception:
            pass
    
    return DEFAULT_FPS


def remove_file_extension(filename: str) -> str:
    """
    Remove file extension from filename.
    
    Args:
        filename: Filename with or without extension (e.g., "video_01.mp4" or "video_01")
    
    Returns:
        Filename without extension (e.g., "video_01")
    """
    # Common video extensions
    extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v']
    
    for ext in extensions:
        if filename.lower().endswith(ext.lower()):
            return filename[:-len(ext)]
    
    return filename


def calculate_end_time(start_ms: int, duration_ms: int = 5000) -> int:
    """
    Calculate end time from start time.
    
    Args:
        start_ms: Start time in milliseconds
        duration_ms: Duration to add in milliseconds (default: 5000ms = 5 seconds)
    
    Returns:
        End time in milliseconds
    """
    return start_ms + duration_ms

