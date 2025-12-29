#!/usr/bin/env python3
"""
OCR Processor for Keyframe Text Extraction
Uses EasyOCR for Vietnamese + English text recognition
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
from tqdm import tqdm
from PIL import Image

try:
    import easyocr
except ImportError:
    print("EasyOCR not installed. Run: pip install easyocr")
    exit(1)


class KeyframeOCRProcessor:
    """Process keyframes to extract text using EasyOCR"""
    
    def __init__(
        self,
        keyframes_dir: str = "/home/ir/retrievalSystem/data/keyframes",
        output_dir: str = "/home/ir/keyframes_new/ocr_results",
        languages: List[str] = ['en'],  # ['en', 'vi'] for Vietnamese
        use_gpu: bool = False
    ):
        self.keyframes_dir = Path(keyframes_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize EasyOCR
        print(f"Initializing EasyOCR (GPU: {use_gpu}, Languages: {languages})...")
        self.reader = easyocr.Reader(languages, gpu=use_gpu)
        print("✅ OCR initialized")
    
    def extract_text_from_image(self, image_path: Path) -> List[Dict]:
        """
        Extract text from a single image
        
        Returns:
            List of dicts with format:
            {
                'text': str,
                'confidence': float,
                'bbox': [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            }
        """
        try:
            # EasyOCR returns: (bbox, text, confidence)
            result = self.reader.readtext(str(image_path))
            
            if not result:
                return []
            
            extracted_texts = []
            for bbox, text, confidence in result:
                extracted_texts.append({
                    'text': text,
                    'confidence': float(confidence),
                    'bbox': bbox
                })
            
            return extracted_texts
        
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            return []
    
    def process_video_folder(self, level_id: str, video_id: str) -> Dict:
        """
        Process all keyframes in a video folder
        
        Returns:
            {
                'video_id': str,
                'level': str,
                'frames': {
                    'frame_id': {
                        'texts': [...],
                        'all_text': 'concatenated text'
                    }
                }
            }
        """
        video_path = self.keyframes_dir / level_id / video_id
        if not video_path.exists():
            return None
        
        frames_data = {}
        image_files = sorted(video_path.glob("*.jpg"))
        
        for img_path in image_files:
            frame_id = img_path.stem  # filename without extension
            texts = self.extract_text_from_image(img_path)
            
            if texts:  # Only save if text found
                frames_data[frame_id] = {
                    'texts': texts,
                    'all_text': ' '.join([t['text'] for t in texts]),
                    'high_conf_text': ' '.join([t['text'] for t in texts if t['confidence'] > 0.8])
                }
        
        return {
            'video_id': video_id,
            'level': level_id,
            'total_frames': len(image_files),
            'frames_with_text': len(frames_data),
            'frames': frames_data
        }
    
    def process_level(self, level_id: str, save_per_video: bool = True):
        """
        Process all videos in a level
        
        Args:
            level_id: Level folder name (e.g., 'L01')
            save_per_video: If True, save one JSON per video. If False, save one JSON per level.
        """
        level_path = self.keyframes_dir / level_id
        if not level_path.exists():
            print(f"⚠️  Level {level_id} not found")
            return
        
        video_folders = sorted([d for d in level_path.iterdir() if d.is_dir()])
        print(f"\n📁 Processing {level_id}: {len(video_folders)} videos")
        
        level_output_dir = self.output_dir / level_id
        level_output_dir.mkdir(parents=True, exist_ok=True)
        
        level_data = []
        
        for video_folder in tqdm(video_folders, desc=f"  {level_id}"):
            video_id = video_folder.name
            video_data = self.process_video_folder(level_id, video_id)
            
            if video_data and video_data['frames_with_text'] > 0:
                level_data.append(video_data)
                
                if save_per_video:
                    # Save individual video JSON
                    output_file = level_output_dir / f"{video_id}_ocr.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(video_data, f, ensure_ascii=False, indent=2)
        
        # Save level summary
        summary_file = self.output_dir / f"{level_id}_summary.json"
        summary = {
            'level': level_id,
            'total_videos': len(video_folders),
            'videos_with_text': len(level_data),
            'total_frames_with_text': sum(v['frames_with_text'] for v in level_data)
        }
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"  ✅ {level_id}: {summary['videos_with_text']}/{summary['total_videos']} videos have text")
        print(f"     Total frames with text: {summary['total_frames_with_text']}")
    
    def process_all_levels(self, levels: List[str] = None):
        """Process all levels L01-L12"""
        if levels is None:
            levels = [f"L{i:02d}" for i in range(1, 13)]
        
        print("="*70)
        print("OCR PROCESSING - EasyOCR")
        print("="*70)
        print(f"Input: {self.keyframes_dir}")
        print(f"Output: {self.output_dir}")
        print(f"Levels: {', '.join(levels)}")
        print("="*70)
        
        for level_id in levels:
            self.process_level(level_id)
        
        print("\n" + "="*70)
        print("✅ OCR PROCESSING COMPLETE")
        print("="*70)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract OCR text from keyframes")
    parser.add_argument(
        "--keyframes-dir",
        default="/home/ir/retrievalSystem/data/keyframes",
        help="Path to keyframes directory"
    )
    parser.add_argument(
        "--output-dir",
        default="/home/ir/keyframes_new/ocr_results",
        help="Path to save OCR results"
    )
    parser.add_argument(
        "--levels",
        nargs="+",
        default=None,
        help="Specific levels to process (e.g., L01 L02). Default: all L01-L12"
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        default=['en'],
        help="OCR languages (e.g., en vi for English + Vietnamese)"
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Use GPU if available"
    )
    
    args = parser.parse_args()
    
    processor = KeyframeOCRProcessor(
        keyframes_dir=args.keyframes_dir,
        output_dir=args.output_dir,
        languages=args.languages,
        use_gpu=args.gpu
    )
    
    processor.process_all_levels(levels=args.levels)


if __name__ == "__main__":
    main()
