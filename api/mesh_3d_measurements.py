"""3D Mesh Measurement Extractor
Extracts precise body measurements from 3D mesh
"""

import numpy as np
import trimesh
from typing import Dict, Tuple, Optional
from scipy.spatial.distance import euclidean
import math

class Mesh3DMeasurementExtractor:
    """Extracts body measurements from 3D mesh"""
    
    def __init__(self, mesh: trimesh.Trimesh, landmarks_3d: np.ndarray):
        """
        Initialize measurement extractor
        
        Args:
            mesh: 3D body mesh
            landmarks_3d: 3D landmark coordinates from MediaPipe
        """
        self.mesh = mesh
        self.landmarks_3d = landmarks_3d
        self.measurements = {}
    
    def get_landmark_point(self, index: int) -> np.ndarray:
        """
        Get 3D coordinates of a specific landmark
        
        Args:
            index: Landmark index
        
        Returns:
            3D coordinates (x, y, z)
        """
        return self.landmarks_3d[index, :3]
    
    def calculate_distance_3d(self, point1: np.ndarray, point2: np.ndarray) -> float:
        """
        Calculate 3D Euclidean distance between two points
        
        Args:
            point1: First 3D point
            point2: Second 3D point
        
        Returns:
            Distance in meters
        """
        return euclidean(point1, point2)
    
    def calculate_circumference_at_height(self, height_y: float, tolerance: float = 0.02) -> float:
        """
        Calculate mesh circumference at a specific height
        
        Args:
            height_y: Y-coordinate height
            tolerance: Height tolerance range
        
        Returns:
            Circumference in meters
        """
        # Get vertices within height range
        vertices = self.mesh.vertices
        mask = np.abs(vertices[:, 1] - height_y) < tolerance
        slice_vertices = vertices[mask]
        
        if len(slice_vertices) < 3:
            return 0.0
        
        # Calculate convex hull perimeter at this height
        try:
            from scipy.spatial import ConvexHull
            # Project to 2D (x, z plane)
            points_2d = slice_vertices[:, [0, 2]]
            hull = ConvexHull(points_2d)
            
            # Calculate perimeter
            perimeter = 0.0
            for i in range(len(hull.vertices)):
                p1 = points_2d[hull.vertices[i]]
                p2 = points_2d[hull.vertices[(i + 1) % len(hull.vertices)]]
                perimeter += euclidean(p1, p2)
            
            return perimeter
        except:
            return 0.0
    
    def extract_all_measurements(self, reference_height_m: Optional[float] = None) -> Dict:
        """
        Extract all body measurements from 3D mesh
        
        Args:
            reference_height_m: Optional reference height in meters for calibration
        
        Returns:
            Dictionary of measurements
        """
        measurements = {}
        
        # Landmark indices (MediaPipe Pose)
        NOSE = 0
        LEFT_SHOULDER = 11
        RIGHT_SHOULDER = 12
        LEFT_ELBOW = 13
        RIGHT_ELBOW = 14
        LEFT_WRIST = 15
        RIGHT_WRIST = 16
        LEFT_HIP = 23
        RIGHT_HIP = 24
        LEFT_KNEE = 25
        RIGHT_KNEE = 26
        LEFT_ANKLE = 27
        RIGHT_ANKLE = 28
        
        # Get landmark points
        nose = self.get_landmark_point(NOSE)
        left_shoulder = self.get_landmark_point(LEFT_SHOULDER)
        right_shoulder = self.get_landmark_point(RIGHT_SHOULDER)
        left_elbow = self.get_landmark_point(LEFT_ELBOW)
        right_elbow = self.get_landmark_point(RIGHT_ELBOW)
        left_wrist = self.get_landmark_point(LEFT_WRIST)
        right_wrist = self.get_landmark_point(RIGHT_WRIST)
        left_hip = self.get_landmark_point(LEFT_HIP)
        right_hip = self.get_landmark_point(RIGHT_HIP)
        left_knee = self.get_landmark_point(LEFT_KNEE)
        right_knee = self.get_landmark_point(RIGHT_KNEE)
        left_ankle = self.get_landmark_point(LEFT_ANKLE)
        right_ankle = self.get_landmark_point(RIGHT_ANKLE)
        
        # 1. Height (nose to average ankle)
        avg_ankle = (left_ankle + right_ankle) / 2
        height_m = abs(nose[1] - avg_ankle[1])
        
        # Calibration factor
        calibration_factor = 1.0
        if reference_height_m:
            calibration_factor = reference_height_m / height_m
            height_m = reference_height_m
        
        measurements['height'] = height_m * 100  # Convert to cm
        
        # 2. Shoulder width (3D distance)
        shoulder_width = self.calculate_distance_3d(left_shoulder, right_shoulder)
        measurements['shoulder_width'] = shoulder_width * calibration_factor * 100
        
        # 3. Chest circumference (at shoulder height)
        chest_height = (left_shoulder[1] + right_shoulder[1]) / 2
        chest_circumference = self.calculate_circumference_at_height(chest_height)
        measurements['chest_circumference'] = chest_circumference * calibration_factor * 100
        
        # 4. Waist circumference (midpoint between shoulders and hips)
        waist_height = ((left_shoulder[1] + right_shoulder[1]) / 2 + (left_hip[1] + right_hip[1]) / 2) / 2
        waist_circumference = self.calculate_circumference_at_height(waist_height)
        measurements['waist_circumference'] = waist_circumference * calibration_factor * 100
        
        # 5. Hip width (3D distance)
        hip_width = self.calculate_distance_3d(left_hip, right_hip)
        measurements['hip_width'] = hip_width * calibration_factor * 100
        
        # 6. Hip circumference
        hip_height = (left_hip[1] + right_hip[1]) / 2
        hip_circumference = self.calculate_circumference_at_height(hip_height)
        measurements['hip_circumference'] = hip_circumference * calibration_factor * 100
        
        # 7. Arm length (shoulder to wrist, averaged)
        left_arm = self.calculate_distance_3d(left_shoulder, left_wrist)
        right_arm = self.calculate_distance_3d(right_shoulder, right_wrist)
        arm_length = (left_arm + right_arm) / 2
        measurements['arm_length'] = arm_length * calibration_factor * 100
        
        # 8. Upper arm length (shoulder to elbow)
        left_upper_arm = self.calculate_distance_3d(left_shoulder, left_elbow)
        right_upper_arm = self.calculate_distance_3d(right_shoulder, right_elbow)
        upper_arm_length = (left_upper_arm + right_upper_arm) / 2
        measurements['upper_arm_length'] = upper_arm_length * calibration_factor * 100
        
        # 9. Forearm length (elbow to wrist)
        left_forearm = self.calculate_distance_3d(left_elbow, left_wrist)
        right_forearm = self.calculate_distance_3d(right_elbow, right_wrist)
        forearm_length = (left_forearm + right_forearm) / 2
        measurements['forearm_length'] = forearm_length * calibration_factor * 100
        
        # 10. Leg length (hip to ankle)
        left_leg = self.calculate_distance_3d(left_hip, left_ankle)
        right_leg = self.calculate_distance_3d(right_hip, right_ankle)
        leg_length = (left_leg + right_leg) / 2
        measurements['leg_length'] = leg_length * calibration_factor * 100
        
        # 11. Inseam (knee to ankle)
        left_inseam = self.calculate_distance_3d(left_knee, left_ankle)
        right_inseam = self.calculate_distance_3d(right_knee, right_ankle)
        inseam = (left_inseam + right_inseam) / 2
        measurements['inseam'] = inseam * calibration_factor * 100
        
        # 12. Torso length (shoulder midpoint to hip midpoint)
        shoulder_mid = (left_shoulder + right_shoulder) / 2
        hip_mid = (left_hip + right_hip) / 2
        torso_length = self.calculate_distance_3d(shoulder_mid, hip_mid)
        measurements['torso_length'] = torso_length * calibration_factor * 100
        
        # Add mesh statistics
        measurements['mesh_volume'] = float(self.mesh.volume) * (calibration_factor ** 3)
        measurements['mesh_surface_area'] = float(self.mesh.area) * (calibration_factor ** 2)
        
        # Add metadata
        measurements['unit'] = 'cm'
        measurements['calibration_factor'] = calibration_factor
        measurements['reference_height_provided'] = reference_height_m is not None
        
        self.measurements = measurements
        return measurements
    
    def get_formatted_measurements(self) -> Dict:
        """
        Get formatted measurements for display
        
        Returns:
            Formatted measurements dictionary
        """
        if not self.measurements:
            return {'error': 'No measurements available. Run extract_all_measurements() first.'}
        
        formatted = {}
        for key, value in self.measurements.items():
            if isinstance(value, float) and key not in ['calibration_factor', 'mesh_volume', 'mesh_surface_area']:
                formatted[key] = f"{value:.2f} cm"
            elif key == 'mesh_volume':
                formatted[key] = f"{value:.6f} m³"
            elif key == 'mesh_surface_area':
                formatted[key] = f"{value:.4f} m²"
            else:
                formatted[key] = value
        
        return formatted

def extract_measurements_from_mesh(mesh: trimesh.Trimesh, 
                                   landmarks_3d: np.ndarray,
                                   reference_height_cm: Optional[float] = None) -> Tuple[bool, any]:
    """
    Main function to extract measurements from 3D mesh
    
    Args:
        mesh: 3D body mesh
        landmarks_3d: 3D landmark coordinates
        reference_height_cm: Optional reference height in cm
    
    Returns:
        (success, measurements_dict or error_message)
    """
    try:
        # Convert reference height to meters if provided
        reference_height_m = reference_height_cm / 100.0 if reference_height_cm else None
        
        # Create extractor
        extractor = Mesh3DMeasurementExtractor(mesh, landmarks_3d)
        
        # Extract measurements
        measurements = extractor.extract_all_measurements(reference_height_m)
        
        print("\n✅ 3D Mesh Measurements Extracted Successfully!")
        print("\nKey Measurements:")
        for key in ['height', 'shoulder_width', 'chest_circumference', 'waist_circumference', 
                    'hip_circumference', 'arm_length', 'leg_length', 'inseam']:
            if key in measurements:
                print(f"  {key.replace('_', ' ').title()}: {measurements[key]:.2f} cm")
        
        return True, measurements
    
    except Exception as e:
        return False, f"Measurement extraction error: {str(e)}"
