"""Tool 8: Video Measurement Pipeline
Complete end-to-end pipeline for video-based body measurements
"""

import os
from typing import Dict, Optional, Tuple
import tempfile

# Import all tools
from .video_upload import save_uploaded_video, validate_video
from .frame_extractor import extract_frames_from_video
from .pose_detector import detect_poses_in_frames
from .pose_quality_validator import validate_poses_batch, filter_valid_poses
from .body_measurement_calculator import calculate_measurements_from_poses
from .results_aggregator import aggregate_pipeline_results, ResultsAggregator
from .error_handler import (
    ErrorCategory,
    ErrorSeverity,
    handle_pipeline_error,
    safe_execute
)

class VideoMeasurementPipeline:
    """Complete pipeline for video-based body measurements"""
    
    def __init__(self, reference_height_cm: Optional[float] = None):
        """
        Initialize pipeline
        
        Args:
            reference_height_cm: Optional reference height for calibration
        """
        self.reference_height_cm = reference_height_cm
        self.temp_dir = tempfile.mkdtemp(prefix='measulor_')
        self.results = None
        self.aggregator = ResultsAggregator()
    
    def process_video(self, video_path: str, max_frames: int = 30) -> Tuple[bool, any]:
        """
        Process video through complete pipeline
        
        Args:
            video_path: Path to video file
            max_frames: Maximum frames to extract
        
        Returns:
            (success, results_or_error)
        """
        try:
            # Step 1: Validate video
            print("Step 1/7: Validating video...")
            success, result = safe_execute(
                validate_video,
                ErrorCategory.VIDEO_UPLOAD,
                video_path
            )
            
            if not success:
                return False, result
            
            video_info = result
            print(f"✓ Video validated: {video_info['duration']:.1f}s, {video_info['fps']:.1f} fps")
            
            # Step 2: Extract frames
            print(f"\nStep 2/7: Extracting frames (max {max_frames})...")
            success, result = safe_execute(
                extract_frames_from_video,
                ErrorCategory.FRAME_EXTRACTION,
                video_path,
                max_frames
            )
            
            if not success:
                return False, result
            
            frames = result
            print(f"✓ Extracted {len(frames)} frames")
            
            # Step 3: Detect poses
            print("\nStep 3/7: Detecting poses in frames...")
            success, result = safe_execute(
                detect_poses_in_frames,
                ErrorCategory.POSE_DETECTION,
                frames
            )
            
            if not success:
                return False, result
            
            poses = result
            print(f"✓ Detected poses in {len(poses)} frames")
            
            # Step 4: Validate pose quality
            print("\nStep 4/7: Validating pose quality...")
            success, result = safe_execute(
                validate_poses_batch,
                ErrorCategory.QUALITY_VALIDATION,
                poses
            )
            
            if not success:
                return False, result
            
            validation_results = result
            print(f"✓ Valid frames: {validation_results['valid_frames']}/{validation_results['total_frames']} "
                  f"({validation_results['valid_percentage']:.1f}%)")
            
            # Step 5: Filter valid poses
            print("\nStep 5/7: Filtering valid poses...")
            valid_poses, valid_indices = filter_valid_poses(poses)
            
            if not valid_poses:
                return False, {
                    'error': 'No valid poses found',
                    'message': 'Video quality insufficient for measurements'
                }
            
            print(f"✓ Using {len(valid_poses)} valid poses for measurement")
            
            # Step 6: Calculate measurements
            print("\nStep 6/7: Calculating body measurements...")
            success, result = safe_execute(
                calculate_measurements_from_poses,
                ErrorCategory.MEASUREMENT_CALCULATION,
                valid_poses,
                self.reference_height_cm
            )
            
            if not success:
                return False, result
            
            measurements = result
            print(f"✓ Measurements calculated")
            
            # Step 7: Aggregate results
            print("\nStep 7/7: Aggregating results...")
            self.results = self.aggregator.aggregate_results(
                video_info,
                frames,
                poses,
                validation_results,
                measurements
            )
            
            print("\n✅ Pipeline completed successfully!\n")
            return True, self.results
        
        except Exception as e:
            error = handle_pipeline_error(
                e,
                ErrorCategory.GENERAL,
                ErrorSeverity.CRITICAL,
                {'stage': 'pipeline_execution'}
            )
            return False, error
    
    def get_summary(self) -> Dict:
        """
        Get pipeline results summary
        
        Returns:
            Results summary
        """
        if self.results is None:
            return {'error': 'No results available. Run pipeline first.'}
        
        return self.aggregator.get_summary()
    
    def get_report(self) -> str:
        """
        Get formatted text report
        
        Returns:
            Formatted report
        """
        if self.results is None:
            return "No results available. Run pipeline first."
        
        return self.aggregator.export_formatted_report()
    
    def get_json(self) -> str:
        """
        Get results as JSON
        
        Returns:
            JSON string
        """
        if self.results is None:
            return '{"error": "No results available"}'
        
        return self.aggregator.export_json()
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Failed to cleanup temp dir: {e}")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.cleanup()

def process_video_simple(video_path: str,
                        reference_height_cm: Optional[float] = None,
                        max_frames: int = 30) -> Tuple[bool, any]:
    """
    Simple convenience function to process a video
    
    Args:
        video_path: Path to video file
        reference_height_cm: Optional reference height for calibration
        max_frames: Maximum frames to process
    
    Returns:
        (success, results_or_error)
    """
    pipeline = VideoMeasurementPipeline(reference_height_cm)
    success, result = pipeline.process_video(video_path, max_frames)
    
    if success:
        # Return formatted summary
        return True, {
            'success': True,
            'summary': pipeline.get_summary(),
            'full_results': result
        }
    else:
        return False, result

# API endpoint wrapper
def create_video_measurement_endpoint(video_file,
                                     reference_height_cm: Optional[float] = None) -> Dict:
    """
    API endpoint wrapper for video measurement
    
    Args:
        video_file: Uploaded video file
        reference_height_cm: Optional reference height
    
    Returns:
        API response dictionary
    """
    try:
        # Save uploaded video
        temp_path = os.path.join(tempfile.gettempdir(), 'upload_' + video_file.filename)
        video_file.save(temp_path)
        
        # Process video
        pipeline = VideoMeasurementPipeline(reference_height_cm)
        success, result = pipeline.process_video(temp_path)
        
        # Cleanup
        try:
            os.remove(temp_path)
        except:
            pass
        
        if success:
            return {
                'success': True,
                'data': pipeline.get_summary(),
                'report': pipeline.get_report()
            }
        else:
            return result
    
    except Exception as e:
        return handle_pipeline_error(
            e,
            ErrorCategory.GENERAL,
            ErrorSeverity.ERROR,
            {'endpoint': 'create_video_measurement'}
        )
