"""Tool 4: Pose Quality Validator
Validates pose detection quality and filters poor detections
"""

import numpy as np
from typing import Dict, List, Tuple, Optional

# Quality thresholds
MIN_VISIBILITY_THRESHOLD = 0.5
MIN_LANDMARKS_REQUIRED = 25  # Out of 33 MediaPipe landmarks
KEY_LANDMARKS = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]  # Shoulders, elbows, wrists, hips, knees, ankles

class PoseQualityValidator:
    """Validates pose detection quality"""
    
    def __init__(self, 
                 min_visibility=MIN_VISIBILITY_THRESHOLD,
                 min_landmarks=MIN_LANDMARKS_REQUIRED):
        """
        Initialize quality validator
        
        Args:
            min_visibility: Minimum visibility score for landmarks
            min_landmarks: Minimum number of visible landmarks required
        """
        self.min_visibility = min_visibility
        self.min_landmarks = min_landmarks
    
    def validate_pose(self, pose_data: Dict) -> Tuple[bool, Dict]:
        """
        Validate a single pose detection
        
        Args:
            pose_data: Pose detection result from pose_detector
        
        Returns:
            (is_valid, quality_metrics)
        """
        if not pose_data or not pose_data.get('detected'):
            return False, {'reason': 'no_detection'}
        
        landmarks = pose_data.get('landmarks', {})
        
        # Check total landmarks count
        if len(landmarks) < self.min_landmarks:
            return False, {
                'reason': 'insufficient_landmarks',
                'landmarks_count': len(landmarks)
            }
        
        # Check visibility of landmarks
        visible_count = 0
        key_landmarks_visible = 0
        visibility_scores = []
        
        for idx, lm_data in landmarks.items():
            visibility = lm_data.get('visibility', 0)
            visibility_scores.append(visibility)
            
            if visibility >= self.min_visibility:
                visible_count += 1
                if idx in KEY_LANDMARKS:
                    key_landmarks_visible += 1
        
        avg_visibility = np.mean(visibility_scores) if visibility_scores else 0
        
        # Check if enough landmarks are visible
        if visible_count < self.min_landmarks:
            return False, {
                'reason': 'low_visibility',
                'visible_count': visible_count,
                'avg_visibility': avg_visibility
            }
        
        # Check key body landmarks
        if key_landmarks_visible < len(KEY_LANDMARKS) * 0.75:  # At least 75% of key landmarks
            return False, {
                'reason': 'key_landmarks_missing',
                'key_visible': key_landmarks_visible,
                'key_required': len(KEY_LANDMARKS)
            }
        
        # Pose is valid
        quality_metrics = {
            'valid': True,
            'total_landmarks': len(landmarks),
            'visible_landmarks': visible_count,
            'avg_visibility': float(avg_visibility),
            'key_landmarks_visible': key_landmarks_visible,
            'quality_score': self._calculate_quality_score(
                visible_count, 
                len(landmarks), 
                avg_visibility
            )
        }
        
        return True, quality_metrics
    
    def _calculate_quality_score(self, visible: int, total: int, avg_vis: float) -> float:
        """
        Calculate overall quality score (0-1)
        
        Args:
            visible: Number of visible landmarks
            total: Total landmarks
            avg_vis: Average visibility score
        
        Returns:
            Quality score between 0 and 1
        """
        visibility_ratio = visible / total if total > 0 else 0
        return (visibility_ratio * 0.5 + avg_vis * 0.5)

def validate_poses_batch(poses: List[Dict]) -> Tuple[bool, any]:
    """
    Validate multiple pose detections
    
    Args:
        poses: List of pose detection results
    
    Returns:
        (success, validation_results or error_message)
    """
    try:
        validator = PoseQualityValidator()
        results = []
        
        for i, pose in enumerate(poses):
            is_valid, metrics = validator.validate_pose(pose)
            results.append({
                'frame_index': i,
                'is_valid': is_valid,
                'metrics': metrics
            })
        
        # Calculate batch statistics
        valid_count = sum(1 for r in results if r['is_valid'])
        valid_percentage = (valid_count / len(results) * 100) if results else 0
        
        batch_stats = {
            'total_frames': len(results),
            'valid_frames': valid_count,
            'invalid_frames': len(results) - valid_count,
            'valid_percentage': valid_percentage,
            'frame_results': results
        }
        
        return True, batch_stats
    
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def filter_valid_poses(poses: List[Dict]) -> Tuple[List[Dict], List[int]]:
    """
    Filter out invalid poses and return only valid ones
    
    Args:
        poses: List of pose detection results
    
    Returns:
        (valid_poses, valid_indices)
    """
    validator = PoseQualityValidator()
    valid_poses = []
    valid_indices = []
    
    for i, pose in enumerate(poses):
        is_valid, _ = validator.validate_pose(pose)
        if is_valid:
            valid_poses.append(pose)
            valid_indices.append(i)
    
    return valid_poses, valid_indices
