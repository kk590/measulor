"""Video to 3D Reconstruction Module
Converts video frames into 3D human body mesh using COLMAP multi-view reconstruction
"""

import os
import cv2
import tempfile
try:
    import pycolmap
except ImportError:
    pycolmap = None
import numpy as np
from typing import List, Tuple, Dict, Optional

class VideoTo3DReconstructor:
    """Reconstructs 3D human body model from video frames using COLMAP"""
    
    def __init__(self):
        self.output_dir = tempfile.mkdtemp()
        self.image_dir = os.path.join(self.output_dir, "images")
        os.makedirs(self.image_dir, exist_ok=True)
        self.db_path = os.path.join(self.output_dir, "database.db")
        self.model_path = os.path.join(self.output_dir, "sparse")
        os.makedirs(self.model_path, exist_ok=True)
        self.model = None
        self.ply_path = None

    def extract_and_match(self, frames: List[np.ndarray]) -> Tuple[bool, str]:
        """Extract and match features using pycolmap"""
        if not pycolmap:
            return False, "pycolmap is not installed"
        try:
            # Save frames to disk for COLMAP
            for i, frame in enumerate(frames):
                frame_path = os.path.join(self.image_dir, f"frame_{i:04d}.jpg")
                cv2.imwrite(frame_path, frame)
            
            # Feature extraction
            pycolmap.extract_features(self.db_path, self.image_dir)
            
            # Feature matching
            pycolmap.match_exhaustive(self.db_path)
            
            return True, "Features extracted and matched"
        except Exception as e:
            return False, f"Error in COLMAP extraction/matching: {e}"

    def reconstruct(self) -> Tuple[bool, str]:
        """Incremental mapping and sparse reconstruction"""
        if not pycolmap:
            return False, "pycolmap is not installed"
        try:
            # Incremental mapping
            maps = pycolmap.incremental_mapping(self.db_path, self.image_dir, self.model_path)
            if not maps:
                return False, "Failed to reconstruct any sparse model"
            
            # Use the largest model reconstructed (maps is a dict)
            largest_model_idx = max(maps.keys(), key=lambda i: maps[i].num_points3D())
            self.model = maps[largest_model_idx]
            
            # Export to PLY
            self.ply_path = os.path.join(self.output_dir, "model.ply")
            self.model.write_ply(self.ply_path)
            
            return True, self.ply_path
        except Exception as e:
            return False, f"Error in COLMAP reconstruction: {e}"

    def get_mesh_info(self) -> Dict:
        if self.model is None:
            return {'error': 'No model available'}
            
        return {
            'num_vertices': self.model.num_points3D(),
            'num_faces': 0, # Point cloud has no faces
            'volume': 0.0,  # Handled by open3d
            'surface_area': 0.0, # Handled by open3d
            'is_watertight': False,
        }

def reconstruct_3d_from_video(frames: List[np.ndarray]) -> Tuple[bool, any]:
    """
    Main function to reconstruct 3D mesh from video frames
    
    Args:
        frames: List of video frames
    
    Returns:
        (success, result_dict or error_message)
    """
    try:
        reconstructor = VideoTo3DReconstructor()
        
        # Step 1: Extract and match features
        print("Step 1: Extracting and matching features using COLMAP...")
        success, msg = reconstructor.extract_and_match(frames)
        if not success:
            return False, msg
        print(f"✓ {msg}")
        
        # Step 2: Create 3D body sparse model
        print("\nStep 2: Creating 3D body sparse model...")
        success, result = reconstructor.reconstruct()
        if not success:
            return False, result
        print(f"✓ Reconstructed sparse model and saved to {result}")
        
        # Get mesh info
        mesh_info = reconstructor.get_mesh_info()
        
        result_dict = {
            'ply_path': result,
            'mesh_info': mesh_info,
            'reconstructor': reconstructor
        }
        
        print("\n✅ 3D reconstruction completed successfully!\n")
        return True, result_dict
    
    except Exception as e:
        return False, f"3D reconstruction pipeline error: {str(e)}"
