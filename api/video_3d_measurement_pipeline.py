"""Complete Video to 3D Model to Measurements Pipeline
Integrates all modules: Video → 3D Reconstruction → Measurements
"""

import os
import tempfile
from typing import Dict, Optional, Tuple

# Import all required modules
from .video_upload import validate_video
from .frame_extractor import extract_frames_from_video
from .video_to_3d_reconstruction import reconstruct_3d_from_video, VideoTo3DReconstructor
from .mesh_3d_measurements import extract_measurements_from_mesh, Mesh3DMeasurementExtractor

class Video3DMeasurementPipeline:
    """Complete pipeline: Video → 3D Model → Body Measurements"""
    
    def __init__(self, reference_height_cm: Optional[float] = None):
        """
        Initialize 3D measurement pipeline
        
        Args:
            reference_height_cm: Optional reference height for calibration
        """
        self.reference_height_cm = reference_height_cm
        self.results = {}
    
    def process_video(self, video_path: str, max_frames: int = 30) -> Tuple[bool, any]:
        """
        Process video through complete 3D pipeline
        
        Args:
            video_path: Path to video file
            max_frames: Maximum frames to extract
        
        Returns:
            (success, results or error_message)
        """
        try:
            print("="*60)
            print("VIDEO TO 3D MODEL TO MEASUREMENTS PIPELINE")
            print("="*60)
            
            # Step 1: Validate video
            print("\n[1/5] Validating video...")
            success, result = validate_video(video_path)
            if not success:
                return False, f"Video validation failed: {result}"
            
            video_info = result
            print(f"  ✓ Video: {video_info['duration']:.1f}s, {video_info['fps']:.1f} fps")
            
            # Step 2: Extract frames
            print(f"\n[2/5] Extracting frames (max {max_frames})...")
            success, frames = extract_frames_from_video(video_path, max_frames)
            if not success:
                return False, f"Frame extraction failed: {frames}"
            
            print(f"  ✓ Extracted {len(frames)} frames")
            
            # Step 3: Reconstruct 3D model from video
            print("\n[3/5] Reconstructing 3D body model from video...")
            success, reconstruction_result = reconstruct_3d_from_video(frames)
            if not success:
                return False, f"3D reconstruction failed: {reconstruction_result}"
            
            mesh = reconstruction_result['mesh']
            landmarks_3d = reconstruction_result['landmarks_3d']
            mesh_info = reconstruction_result['mesh_info']
            
            print(f"  ✓ 3D model created: {mesh_info['num_vertices']} vertices")
            print(f"  ✓ Volume: {mesh_info['volume']:.6f} m³")
            print(f"  ✓ Surface area: {mesh_info['surface_area']:.4f} m²")
            
            # Step 4: Extract measurements from 3D mesh
            print("\n[4/5] Extracting body measurements from 3D model...")
            success, measurements = extract_measurements_from_mesh(
                mesh, 
                landmarks_3d,
                self.reference_height_cm
            )
            if not success:
                return False, f"Measurement extraction failed: {measurements}"
            
            # Step 5: Compile results
            print("\n[5/5] Compiling results...")
            self.results = {
                'success': True,
                'pipeline_type': 'video_to_3d_to_measurements',
                'video_info': video_info,
                'processing_stats': {
                    'frames_extracted': len(frames),
                    'frames_used': len(frames)
                },
                '3d_model': {
                    'vertices': mesh_info['num_vertices'],
                    'faces': mesh_info['num_faces'],
                    'volume_m3': mesh_info['volume'],
                    'surface_area_m2': mesh_info['surface_area'],
                    'is_watertight': mesh_info['is_watertight']
                },
                'measurements': measurements,
                'quality': self._assess_quality(mesh_info, measurements)
            }
            
            print("\n" + "="*60)
            print("✅ PIPELINE COMPLETED SUCCESSFULLY!")
            print("="*60)
            
            return True, self.results
        
        except Exception as e:
            return False, f"Pipeline error: {str(e)}"
    
    def _assess_quality(self, mesh_info: Dict, measurements: Dict) -> Dict:
        """
        Assess overall quality of 3D reconstruction and measurements
        
        Args:
            mesh_info: Mesh statistics
            measurements: Measurement results
        
        Returns:
            Quality assessment
        """
        quality = {}
        
        # Assess mesh quality
        vertex_count = mesh_info.get('num_vertices', 0)
        is_watertight = mesh_info.get('is_watertight', False)
        
        if vertex_count > 500 and is_watertight:
            quality['mesh_quality'] = 'excellent'
        elif vertex_count > 200:
            quality['mesh_quality'] = 'good'
        elif vertex_count > 100:
            quality['mesh_quality'] = 'fair'
        else:
            quality['mesh_quality'] = 'poor'
        
        # Assess measurement confidence
        has_calibration = measurements.get('reference_height_provided', False)
        
        if has_calibration and quality['mesh_quality'] in ['excellent', 'good']:
            quality['measurement_confidence'] = 'high'
        elif quality['mesh_quality'] in ['excellent', 'good']:
            quality['measurement_confidence'] = 'medium'
        else:
            quality['measurement_confidence'] = 'low'
        
        # Generate recommendations
        quality['recommendations'] = self._generate_recommendations(quality, mesh_info)
        
        return quality
    
    def _generate_recommendations(self, quality: Dict, mesh_info: Dict) -> list:
        """
        Generate recommendations based on quality
        
        Args:
            quality: Quality assessment
            mesh_info: Mesh statistics
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if quality['mesh_quality'] == 'poor':
            recommendations.append("Mesh quality is low. Try recording video with better lighting.")
            recommendations.append("Ensure full body is visible throughout the video.")
        
        if quality['measurement_confidence'] == 'low':
            recommendations.append("Low measurement confidence. Provide reference height for better accuracy.")
        
        if not mesh_info.get('is_watertight', False):
            recommendations.append("3D model has holes. This may affect volume-based measurements.")
        
        if not recommendations:
            recommendations.append("Measurements appear accurate. 3D model quality is good.")
        
        return recommendations
    
    def get_summary(self) -> Dict:
        """
        Get summary of results
        
        Returns:
            Summary dictionary
        """
        if not self.results:
            return {'error': 'No results available. Run pipeline first.'}
        
        measurements = self.results.get('measurements', {})
        
        summary = {
            'pipeline': 'video → 3D model → measurements',
            'quality': self.results['quality']['mesh_quality'],
            'confidence': self.results['quality']['measurement_confidence'],
            '3d_model': self.results['3d_model'],
            'key_measurements': {}
        }
        
        # Extract key measurements
        key_fields = [
            'height', 'shoulder_width', 'chest_circumference',
            'waist_circumference', 'hip_circumference', 'hip_width',
            'arm_length', 'leg_length', 'inseam', 'torso_length'
        ]
        
        for field in key_fields:
            if field in measurements:
                summary['key_measurements'][field] = f"{measurements[field]:.2f} cm"
        
        return summary
    
    def get_full_report(self) -> str:
        """
        Get formatted text report
        
        Returns:
            Formatted report
        """
        if not self.results:
            return "No results available. Run pipeline first."
        
        report = []
        report.append("=" * 70)
        report.append("3D BODY MEASUREMENT REPORT (Video → 3D Model → Measurements)")
        report.append("=" * 70)
        
        # Video info
        video_info = self.results['video_info']
        report.append(f"\nVideo: {video_info['filename']}")
        report.append(f"Duration: {video_info['duration']:.1f}s, FPS: {video_info['fps']:.1f}")
        
        # 3D Model info
        model = self.results['3d_model']
        report.append("\n3D Model Statistics:")
        report.append("-" * 70)
        report.append(f"  Vertices: {model['vertices']:,}")
        report.append(f"  Faces: {model['faces']:,}")
        report.append(f"  Volume: {model['volume_m3']:.6f} m³")
        report.append(f"  Surface Area: {model['surface_area_m2']:.4f} m²")
        report.append(f"  Watertight: {'Yes' if model['is_watertight'] else 'No'}")
        
        # Quality
        quality = self.results['quality']
        report.append("\nQuality Assessment:")
        report.append("-" * 70)
        report.append(f"  Mesh Quality: {quality['mesh_quality'].upper()}")
        report.append(f"  Measurement Confidence: {quality['measurement_confidence'].upper()}")
        
        # Measurements
        measurements = self.results['measurements']
        report.append("\nBody Measurements:")
        report.append("-" * 70)
        
        measurement_list = [
            ('Height', 'height'),
            ('Shoulder Width', 'shoulder_width'),
            ('Chest Circumference', 'chest_circumference'),
            ('Waist Circumference', 'waist_circumference'),
            ('Hip Width', 'hip_width'),
            ('Hip Circumference', 'hip_circumference'),
            ('Arm Length', 'arm_length'),
            ('Upper Arm Length', 'upper_arm_length'),
            ('Forearm Length', 'forearm_length'),
            ('Leg Length', 'leg_length'),
            ('Inseam', 'inseam'),
            ('Torso Length', 'torso_length')
        ]
        
        for label, key in measurement_list:
            if key in measurements:
                value = measurements[key]
                report.append(f"  {label:.<40} {value:.2f} cm")
        
        # Recommendations
        report.append("\nRecommendations:")
        report.append("-" * 70)
        for rec in quality.get('recommendations', []):
            report.append(f"  • {rec}")
        
        report.append("\n" + "=" * 70)
        
        return "\n".join(report)

def process_video_to_3d_measurements(video_path: str,
                                    reference_height_cm: Optional[float] = None,
                                    max_frames: int = 30) -> Tuple[bool, any]:
    """
    Convenience function to process video through 3D pipeline
    
    Args:
        video_path: Path to video file
        reference_height_cm: Optional reference height for calibration
        max_frames: Maximum frames to process
    
    Returns:
        (success, results or error_message)
    """
    pipeline = Video3DMeasurementPipeline(reference_height_cm)
    return pipeline.process_video(video_path, max_frames)
