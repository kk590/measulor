"""Tool 2: Video Frame Extractor
Extracts frames from video at specified intervals for pose detection
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional

# Configuration
DEFAULT_FRAME_INTERVAL = 5  # Extract every 5th frame
MAX_FRAMES_TO_PROCESS = 30  # Maximum frames to extract
MIN_FRAMES_REQUIRED = 10    # Minimum frames needed for valid measurement

def get_video_info(video_path: str) -> Optional[dict]:
    """
    Get basic information about the video
    Returns: dict with fps, frame_count, duration, resolution
    """
    try:
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return None
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        
        cap.release()
        
        return {
            'fps': fps,
            'frame_count': frame_count,
            'duration': duration,
            'width': width,
            'height': height,
            'resolution': f"{width}x{height}"
        }
    except Exception as e:
        return None

def extract_frames(video_path: str, 
                  frame_interval: int = DEFAULT_FRAME_INTERVAL,
                  max_frames: int = MAX_FRAMES_TO_PROCESS) -> Tuple[bool, any]:
    """
    Extract frames from video at specified intervals
    
    Args:
        video_path: Path to video file
        frame_interval: Extract every Nth frame
        max_frames: Maximum number of frames to extract
    
    Returns:
        (success, frames_list or error_message)
    """
    try:
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return False, "Could not open video file"
        
        frames = []
        frame_number = 0
        extracted_count = 0
        
        while cap.isOpened() and extracted_count < max_frames:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Extract frame at specified interval
            if frame_number % frame_interval == 0:
                frames.append(frame)
                extracted_count += 1
            
            frame_number += 1
        
        cap.release()
        
        # Check if we have enough frames
        if len(frames) < MIN_FRAMES_REQUIRED:
            return False, f"Too few frames extracted. Got {len(frames)}, need at least {MIN_FRAMES_REQUIRED}"
        
        return True, frames
    
    except Exception as e:
        return False, f"Error extracting frames: {str(e)}"

def extract_single_frame(video_path: str, frame_position: int = 0) -> Tuple[bool, any]:
    """
    Extract a single frame from video at specified position
    
    Args:
        video_path: Path to video file
        frame_position: Frame number to extract (0 = first frame)
    
    Returns:
        (success, frame or error_message)
    """
    try:
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return False, "Could not open video file"
        
        # Set frame position
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return False, f"Could not read frame at position {frame_position}"
        
        return True, frame
    
    except Exception as e:
        return False, f"Error extracting frame: {str(e)}"

def extract_frames_by_time(video_path: str, 
                          time_intervals: List[float]) -> Tuple[bool, any]:
    """
    Extract frames at specific time points (in seconds)
    
    Args:
        video_path: Path to video file
        time_intervals: List of time points in seconds
    
    Returns:
        (success, frames_list or error_message)
    """
    try:
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return False, "Could not open video file"
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = []
        
        for time_sec in time_intervals:
            frame_num = int(time_sec * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
        
        cap.release()
        
        if not frames:
            return False, "No frames could be extracted at specified times"
        
        return True, frames
    
    except Exception as e:
        return False, f"Error extracting frames by time: {str(e)}"

def get_frame_quality(frame: np.ndarray) -> dict:
    """
    Assess the quality of a frame
    
    Args:
        frame: Video frame as numpy array
    
    Returns:
        dict with quality metrics (brightness, blur_score, etc.)
    """
    try:
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate brightness (mean pixel value)
        brightness = np.mean(gray)
        
        # Calculate blur score using Laplacian variance
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        blur_score = laplacian.var()
        
        # Determine quality
        is_bright_enough = 40 < brightness < 220  # Not too dark or overexposed
        is_sharp_enough = blur_score > 100  # Higher = sharper
        
        return {
            'brightness': float(brightness),
            'blur_score': float(blur_score),
            'is_bright_enough': is_bright_enough,
            'is_sharp_enough': is_sharp_enough,
            'overall_quality': 'good' if (is_bright_enough and is_sharp_enough) else 'poor'
        }
    except Exception as e:
        return {'error': str(e)}

def filter_good_frames(frames: List[np.ndarray]) -> List[np.ndarray]:
    """
    Filter out poor quality frames
    
    Args:
        frames: List of video frames
    
    Returns:
        List of good quality frames
    """
    good_frames = []
    
    for frame in frames:
        quality = get_frame_quality(frame)
        if quality.get('overall_quality') == 'good':
            good_frames.append(frame)
    
    return good_frames
