video_to_3d_reconstruction.py"""Video to 3D Reconstruction Module
Converts video frames into 3D human body mesh using multi-view reconstruction
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
import trimesh
import open3d as o3d
from scipy.spatial import Delaunay

# Import MediaPipe for pose landmarks (used as 3D scaffold)
import mediapipe as mp
mp_pose = mp.solutions.pose

class VideoTo3DReconstructor:
    """Reconstructs 3D human body mesh from video frames"""
    
    def __init__(self):
        self.pose_detector = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,  # Use highest quality model
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mesh = None
        self.landmark_3d_points = []
    
    def extract_3d_landmarks(self, frames: List[np.ndarray]) -> Tuple[bool, any]:
        """
        Extract 3D landmarks from multiple video frames
        
        Args:
            frames: List of video frames
        
        Returns:
            (success, 3d_landmarks or error_message)
        """
        try:
            all_landmarks_3d = []
            
            for frame in frames:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width = frame_rgb.shape[:2]
                
                # Process frame
                results = self.pose_detector.process(frame_rgb)
                
                if results.pose_world_landmarks:
                    # Extract 3D world coordinates (in meters)
                    landmarks_3d = []
                    for landmark in results.pose_world_landmarks.landmark:
                        landmarks_3d.append([
                            landmark.x,
                            landmark.y,
                            landmark.z,
                            landmark.visibility
                        ])
                    all_landmarks_3d.append(landmarks_3d)
            
            if not all_landmarks_3d:
                return False, "No 3D landmarks detected in any frame"
            
            # Average landmarks across all frames for stability
            avg_landmarks = np.mean(all_landmarks_3d, axis=0)
            self.landmark_3d_points = avg_landmarks
            
            return True, avg_landmarks
        
        except Exception as e:
            return False, f"3D landmark extraction error: {str(e)}"
    
    def create_body_mesh(self, landmarks_3d: np.ndarray) -> Tuple[bool, any]:
        """
        Create 3D mesh from landmarks using Delaunay triangulation
        
        Args:
            landmarks_3d: 3D landmark coordinates
        
        Returns:
            (success, mesh or error_message)
        """
        try:
            # Extract xyz coordinates (ignore visibility)
            points_3d = landmarks_3d[:, :3]
            
            # Define body part indices for better mesh generation
            # Key body points for mesh creation
            body_indices = [
                0,   # nose
                11, 12,  # shoulders
                13, 14,  # elbows
                15, 16,  # wrists
                23, 24,  # hips
                25, 26,  # knees
                27, 28,  # ankles
                # Add intermediate points for smoother mesh
                7, 8,    # ears
                9, 10,   # eyes
            ]
            
            # Select key body points
            key_points = points_3d[body_indices]
            
            # Create convex hull for body surface
            try:
                mesh = trimesh.convex.convex_hull(key_points)
            except:
                # Fallback: create simple mesh using Delaunay
                # Project to 2D for triangulation
                points_2d = key_points[:, :2]
                tri = Delaunay(points_2d)
                
                # Create 3D mesh
                mesh = trimesh.Trimesh(
                    vertices=key_points,
                    faces=tri.simplices
                )
            
            # Smooth the mesh
            mesh = trimesh.smoothing.filter_laplacian(mesh, iterations=5)
            
            self.mesh = mesh
            return True, mesh
        
        except Exception as e:
            return False, f"Mesh creation error: {str(e)}"
    
    def refine_mesh(self, mesh: trimesh.Trimesh) -> Tuple[bool, any]:
        """
        Refine and clean the 3D mesh
        
        Args:
            mesh: Input mesh
        
        Returns:
            (success, refined_mesh or error_message)
        """
        try:
            # Remove degenerate faces
            mesh.remove_degenerate_faces()
            
            # Remove duplicate vertices
            mesh.merge_vertices()
            
            # Fill holes
            mesh.fill_holes()
            
            # Subdivide for smoother appearance
            mesh = mesh.subdivide()
            
            # Additional smoothing
            mesh = trimesh.smoothing.filter_laplacian(mesh, iterations=3)
            
            self.mesh = mesh
            return True, mesh
        
        except Exception as e:
            return False, f"Mesh refinement error: {str(e)}"
    
    def export_mesh(self, output_path: str, format='ply') -> bool:
        """
        Export mesh to file
        
        Args:
            output_path: Output file path
            format: Export format (ply, obj, stl)
        
        Returns:
            Success status
        """
        try:
            if self.mesh is None:
                return False
            
            self.mesh.export(output_path, file_type=format)
            return True
        
        except Exception as e:
            print(f"Mesh export error: {str(e)}")
            return False
    
    def get_mesh_info(self) -> Dict:
        """
        Get mesh statistics and information
        
        Returns:
            Mesh information dictionary
        """
        if self.mesh is None:
            return {'error': 'No mesh available'}
        
        return {
            'num_vertices': len(self.mesh.vertices),
            'num_faces': len(self.mesh.faces),
            'volume': float(self.mesh.volume),
            'surface_area': float(self.mesh.area),
            'is_watertight': self.mesh.is_watertight,
            'bounds': self.mesh.bounds.tolist()
        }
    
    def cleanup(self):
        """Release resources"""
        if self.pose_detector:
            self.pose_detector.close()

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
        
        # Step 1: Extract 3D landmarks
        print("Step 1: Extracting 3D landmarks from video...")
        success, landmarks = reconstructor.extract_3d_landmarks(frames)
        if not success:
            return False, landmarks
        print(f"✓ Extracted 3D landmarks: {len(landmarks)} points")
        
        # Step 2: Create body mesh
        print("\nStep 2: Creating 3D body mesh...")
        success, mesh = reconstructor.create_body_mesh(landmarks)
        if not success:
            return False, mesh
        print(f"✓ Created mesh: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
        
        # Step 3: Refine mesh
        print("\nStep 3: Refining mesh...")
        success, refined_mesh = reconstructor.refine_mesh(mesh)
        if not success:
            return False, refined_mesh
        print(f"✓ Refined mesh: {len(refined_mesh.vertices)} vertices")
        
        # Get mesh info
        mesh_info = reconstructor.get_mesh_info()
        
        result = {
            'mesh': refined_mesh,
            'landmarks_3d': landmarks,
            'mesh_info': mesh_info,
            'reconstructor': reconstructor
        }
        
        print("\n✅ 3D reconstruction completed successfully!\n")
        return True, result
    
    except Exception as e:
        return False, f"3D reconstruction pipeline error: {str(e)}"
