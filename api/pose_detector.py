"""Tool 3: Frame-by-Frame Pose Detector
Detects human pose landmarks in video frames using MediaPipe
"""

import mediapipe as mp
import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# Pose detection configuration
MIN_DETECTION_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5

class PoseDetector:
    """Wrapper class for MediaPipe Pose detection"""
    
    def __init__(self, 
                 static_image_mode=False,
                 min_detection_confidence=MIN_DETECTION_CONFIDENCE,
                 min_tracking_confidence=MIN_TRACKING_CONFIDENCE):
        """
        Initialize pose detector
        
        Args:
            static_image_mode: If True, treats each frame independently
            min_detection_confidence: Minimum confidence for person detection
            min_tracking_confidence: Minimum confidence for landmark tracking
        """
        self.pose = mp_pose.Pose(
            static_image_mode=static_image_mode,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
    
    def detect_pose(self, frame: np.ndarray) -> Tuple[bool, Optional[Dict]]:
        """
        Detect pose in a single frame
        
        Args:
            frame: Video frame as numpy array (BGR format)
        
        Returns:
            (success, pose_data or None)
        """
        try:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, _ = frame_rgb.shape
            
            # Process frame
            results = self.pose.process(frame_rgb)
            
            if not results.pose_landmarks:
                return False, None
            
            # Extract landmarks
            landmarks = {}
            for idx, landmark in enumerate(results.pose_landmarks.landmark):
                landmarks[idx] = {
                    'x': landmark.x * width,
                    'y': landmark.y * height,
                    'z': landmark.z,
                    'visibility': landmark.visibility
                }
            
            pose_data = {
                'landmarks': landmarks,
                'frame_shape': (height, width),
                'detected': True
            }
            
            return True, pose_data
        
        except Exception as e:
            return False, None
    
    def close(self):
        """Release resources"""
        self.pose.close()

def detect_poses_in_frames(frames: List[np.ndarray]) -> Tuple[bool, any]:
    """
    Detect poses in multiple frames
    
    Args:
        frames: List of video frames
    
    Returns:
        (success, poses_list or error_message)
    """
    try:
        detector = PoseDetector(static_image_mode=False)
        poses = []
        
        for frame in frames:
            success, pose_data = detector.detect_pose(frame)
            if success:
                poses.append(pose_data)
        
        detector.close()
        
        if not poses:
            return False, "No poses detected in any frame"
        
        return True, poses
    
    except Exception as e:
        return False, f"Error detecting poses: {str(e)}"

def get_landmark_visibility(pose_data: Dict, landmark_idx: int) -> float:
    """
    Get visibility score for a specific landmark
    
    Args:
        pose_data: Pose detection result
        landmark_idx: Index of landmark (0-32)
    
    Returns:
        Visibility score (0.0 to 1.0)
    """
    landmarks = pose_data.get('landmarks', {})
    if landmark_idx in landmarks:
        return landmarks[landmark_idx].get('visibility', 0.0)
    return 0.0

def is_full_body_visible(pose_data: Dict, threshold=0.5) -> bool:
    """
    Check if full body is visible in frame
    
    Args:
        pose_data: Pose detection result
        threshold: Minimum visibility threshold
    
    Returns:
        True if key body points are visible
    """
    # Key points for full body: nose, shoulders, hips, knees, ankles
    key_points = [
        0,   # nose
        11,  # left shoulder
        12,  # right shoulder
        23,  # left hip
        24,  # right hip
        25,  # left knee
        26,  # right knee
        27,  # left ankle
        28   # right ankle
    ]
    
    visible_count = 0
    for idx in key_points:
        if get_landmark_visibility(pose_data, idx) > threshold:
            visible_count += 1
    
    # Require at least 80% of key points visible
    return visible_count >= len(key_points) * 0.8

def filter_valid_poses(poses: List[Dict], 
                      min_visibility=0.5) -> List[Dict]:
    """
    Filter poses to keep only those with full body visible
    
    Args:
        poses: List of pose detection results
        min_visibility: Minimum visibility threshold
    
    Returns:
        Filtered list of valid poses
    """
    valid_poses = []
    for pose in poses:
        if is_full_body_visible(pose, min_visibility):
            valid_poses.append(pose)
    return valid_poses

def get_pose_confidence_score(pose_data: Dict) -> float:
    """
    Calculate overall confidence score for a pose
    
    Args:
        pose_data: Pose detection result
    
    Returns:
        Average confidence score (0.0 to 1.0)
    """
    landmarks = pose_data.get('landmarks', {})
    if not landmarks:
        return 0.0
    
    visibilities = [lm.get('visibility', 0.0) for lm in landmarks.values()]
    return sum(visibilities) / len(visibilities) if visibilities else 0.0

def draw_pose_on_frame(frame: np.ndarray, 
                       pose_data: Dict) -> np.ndarray:
    """
    Draw pose landmarks and connections on frame
    
    Args:
        frame: Video frame
        pose_data: Pose detection result
    
    Returns:
        Frame with pose overlay
    """
    try:
        # Create a copy to avoid modifying original
        output_frame = frame.copy()
        landmarks = pose_data.get('landmarks', {})
        
        # Draw landmarks
        for idx, lm_data in landmarks.items():
            x = int(lm_data['x'])
            y = int(lm_data['y'])
            visibility = lm_data.get('visibility', 0.0)
            
            if visibility > 0.5:
                # Draw circle for landmark
                color = (0, 255, 0) if visibility > 0.8 else (0, 255, 255)
                cv2.circle(output_frame, (x, y), 5, color, -1)
        
        return output_frame
    except Exception as e:
        return frame

def get_pose_statistics(poses: List[Dict]) -> Dict:
    """
    Calculate statistics across all detected poses
    
    Args:
        poses: List of pose detection results
    
    Returns:
        Statistics dictionary
    """
    if not poses:
        return {
            'total_poses': 0,
            'average_confidence': 0.0,
            'full_body_visible_count': 0
        }
    
    confidences = [get_pose_confidence_score(p) for p in poses]
    full_body_count = sum(1 for p in poses if is_full_body_visible(p))
    
    return {
        'total_poses': len(poses),
        'average_confidence': sum(confidences) / len(confidences),
        'min_confidence': min(confidences),
        'max_confidence': max(confidences),
        'full_body_visible_count': full_body_count,
        'full_body_percentage': (full_body_count / len(poses)) * 100
    }
