"""Tool 5: Body Measurement Calculator
Calculates body measurements from pose landmarks
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import math

# MediaPipe landmark indices
LANDMARKS = {
    'left_shoulder': 11,
    'right_shoulder': 12,
    'left_elbow': 13,
    'right_elbow': 14,
    'left_wrist': 15,
    'right_wrist': 16,
    'left_hip': 23,
    'right_hip': 24,
    'left_knee': 25,
    'right_knee': 26,
    'left_ankle': 27,
    'right_ankle': 28,
    'nose': 0,
    'left_eye': 2,
    'right_eye': 5
}

class BodyMeasurementCalculator:
    """Calculates body measurements from pose landmarks"""
    
    def __init__(self, reference_height_cm: Optional[float] = None):
        """
        Initialize calculator
        
        Args:
            reference_height_cm: User's actual height in cm for calibration
        """
        self.reference_height_cm = reference_height_cm
        self.calibration_factor = None
    
    def calculate_distance(self, point1: Dict, point2: Dict) -> float:
        """
        Calculate Euclidean distance between two landmarks
        
        Args:
            point1: First landmark with 'x', 'y', 'z' coordinates
            point2: Second landmark with 'x', 'y', 'z' coordinates
        
        Returns:
            Distance in pixels
        """
        dx = point1['x'] - point2['x']
        dy = point1['y'] - point2['y']
        dz = point1.get('z', 0) - point2.get('z', 0)
        
        return math.sqrt(dx**2 + dy**2 + dz**2)
    
    def calibrate(self, landmarks: Dict) -> bool:
        """
        Calibrate measurements using reference height
        
        Args:
            landmarks: Detected pose landmarks
        
        Returns:
            Success status
        """
        if not self.reference_height_cm:
            self.calibration_factor = 1.0
            return True
        
        try:
            # Calculate body height from nose to ankle
            nose = landmarks[LANDMARKS['nose']]
            left_ankle = landmarks[LANDMARKS['left_ankle']]
            right_ankle = landmarks[LANDMARKS['right_ankle']]
            
            # Use average of both ankles
            avg_ankle_y = (left_ankle['y'] + right_ankle['y']) / 2
            measured_height_px = abs(nose['y'] - avg_ankle_y)
            
            # Calculate calibration factor (cm per pixel)
            self.calibration_factor = self.reference_height_cm / measured_height_px
            return True
        
        except Exception:
            self.calibration_factor = 1.0
            return False
    
    def calculate_measurements(self, landmarks: Dict) -> Dict:
        """
        Calculate body measurements from landmarks
        
        Args:
            landmarks: Detected pose landmarks
        
        Returns:
            Dictionary of measurements
        """
        if self.calibration_factor is None:
            self.calibrate(landmarks)
        
        measurements = {}
        
        try:
            # Shoulder width
            left_shoulder = landmarks[LANDMARKS['left_shoulder']]
            right_shoulder = landmarks[LANDMARKS['right_shoulder']]
            shoulder_width_px = self.calculate_distance(left_shoulder, right_shoulder)
            measurements['shoulder_width'] = shoulder_width_px * self.calibration_factor
            
            # Arm length (shoulder to wrist)
            left_wrist = landmarks[LANDMARKS['left_wrist']]
            right_wrist = landmarks[LANDMARKS['right_wrist']]
            left_arm_length = self.calculate_distance(left_shoulder, left_wrist)
            right_arm_length = self.calculate_distance(right_shoulder, right_wrist)
            avg_arm_length = (left_arm_length + right_arm_length) / 2
            measurements['arm_length'] = avg_arm_length * self.calibration_factor
            
            # Torso length (shoulder to hip)
            left_hip = landmarks[LANDMARKS['left_hip']]
            right_hip = landmarks[LANDMARKS['right_hip']]
            avg_shoulder_y = (left_shoulder['y'] + right_shoulder['y']) / 2
            avg_hip_y = (left_hip['y'] + right_hip['y']) / 2
            torso_length_px = abs(avg_shoulder_y - avg_hip_y)
            measurements['torso_length'] = torso_length_px * self.calibration_factor
            
            # Hip width
            hip_width_px = self.calculate_distance(left_hip, right_hip)
            measurements['hip_width'] = hip_width_px * self.calibration_factor
            
            # Leg length (hip to ankle)
            left_ankle = landmarks[LANDMARKS['left_ankle']]
            right_ankle = landmarks[LANDMARKS['right_ankle']]
            left_leg_length = self.calculate_distance(left_hip, left_ankle)
            right_leg_length = self.calculate_distance(right_hip, right_ankle)
            avg_leg_length = (left_leg_length + right_leg_length) / 2
            measurements['leg_length'] = avg_leg_length * self.calibration_factor
            
            # Inseam (knee to ankle)
            left_knee = landmarks[LANDMARKS['left_knee']]
            right_knee = landmarks[LANDMARKS['right_knee']]
            left_inseam = self.calculate_distance(left_knee, left_ankle)
            right_inseam = self.calculate_distance(right_knee, right_ankle)
            avg_inseam = (left_inseam + right_inseam) / 2
            measurements['inseam'] = avg_inseam * self.calibration_factor
            
            # Total height
            nose = landmarks[LANDMARKS['nose']]
            avg_ankle_y = (left_ankle['y'] + right_ankle['y']) / 2
            height_px = abs(nose['y'] - avg_ankle_y)
            measurements['height'] = height_px * self.calibration_factor
            
            # Add calibration info
            measurements['calibration_factor'] = self.calibration_factor
            measurements['unit'] = 'cm' if self.reference_height_cm else 'pixels'
            
        except KeyError as e:
            measurements['error'] = f'Missing landmark: {str(e)}'
        except Exception as e:
            measurements['error'] = f'Calculation error: {str(e)}'
        
        return measurements

def calculate_measurements_from_poses(poses: List[Dict], 
                                     reference_height_cm: Optional[float] = None) -> Tuple[bool, any]:
    """
    Calculate measurements from multiple pose detections and average them
    
    Args:
        poses: List of valid pose detections
        reference_height_cm: Optional reference height for calibration
    
    Returns:
        (success, measurements or error_message)
    """
    try:
        if not poses:
            return False, "No poses provided"
        
        calculator = BodyMeasurementCalculator(reference_height_cm)
        all_measurements = []
        
        for pose in poses:
            landmarks = pose.get('landmarks', {})
            if landmarks:
                measurements = calculator.calculate_measurements(landmarks)
                if 'error' not in measurements:
                    all_measurements.append(measurements)
        
        if not all_measurements:
            return False, "No valid measurements could be calculated"
        
        # Average measurements across all frames
        avg_measurements = {}
        measurement_keys = [k for k in all_measurements[0].keys() 
                          if k not in ['calibration_factor', 'unit', 'error']]
        
        for key in measurement_keys:
            values = [m[key] for m in all_measurements if key in m]
            if values:
                avg_measurements[key] = np.mean(values)
                avg_measurements[f'{key}_std'] = np.std(values)
        
        avg_measurements['calibration_factor'] = calculator.calibration_factor
        avg_measurements['unit'] = all_measurements[0].get('unit', 'pixels')
        avg_measurements['frames_used'] = len(all_measurements)
        avg_measurements['total_frames'] = len(poses)
        
        return True, avg_measurements
    
    except Exception as e:
        return False, f"Measurement calculation error: {str(e)}"

def format_measurements(measurements: Dict) -> Dict:
    """
    Format measurements for display
    
    Args:
        measurements: Raw measurements dictionary
    
    Returns:
        Formatted measurements
    """
    formatted = {}
    
    unit = measurements.get('unit', 'pixels')
    
    for key, value in measurements.items():
        if key.endswith('_std'):
            formatted[key] = f"{value:.2f} {unit}"
        elif isinstance(value, (int, float)) and key not in ['calibration_factor', 'frames_used', 'total_frames']:
            formatted[key] = f"{value:.2f} {unit}"
        else:
            formatted[key] = value
    
    return formatted
