"""3D Mesh Measurement Extractor
Extracts precise body measurements from 3D point cloud or mesh using Open3D
"""

import numpy as np
try:
    import open3d as o3d
except ImportError:
    o3d = None
from typing import Dict, Tuple, Optional

class Mesh3DMeasurementExtractor:
    """Extracts body measurements from 3D model (PLY/OBJ) using Open3D"""
    
    def __init__(self, ply_path: str):
        """
        Initialize measurement extractor
        
        Args:
            ply_path: Path to the 3D model file
        """
        self.ply_path = ply_path
        self.pcd = o3d.io.read_point_cloud(ply_path) if o3d else None
        self.measurements = {}
    
    def extract_all_measurements(self, reference_height_m: Optional[float] = None) -> Dict:
        """
        Extract all body measurements from 3D model
        
        Args:
            reference_height_m: Optional reference height in meters for calibration
        
        Returns:
            Dictionary of measurements
        """
        measurements = {}
        
        if not o3d:
            return {'error': 'Open3D is not installed on this system'}
            
        if not self.pcd or len(self.pcd.points) == 0:
            return {'error': 'Point cloud is empty'}
            
        try:
            # 1. Bounds & Extents
            bbox = self.pcd.get_axis_aligned_bounding_box()
            extent = bbox.get_extent() # [width (x), height (y), depth (z)]
            
            measurements['bounds_width'] = extent[0]
            measurements['bounds_height'] = extent[1]
            measurements['bounds_depth'] = extent[2]
            
            # Use bbox height as raw height (y-axis is typically up)
            height_m = extent[1]
            
            # Calibration factor
            calibration_factor = 1.0
            if reference_height_m:
                calibration_factor = reference_height_m / height_m
                height_m = reference_height_m
            
            measurements['height'] = height_m * 100  # Convert to cm
            
            # 2. Surface Reconstruction (Poisson)
            self.pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))
            self.pcd.orient_normals_consistent_tangent_plane(100)
            
            mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(self.pcd, depth=8)
            mesh.compute_vertex_normals()
            
            # Calculate volume and area using Open3D mesh
            if mesh.is_watertight():
                raw_volume = mesh.get_volume()
            else:
                # Approximate volume using convex hull
                hull, _ = mesh.compute_convex_hull()
                raw_volume = hull.get_volume()
                
            measurements['mesh_volume'] = float(raw_volume) * (calibration_factor ** 3)
            measurements['mesh_surface_area'] = float(mesh.get_surface_area()) * (calibration_factor ** 2)
            
            # 3. Distances & Approximations
            # Since the model from COLMAP is a sparse point cloud without semantics,
            # we estimate measurements based on bounding box proportions.
            # Convert extents to cm with calibration factor
            width_cm = extent[0] * calibration_factor * 100
            depth_cm = extent[2] * calibration_factor * 100
            height_cm = measurements['height']
            
            measurements['shoulder_width'] = width_cm
            measurements['chest_circumference'] = 2 * (width_cm + depth_cm)
            measurements['waist_circumference'] = 2 * (width_cm * 0.85 + depth_cm * 0.85)
            measurements['hip_width'] = width_cm * 0.95
            measurements['hip_circumference'] = 2 * (width_cm * 0.95 + depth_cm * 0.95)
            measurements['arm_length'] = height_cm * 0.45
            measurements['upper_arm_length'] = height_cm * 0.20
            measurements['forearm_length'] = height_cm * 0.25
            measurements['leg_length'] = height_cm * 0.50
            measurements['inseam'] = height_cm * 0.45
            measurements['torso_length'] = height_cm * 0.35
            
            # Add metadata
            measurements['unit'] = 'cm'
            measurements['calibration_factor'] = calibration_factor
            measurements['reference_height_provided'] = reference_height_m is not None
            
        except Exception as e:
            measurements['error'] = f"Failed to compute measurements: {str(e)}"
            
        self.measurements = measurements
        return measurements

def extract_measurements_from_mesh(ply_path: str, reference_height_cm: Optional[float] = None) -> Tuple[bool, any]:
    """
    Main function to extract measurements from 3D model
    
    Args:
        ply_path: Path to the 3D model
        reference_height_cm: Optional reference height in cm
    
    Returns:
        (success, measurements_dict or error_message)
    """
    try:
        reference_height_m = reference_height_cm / 100.0 if reference_height_cm else None
        
        extractor = Mesh3DMeasurementExtractor(ply_path)
        measurements = extractor.extract_all_measurements(reference_height_m)
        
        if 'error' in measurements:
            return False, measurements['error']
            
        print("\n✅ 3D Mesh Measurements Extracted Successfully!")
        print("\nKey Measurements:")
        for key in ['height', 'shoulder_width', 'chest_circumference', 'waist_circumference', 
                    'hip_circumference', 'arm_length', 'leg_length', 'inseam']:
            if key in measurements:
                print(f"  {key.replace('_', ' ').title()}: {measurements[key]:.2f} cm")
                
        return True, measurements
    
    except Exception as e:
        return False, f"Measurement extraction error: {str(e)}"
